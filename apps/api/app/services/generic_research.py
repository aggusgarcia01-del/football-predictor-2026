import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from math import exp, factorial
from typing import Any

from app.models.schemas import GenericMatchResearchRequest, GenericMatchResearchResult, GenericPredictionSelection
from app.services import data
from app.services.analysis import analyze_question
from app.services.statistical_inputs import reliability


FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _poisson(lam: float, goals: int) -> float:
    return (exp(-lam) * lam**goals) / factorial(goals)


def _score_probabilities(home_xg: float, away_xg: float) -> dict[str, float]:
    home = draw = away = over_25 = btts_yes = 0.0
    for hg in range(8):
        for ag in range(8):
            probability = _poisson(home_xg, hg) * _poisson(away_xg, ag)
            if hg > ag:
                home += probability
            elif hg == ag:
                draw += probability
            else:
                away += probability
            if hg + ag > 2.5:
                over_25 += probability
            if hg > 0 and ag > 0:
                btts_yes += probability
    total = home + draw + away
    return {
        "Home": home / total,
        "Draw": draw / total,
        "Away": away / total,
        "1X": (home + draw) / total,
        "12": (home + away) / total,
        "X2": (draw + away) / total,
        "Over 2.5": over_25 / total,
        "Under 2.5": 1 - (over_25 / total),
        "BTTS Yes": btts_yes / total,
        "BTTS No": 1 - (btts_yes / total),
    }


def _selection(market: str, selection: str, probability: float, edge: float = 0.04) -> GenericPredictionSelection:
    fair_odds = 1 / max(probability, 0.0001)
    return GenericPredictionSelection(
        market=market,
        selection=selection,
        probability=round(probability, 4),
        fair_odds=round(fair_odds, 3),
        minimum_odds_for_value=round(fair_odds * (1 + edge), 3),
    )


def _local_team_id(name: str) -> str | None:
    normalized = _normalize(name)
    for team_id, team in data.teams().items():
        aliases = [_normalize(team.name), team_id.casefold()]
        aliases.extend(_normalize(alias) for alias in data.team_aliases().get(team_id, []))
        if normalized in aliases:
            return team_id
    return None


def _try_local_prediction(request: GenericMatchResearchRequest) -> GenericMatchResearchResult | None:
    home_id = _local_team_id(request.home_team)
    away_id = _local_team_id(request.away_team)
    if not home_id or not away_id:
        return None
    analysis = analyze_question(type("Request", (), {"question": f"Analiza {request.home_team} vs {request.away_team}"})())
    prediction = analysis.prediction
    probabilities: list[GenericPredictionSelection] = []
    for market, rows in prediction.markets.items():
        for row in rows:
            probabilities.append(_selection(market, row.selection, row.probability))
    home_rel = reliability(data.team_metrics().get(home_id))
    away_rel = reliability(data.team_metrics().get(away_id))
    confidence = "MEDIA" if (home_rel + away_rel) / 2 >= 0.55 else "BAJA"
    return GenericMatchResearchResult(
        status="LOCAL_MODEL_MATCHED",
        home_team=prediction.match.home_team.name,
        away_team=prediction.match.away_team.name,
        match_date=request.match_date,
        data_sources=["local_seed", "statsbomb_open_data_when_available"],
        expected_goals_home=prediction.expected_goals_home,
        expected_goals_away=prediction.expected_goals_away,
        probabilities=sorted(probabilities, key=lambda row: row.probability, reverse=True),
        confidence=confidence,
        evidence=[
            f"Reliability home/away: {home_rel:.2f}/{away_rel:.2f}.",
            "Uses local World Cup model: ELO + StatsBomb/team metrics + Poisson/Dixon-Coles.",
        ],
        limitations=[
            "Only reliable for teams mapped in the local project.",
            "For any club/global fixture, configure FOOTBALL_DATA_API_KEY or another provider.",
        ],
        next_steps=["Import real prematch odds and confirmed lineups before betting."],
    )


def _football_data_request(path: str, params: dict[str, str] | None = None) -> Any:
    token = os.getenv("FOOTBALL_DATA_API_KEY")
    if not token:
        raise RuntimeError("MISSING_FOOTBALL_DATA_API_KEY")
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{FOOTBALL_DATA_BASE}{path}{query}",
        headers={"X-Auth-Token": token},
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.load(response)


def _date_window(match_date: str | None) -> tuple[str, str]:
    if match_date:
        center = datetime.fromisoformat(match_date[:10]).date()
    else:
        center = datetime.now(UTC).date()
    return (center - timedelta(days=3)).isoformat(), (center + timedelta(days=7)).isoformat()


def _find_provider_match(request: GenericMatchResearchRequest) -> dict | None:
    date_from, date_to = _date_window(request.match_date)
    payload = _football_data_request("/matches", {"dateFrom": date_from, "dateTo": date_to})
    home = _normalize(request.home_team)
    away = _normalize(request.away_team)
    for match in payload.get("matches", []):
        home_name = _normalize(match.get("homeTeam", {}).get("name", ""))
        away_name = _normalize(match.get("awayTeam", {}).get("name", ""))
        if home in home_name and away in away_name:
            return match
        if away in home_name and home in away_name:
            return match
    return None


