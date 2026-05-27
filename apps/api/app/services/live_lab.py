import json
from datetime import UTC, datetime
from math import exp, factorial
from pathlib import Path

from app.services.generic_research import research_generic_match
from app.models.schemas import GenericMatchResearchRequest


ROOT = Path(__file__).resolve().parents[4]
SNAPSHOTS_FILE = ROOT / "data" / "imports" / "live_prediction_snapshots.json"


def _poisson(lam: float, goals: int) -> float:
    return (exp(-lam) * lam**goals) / factorial(goals)


def _remaining_matrix(home_remaining_xg: float, away_remaining_xg: float, max_goals: int = 6) -> dict[tuple[int, int], float]:
    matrix: dict[tuple[int, int], float] = {}
    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            matrix[(hg, ag)] = _poisson(home_remaining_xg, hg) * _poisson(away_remaining_xg, ag)
    total = sum(matrix.values())
    return {score: probability / total for score, probability in matrix.items()}


def _load_snapshots() -> list[dict]:
    if not SNAPSHOTS_FILE.exists():
        return []
    with SNAPSHOTS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_snapshots(rows: list[dict]) -> None:
    SNAPSHOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOTS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)


def live_prediction_snapshot(payload: dict, save: bool = True) -> dict:
    home_team = str(payload["home_team"])
    away_team = str(payload["away_team"])
    minute = max(1, min(int(payload["minute"]), 120))
    home_goals = int(payload.get("home_goals", 0))
    away_goals = int(payload.get("away_goals", 0))
    match_date = payload.get("match_date")

    prematch = research_generic_match(
        GenericMatchResearchRequest(home_team=home_team, away_team=away_team, match_date=match_date)
    )
    if prematch.expected_goals_home is None or prematch.expected_goals_away is None:
        base_home_xg = float(payload.get("home_prematch_xg", 1.25))
        base_away_xg = float(payload.get("away_prematch_xg", 1.15))
        source_note = "fallback_manual_or_global_xg"
    else:
        base_home_xg = prematch.expected_goals_home
        base_away_xg = prematch.expected_goals_away
        source_note = prematch.status

    remaining_share = max(0.0, (96 - minute) / 96)
    home_remaining_xg = max(0.02, base_home_xg * remaining_share)
    away_remaining_xg = max(0.02, base_away_xg * remaining_share)
    matrix = _remaining_matrix(home_remaining_xg, away_remaining_xg)

    home_win = draw = away_win = over_25 = btts_yes = 0.0
    current_total = home_goals + away_goals
    for (hg_add, ag_add), probability in matrix.items():
        final_home = home_goals + hg_add
        final_away = away_goals + ag_add
        if final_home > final_away:
            home_win += probability
        elif final_home == final_away:
            draw += probability
        else:
            away_win += probability
        if final_home + final_away > 2.5:
            over_25 += probability
        if final_home > 0 and final_away > 0:
            btts_yes += probability

    snapshot = {
        "id": f"live-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "home_team": home_team,
        "away_team": away_team,
        "minute": minute,
        "score": {"home": home_goals, "away": away_goals},
        "source_note": source_note,
        "base_expected_goals": {"home": round(base_home_xg, 3), "away": round(base_away_xg, 3)},
        "remaining_expected_goals": {"home": round(home_remaining_xg, 3), "away": round(away_remaining_xg, 3)},
        "probabilities": {
            "home_win": round(home_win, 4),
            "draw": round(draw, 4),
            "away_win": round(away_win, 4),
            "over_2_5": round(over_25, 4),
            "under_2_5": round(1 - over_25, 4),
            "btts_yes": round(btts_yes, 4),
            "btts_no": round(1 - btts_yes, 4),
        },
        "top_call": max(
            [
                ("home_win", home_win),
                ("draw", draw),
                ("away_win", away_win),
                ("under_2_5", 1 - over_25),
                ("over_2_5", over_25),
                ("btts_no", 1 - btts_yes),
                ("btts_yes", btts_yes),
            ],
            key=lambda item: item[1],
        )[0],
        "status": "LIVE_RESEARCH_SNAPSHOT",
        "notes": [
            "This is an in-play approximation from current score, minute and prematch xG.",
            "It is useful for testing model behavior, not for validated live betting.",
            "For stronger live predictions, connect live shots/xG/red cards/lineups.",
        ],
    }

    if save:
        rows = _load_snapshots()
        rows.append(snapshot)
        _save_snapshots(rows)

    return snapshot


def list_live_snapshots() -> list[dict]:
    return _load_snapshots()


def settle_live_snapshot(snapshot_id: str, final_home_goals: int, final_away_goals: int) -> dict:
    rows = _load_snapshots()
    for row in rows:
        if row["id"] != snapshot_id:
            continue
        actual = "home_win" if final_home_goals > final_away_goals else "away_win" if final_home_goals < final_away_goals else "draw"
        row["settled"] = {
            "final_score": {"home": final_home_goals, "away": final_away_goals},
            "actual_1x2": actual,
            "top_call_hit": row["top_call"] == actual,
            "settled_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        _save_snapshots(rows)
        return row
    raise KeyError(snapshot_id)
