import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from typing import Any


API_FOOTBALL_BASE = "https://v3.football.api-sports.io"


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _request(path: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
    api_key = os.getenv("API_FOOTBALL_KEY") or os.getenv("APISPORTS_KEY")
    if not api_key:
        raise RuntimeError("MISSING_API_FOOTBALL_KEY")
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{API_FOOTBALL_BASE}{path}{query}",
        headers={"x-apisports-key": api_key},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)


def _missing_key_response() -> dict[str, Any]:
    return {
        "status": "MISSING_API_FOOTBALL_KEY",
        "provider": "API-Football / API-Sports",
        "required_env": "API_FOOTBALL_KEY",
        "fallback_env": "APISPORTS_KEY",
        "notes": [
            "Create an API-Sports/API-Football key and set API_FOOTBALL_KEY.",
            "This connector is designed for fixtures, live scores, events, lineups, statistics, predictions and odds.",
        ],
    }


def api_football_live() -> dict[str, Any]:
    try:
        payload = _request("/fixtures", {"live": "all"})
    except RuntimeError:
        return _missing_key_response()
    return {
        "status": "LIVE_FIXTURES_IMPORTED_FROM_PROVIDER",
        "provider": "API-Football / API-Sports",
        "count": len(payload.get("response", [])),
        "fixtures": payload.get("response", []),
    }


def api_football_fixture_detail(fixture_id: int) -> dict[str, Any]:
    try:
        fixture = _request("/fixtures", {"id": fixture_id})
        statistics = _request("/fixtures/statistics", {"fixture": fixture_id})
        lineups = _request("/fixtures/lineups", {"fixture": fixture_id})
        events = _request("/fixtures/events", {"fixture": fixture_id})
        predictions = _request("/predictions", {"fixture": fixture_id})
    except RuntimeError:
        return _missing_key_response()
    return {
        "status": "FIXTURE_DETAIL_IMPORTED_FROM_PROVIDER",
        "provider": "API-Football / API-Sports",
        "fixture": fixture.get("response", []),
        "statistics": statistics.get("response", []),
        "lineups": lineups.get("response", []),
        "events": events.get("response", []),
        "provider_predictions": predictions.get("response", []),
    }


def _date_range(center: str | None) -> list[str]:
    if center:
        base = datetime.fromisoformat(center[:10]).date()
    else:
        base = datetime.now(UTC).date()
    return [(base + timedelta(days=offset)).isoformat() for offset in range(-3, 8)]


def find_api_football_fixture(home_team: str, away_team: str, match_date: str | None = None) -> dict[str, Any]:
    home = _normalize(home_team)
    away = _normalize(away_team)
    try:
        for day in _date_range(match_date):
            payload = _request("/fixtures", {"date": day})
            for item in payload.get("response", []):
                teams = item.get("teams", {})
                home_name = _normalize(teams.get("home", {}).get("name", ""))
                away_name = _normalize(teams.get("away", {}).get("name", ""))
                if home in home_name and away in away_name:
                    return {"status": "MATCH_FOUND", "fixture": item}
                if away in home_name and home in away_name:
                    return {"status": "MATCH_FOUND_REVERSED", "fixture": item}
    except RuntimeError:
        return _missing_key_response()
    return {
        "status": "NO_MATCH_FOUND",
        "provider": "API-Football / API-Sports",
        "home_team": home_team,
        "away_team": away_team,
        "match_date": match_date,
    }


def api_football_match_research(home_team: str, away_team: str, match_date: str | None = None) -> dict[str, Any]:
    found = find_api_football_fixture(home_team, away_team, match_date)
    if found.get("status") in {"MISSING_API_FOOTBALL_KEY", "NO_MATCH_FOUND"}:
        return found

    fixture = found["fixture"]
    fixture_id = int(fixture["fixture"]["id"])
    detail = api_football_fixture_detail(fixture_id)
    return {
        "status": "API_FOOTBALL_RESEARCH_READY",
        "provider": "API-Football / API-Sports",
        "matched_fixture": fixture,
        "detail": detail,
        "notes": [
            "Use fixture statistics for live/in-play model adjustments.",
            "Use lineups once available 30-60 minutes before kickoff.",
            "Use provider predictions as a comparison signal, not as the only model.",
        ],
    }


def api_football_training_instructions() -> dict[str, Any]:
    return {
        "status": "TRAINING_WORKFLOW",
        "steps": [
            "1. Prematch: save fixture, odds, lineups and model prediction before kickoff.",
            "2. Live: every 10-15 minutes save score, minute, shots, shots on target, corners, red cards and live odds.",
            "3. Final: settle the snapshot with final score and market results.",
            "4. Backtest: compare predicted probabilities with actual outcomes by market.",
            "5. Calibrate: reduce trust where historical buckets are overconfident.",
        ],
        "minimum_dataset": [
            "At least 300 completed matches for basic 1X2 calibration.",
            "At least 1000 completed matches for stronger market calibration.",
            "Historical odds snapshots if you want ROI/value validation.",
        ],
        "what_to_capture": [
            "fixture_id, league, season, kickoff time",
            "home/away teams",
            "prematch probabilities and odds",
            "lineups and absences",
            "live minute, score, shots, shots on target, corners, cards",
            "final score and settled markets",
        ],
    }