def _team_recent_stats(team_id: int, venue: str | None = None, limit: int = 15) -> dict[str, float]:
    params = {"status": "FINISHED", "limit": str(limit)}
    if venue:
        params["venue"] = venue
    payload = _football_data_request(f"/teams/{team_id}/matches", params)
    matches = payload.get("matches", [])[:limit]
    if not matches:
        return {"matches": 0, "goals_for": 1.25, "goals_against": 1.25, "points": 1.4}
    gf = ga = points = 0
    for match in matches:
        is_home = match.get("homeTeam", {}).get("id") == team_id
        score = match.get("score", {}).get("fullTime", {})
        team_goals = int(score.get("home") if is_home else score.get("away") or 0)
        opp_goals = int(score.get("away") if is_home else score.get("home") or 0)
        gf += team_goals
        ga += opp_goals
        points += 3 if team_goals > opp_goals else 1 if team_goals == opp_goals else 0
    n = len(matches)
    return {"matches": n, "goals_for": gf / n, "goals_against": ga / n, "points": points / n}


def _provider_prediction(request: GenericMatchResearchRequest) -> GenericMatchResearchResult:
    match = _find_provider_match(request)
    if not match:
        return GenericMatchResearchResult(
            status="PROVIDER_NO_MATCH_FOUND",
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            data_sources=["football-data.org"],
            probabilities=[],
            confidence="SIN_DATOS",
            evidence=[],
            limitations=["No matching fixture was found in the provider date window."],
            next_steps=["Check team names/date or use a provider with broader coverage."],
        )

    home = match["homeTeam"]
    away = match["awayTeam"]
    home_stats = _team_recent_stats(int(home["id"]), "HOME")
    away_stats = _team_recent_stats(int(away["id"]), "AWAY")
    home_xg = max(0.25, (home_stats["goals_for"] * 0.58) + (away_stats["goals_against"] * 0.42))
    away_xg = max(0.25, (away_stats["goals_for"] * 0.58) + (home_stats["goals_against"] * 0.42))
    probs = _score_probabilities(home_xg, away_xg)
    selections = [
        _selection("1X2", "Home", probs["Home"]),
        _selection("1X2", "Draw", probs["Draw"]),
        _selection("1X2", "Away", probs["Away"]),
        _selection("Double Chance", "1X", probs["1X"]),
        _selection("Double Chance", "12", probs["12"]),
        _selection("Double Chance", "X2", probs["X2"]),
        _selection("Over/Under 2.5", "Over 2.5", probs["Over 2.5"]),
        _selection("Over/Under 2.5", "Under 2.5", probs["Under 2.5"]),
        _selection("BTTS", "Yes", probs["BTTS Yes"]),
        _selection("BTTS", "No", probs["BTTS No"]),
    ]
    confidence = "MEDIA" if min(home_stats["matches"], away_stats["matches"]) >= 8 else "BAJA"
    return GenericMatchResearchResult(
        status="PROVIDER_MODEL_MATCHED",
        home_team=home["name"],
        away_team=away["name"],
        match_date=match.get("utcDate"),
        data_sources=["football-data.org"],
        expected_goals_home=round(home_xg, 2),
        expected_goals_away=round(away_xg, 2),
        probabilities=sorted(selections, key=lambda row: row.probability, reverse=True),
        confidence=confidence,
        evidence=[
            f"{home['name']} recent home sample: {home_stats['matches']} matches, GF {home_stats['goals_for']:.2f}, GA {home_stats['goals_against']:.2f}, PPM {home_stats['points']:.2f}.",
            f"{away['name']} recent away sample: {away_stats['matches']} matches, GF {away_stats['goals_for']:.2f}, GA {away_stats['goals_against']:.2f}, PPM {away_stats['points']:.2f}.",
            "Expected goals use recent goals for/against; not xG unless a richer provider is connected.",
        ],
        limitations=[
            "football-data.org is useful for fixtures/results/form, but not full xG/lineup/shot-quality data.",
            "Prediction improves with xG, injuries, lineups and live odds providers.",
        ],
        next_steps=[
            "Import bookmaker odds and compare with minimum_odds_for_value.",
            "Re-run 30-40 minutes before kickoff with lineups.",
        ],
    )


def research_generic_match(request: GenericMatchResearchRequest) -> GenericMatchResearchResult:
    local = _try_local_prediction(request)
    if local:
        return local
    try:
        return _provider_prediction(request)
    except RuntimeError as exc:
        if str(exc) != "MISSING_FOOTBALL_DATA_API_KEY":
            raise
        return GenericMatchResearchResult(
            status="NEEDS_DATA_PROVIDER_KEY",
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            data_sources=[],
            probabilities=[],
            confidence="SIN_DATOS",
            evidence=[],
            limitations=[
                "This match is not in the local World Cup/team dataset.",
                "To support arbitrary clubs/fixtures, set FOOTBALL_DATA_API_KEY or connect another provider.",
            ],
            next_steps=[
                "Create a free key at football-data.org and set FOOTBALL_DATA_API_KEY.",
                "For advanced xG/lineups, connect a licensed provider such as API-Football/Sportmonks/Opta.",
            ],
        )
