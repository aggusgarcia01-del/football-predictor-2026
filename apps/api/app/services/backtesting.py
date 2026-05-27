import json
from collections import defaultdict
from math import exp, factorial, log
from pathlib import Path

from app.models.schemas import BacktestResult
from app.services import data
from app.services.prediction import predict_match


def _actual_selection(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "Home"
    if home_goals < away_goals:
        return "Away"
    return "Draw"


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _team_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for team_id, team in data.teams().items():
        lookup[_normalize(team.name)] = team_id
        for alias in data.team_aliases().get(team_id, []):
            lookup[_normalize(alias)] = team_id
    return lookup


def _historical_probabilities(home_team_id: str, away_team_id: str) -> dict[str, float]:
    teams = data.teams()
    home_elo = teams[home_team_id].elo
    away_elo = teams[away_team_id].elo
    diff = home_elo - away_elo
    home_strength = exp(diff / 420)
    away_strength = exp(-diff / 420)
    draw_strength = 0.78
    total = home_strength + away_strength + draw_strength
    return {
        "Home": home_strength / total,
        "Draw": draw_strength / total,
        "Away": away_strength / total,
    }


def _poisson(lam: float, goals: int) -> float:
    return (exp(-lam) * lam**goals) / factorial(goals)


def _xg_probabilities(home_xg: float, away_xg: float) -> dict[str, float]:
    home = draw = away = 0.0
    for hg in range(8):
        for ag in range(8):
            probability = _poisson(home_xg, hg) * _poisson(away_xg, ag)
            if hg > ag:
                home += probability
            elif hg == ag:
                draw += probability
            else:
                away += probability
    total = home + draw + away
    return {"Home": home / total, "Draw": draw / total, "Away": away / total}


def _event_xg_by_team(match_id: str, lookup: dict[str, str]) -> dict[str, float]:
    root = Path(__file__).resolve().parents[4]
    event_file = root / "data" / "statsbomb_cache" / f"events__{match_id}.json"
    if not event_file.exists():
        return {}
    with event_file.open("r", encoding="utf-8") as handle:
        events = json.load(handle)
    xg: dict[str, float] = defaultdict(float)
    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        shot = event.get("shot", {})
        if shot.get("type", {}).get("name") == "Penalty":
            continue
        team_id = lookup.get(_normalize(event.get("team", {}).get("name", "")))
        if team_id:
            xg[team_id] += float(shot.get("statsbomb_xg", 0.0) or 0.0)
    return xg


def _run_statsbomb_rolling_xg_backtest(min_prior_matches: int = 3) -> BacktestResult:
    root = Path(__file__).resolve().parents[4]
    cache_dir = root / "data" / "statsbomb_cache"
    lookup = _team_lookup()
    rows: list[dict] = []
    for match_file in cache_dir.glob("matches__*.json"):
        with match_file.open("r", encoding="utf-8") as handle:
            matches = json.load(handle)
        for match in matches:
            home_id = lookup.get(_normalize(match.get("home_team", {}).get("home_team_name", "")))
            away_id = lookup.get(_normalize(match.get("away_team", {}).get("away_team_name", "")))
            if home_id and away_id:
                rows.append(
                    {
                        "match_id": str(match.get("match_id")),
                        "match_date": match.get("match_date", ""),
                        "home_id": home_id,
                        "away_id": away_id,
                        "home_goals": int(match.get("home_score", 0)),
                        "away_goals": int(match.get("away_score", 0)),
                    }
                )
    rows.sort(key=lambda row: row["match_date"])

    team_history = defaultdict(lambda: {"matches": 0, "xg_for": 0.0, "xg_against": 0.0})
    evaluated = 0
    brier_total = 0.0
    log_loss_total = 0.0
    skipped = 0

    for row in rows:
        home_hist = team_history[row["home_id"]]
        away_hist = team_history[row["away_id"]]
        if home_hist["matches"] >= min_prior_matches and away_hist["matches"] >= min_prior_matches:
            home_attack = home_hist["xg_for"] / home_hist["matches"]
            home_defense = home_hist["xg_against"] / home_hist["matches"]
            away_attack = away_hist["xg_for"] / away_hist["matches"]
            away_defense = away_hist["xg_against"] / away_hist["matches"]
            home_xg = max(0.2, (home_attack * 0.62) + (away_defense * 0.38))
            away_xg = max(0.2, (away_attack * 0.62) + (home_defense * 0.38))
            probabilities = _xg_probabilities(home_xg, away_xg)
            actual = _actual_selection(row["home_goals"], row["away_goals"])
            brier_total += sum(
                (probabilities[selection] - (1.0 if selection == actual else 0.0)) ** 2
                for selection in ("Home", "Draw", "Away")
            )
            log_loss_total += -log(max(probabilities[actual], 1e-9))
            evaluated += 1
        else:
            skipped += 1

        xg = _event_xg_by_team(row["match_id"], lookup)
        home_xg_actual = xg.get(row["home_id"], 0.0)
        away_xg_actual = xg.get(row["away_id"], 0.0)
        team_history[row["home_id"]]["matches"] += 1
        team_history[row["home_id"]]["xg_for"] += home_xg_actual
        team_history[row["home_id"]]["xg_against"] += away_xg_actual
        team_history[row["away_id"]]["matches"] += 1
        team_history[row["away_id"]]["xg_for"] += away_xg_actual
        team_history[row["away_id"]]["xg_against"] += home_xg_actual

    if evaluated == 0:
        return BacktestResult(
            dataset="statsbomb_rolling_xg",
            matches_evaluated=0,
            flagged_bets=0,
            roi=0.0,
            brier_score=0.0,
            log_loss=0.0,
            passed_roi_gate=False,
            passed_brier_gate=False,
            passed_log_loss_gate=False,
            production_gate_status="BLOCKED_NOT_ENOUGH_PRIOR_MATCHES",
            notes=["No matches had enough prior data for both teams."],
        )

    brier = brier_total / evaluated
    loss = log_loss_total / evaluated
    return BacktestResult(
        dataset="statsbomb_rolling_xg",
        matches_evaluated=evaluated,
        flagged_bets=0,
        roi=0.0,
        brier_score=round(brier, 4),
        log_loss=round(loss, 4),
        passed_roi_gate=False,
        passed_brier_gate=brier < 0.62,
        passed_log_loss_gate=loss < 1.25,
        production_gate_status="RESEARCH_ONLY_ROLLING_NO_ODDS",
        notes=[
            f"Rolling xG backtest; skipped {skipped} early matches without enough prior data.",
            "Each prediction uses only earlier matches in the cached StatsBomb competitions.",
            "Still not an ROI test because historical bookmaker odds are missing.",
        ],
    )


def _run_statsbomb_cache_backtest() -> BacktestResult:
    root = Path(__file__).resolve().parents[4]
    cache_dir = root / "data" / "statsbomb_cache"
    lookup = _team_lookup()
    if not cache_dir.exists():
        return BacktestResult(
            dataset="statsbomb_open_data",
            matches_evaluated=0,
            flagged_bets=0,
            roi=0.0,
            brier_score=0.0,
            log_loss=0.0,
            passed_roi_gate=False,
            passed_brier_gate=False,
            passed_log_loss_gate=False,
            production_gate_status="BLOCKED_NO_STATSBOMB_CACHE",
            notes=["Run POST /data/statsbomb/sync first so cached match files exist."],
        )

    rows: list[dict] = []
    for match_file in cache_dir.glob("matches__*.json"):
        with match_file.open("r", encoding="utf-8") as handle:
            matches = json.load(handle)
        for match in matches:
            home_id = lookup.get(_normalize(match.get("home_team", {}).get("home_team_name", "")))
            away_id = lookup.get(_normalize(match.get("away_team", {}).get("away_team_name", "")))
            if home_id and away_id:
                rows.append(
                    {
                        "home_id": home_id,
                        "away_id": away_id,
                        "home_goals": int(match.get("home_score", 0)),
                        "away_goals": int(match.get("away_score", 0)),
                    }
                )

    if not rows:
        return BacktestResult(
            dataset="statsbomb_open_data",
            matches_evaluated=0,
            flagged_bets=0,
            roi=0.0,
            brier_score=0.0,
            log_loss=0.0,
            passed_roi_gate=False,
            passed_brier_gate=False,
            passed_log_loss_gate=False,
            production_gate_status="BLOCKED_NO_MATCHING_TEAMS",
            notes=["StatsBomb cache exists, but no cached matches mapped to seeded World Cup 2026 teams."],
        )

    brier_total = 0.0
    log_loss_total = 0.0
    for row in rows:
        actual = _actual_selection(row["home_goals"], row["away_goals"])
        probabilities = _historical_probabilities(row["home_id"], row["away_id"])
        brier_total += sum(
            (probabilities[selection] - (1.0 if selection == actual else 0.0)) ** 2
            for selection in ("Home", "Draw", "Away")
        )
        log_loss_total += -log(max(probabilities[actual], 1e-9))

    matches_evaluated = len(rows)
    brier = brier_total / matches_evaluated
    loss = log_loss_total / matches_evaluated
    passed_brier = brier < 0.62
    passed_log_loss = loss < 1.25
    return BacktestResult(
        dataset="statsbomb_open_data",
        matches_evaluated=matches_evaluated,
        flagged_bets=0,
        roi=0.0,
        brier_score=round(brier, 4),
        log_loss=round(loss, 4),
        passed_roi_gate=False,
        passed_brier_gate=passed_brier,
        passed_log_loss_gate=passed_log_loss,
        production_gate_status="RESEARCH_ONLY_NO_HISTORICAL_ODDS",
        notes=[
            "Evaluates cached StatsBomb international matches mapped to seeded teams.",
            "This is a model calibration smoke test, not a betting ROI test because historical bookmaker odds are not included.",
            "Next improvement: rolling pre-match features generated only from matches before each historical kickoff.",
        ],
    )


def run_backtest(dataset: str = "seed_backtest_demo") -> BacktestResult:
    if dataset == "statsbomb_open_data":
        return _run_statsbomb_cache_backtest()
    if dataset == "statsbomb_rolling_xg":
        return _run_statsbomb_rolling_xg_backtest()

    rows = [row for row in data.historical_results() if row.get("dataset") == dataset]
    if not rows:
        return BacktestResult(
            dataset=dataset,
            matches_evaluated=0,
            flagged_bets=0,
            roi=0.0,
            brier_score=0.0,
            log_loss=0.0,
            passed_roi_gate=False,
            passed_brier_gate=False,
            passed_log_loss_gate=False,
            production_gate_status="BLOCKED_NO_DATA",
            notes=["No historical rows found for dataset."],
        )

    brier_total = 0.0
    log_loss_total = 0.0
    stake_total = 0.0
    profit_total = 0.0
    flagged_bets = 0

    for row in rows:
        prediction = predict_match(str(row["match_id"]))
        actual = _actual_selection(int(row["home_goals"]), int(row["away_goals"]))
        probabilities = {item.selection: item.probability for item in prediction.markets["1X2"]}

        brier_total += sum(
            (probabilities[selection] - (1.0 if selection == actual else 0.0)) ** 2
            for selection in ("Home", "Draw", "Away")
        )
        log_loss_total += -log(max(probabilities[actual], 1e-9))

        for item in prediction.markets["1X2"]:
            if item.ev is None or item.odds is None or item.ev <= 0.03:
                continue
            flagged_bets += 1
            stake_total += 1.0
            profit_total += item.odds - 1 if item.selection == actual else -1.0

    matches_evaluated = len(rows)
    roi = profit_total / stake_total if stake_total else 0.0
    brier = brier_total / matches_evaluated
    loss = log_loss_total / matches_evaluated

    passed_roi = roi > 0.04 and stake_total > 0
    passed_brier = brier < 0.22
    passed_log_loss = loss < 0.95
    gate_status = "PASSED" if passed_roi and passed_brier and passed_log_loss else "BLOCKED_NEEDS_REAL_BACKTEST"

    return BacktestResult(
        dataset=dataset,
        matches_evaluated=matches_evaluated,
        flagged_bets=flagged_bets,
        roi=round(roi, 4),
        brier_score=round(brier, 4),
        log_loss=round(loss, 4),
        passed_roi_gate=passed_roi,
        passed_brier_gate=passed_brier,
        passed_log_loss_gate=passed_log_loss,
        production_gate_status=gate_status,
        notes=[
            "This backtest uses a tiny seed dataset for pipeline validation only.",
            "Production gate must use Euro 2024, Copa America 2024, and WC qualifiers with historical odds.",
        ],
    )
