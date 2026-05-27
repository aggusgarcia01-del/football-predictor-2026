import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from app.models.schemas import ImportDatasetRequest
from app.services import data
from app.services.ingestion import import_dataset


ODDS_API_BASE = "https://api.the-odds-api.com/v4"


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _team_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for team_id, team in data.teams().items():
        lookup[_normalize(team.name)] = team_id
        for alias in data.team_aliases().get(team_id, []):
            lookup[_normalize(alias)] = team_id
    return lookup


def _selection_from_outcome(outcome_name: str, home_name: str, away_name: str) -> str | None:
    normalized = _normalize(outcome_name)
    if normalized == "draw":
        return "Draw"
    if normalized == _normalize(home_name):
        return "Home"
    if normalized == _normalize(away_name):
        return "Away"
    return None


def import_the_odds_api(
    sport: str = "soccer_fifa_world_cup",
    regions: str = "us,eu,uk",
    markets: str = "h2h",
    dry_run: bool = False,
) -> dict[str, Any]:
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        return {
            "status": "MISSING_API_KEY",
            "provider": "The Odds API",
            "required_env": "THE_ODDS_API_KEY",
            "notes": [
                "Create an API key at https://the-odds-api.com/ and set THE_ODDS_API_KEY before importing.",
                "No scraping is used; this connector only calls the official API.",
            ],
        }

    params = urllib.parse.urlencode(
        {
            "apiKey": api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
    )
    url = f"{ODDS_API_BASE}/sports/{urllib.parse.quote(sport)}/odds?{params}"
    with urllib.request.urlopen(url, timeout=40) as response:
        payload = json.load(response)

    lookup = _team_lookup()
    local_matches = data.matches()
    records: list[dict[str, Any]] = []
    unmatched_events: list[dict[str, Any]] = []
    captured_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    for event in payload:
        home_name = event.get("home_team", "")
        away_name = event.get("away_team", "")
        home_id = lookup.get(_normalize(home_name))
        away_id = lookup.get(_normalize(away_name))
        match = next(
            (
                row
                for row in local_matches.values()
                if row.home_team_id == home_id and row.away_team_id == away_id
            ),
            None,
        )
        if not match:
            unmatched_events.append({"home_team": home_name, "away_team": away_name, "commence_time": event.get("commence_time")})
            continue

        for bookmaker in event.get("bookmakers", []):
            bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or "unknown"
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    selection = _selection_from_outcome(outcome.get("name", ""), home_name, away_name)
                    if not selection:
                        continue
                    records.append(
                        {
                            "match_id": match.id,
                            "bookmaker": bookmaker_name,
                            "market": "1X2",
                            "selection": selection,
                            "decimal_odds": float(outcome.get("price")),
                            "captured_at": captured_at,
                            "source": "the_odds_api",
                            "provider_event_id": event.get("id"),
                        }
                    )

    import_result = None
    if records and not dry_run:
        import_result = import_dataset("odds", ImportDatasetRequest(records=records)).model_dump()

    return {
        "status": "DRY_RUN" if dry_run else "IMPORTED" if records else "NO_MATCHED_ODDS",
        "provider": "The Odds API",
        "sport": sport,
        "regions": regions,
        "markets": markets,
        "events_received": len(payload),
        "records_matched": len(records),
        "unmatched_events": unmatched_events[:20],
        "import_result": import_result,
        "notes": [
            "This imports pre-match h2h odds when the provider has events matching local fixtures.",
            "World Cup 2026 markets may not exist yet; the connector is ready once the provider lists them.",
        ],
    }
