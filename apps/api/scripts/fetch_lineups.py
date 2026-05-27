#!/usr/bin/env python3
"""
Fetch confirmed/probable lineups for a local match via API-Football/API-Sports.

Setup:
  $env:API_FOOTBALL_KEY="your_key"

Run from apps/api:
  .\\.venv\\Scripts\\python.exe scripts\\fetch_lineups.py --match fwc26-001
"""
import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import data
from app.services.api_football_provider import api_football_match_research


POSITION_MAP = {
    "G": "GK",
    "D": "DF",
    "M": "MF",
    "F": "FW",
    "Goalkeeper": "GK",
    "Defender": "DF",
    "Midfielder": "MF",
    "Attacker": "FW",
}


def _position(value: str | None) -> str:
    if not value:
        return "MF"
    return POSITION_MAP.get(value, POSITION_MAP.get(value[:1].upper(), "MF"))


def _convert_lineup(match_id: str, local_team_id: str, provider_lineup: dict) -> dict:
    players = []
    for item in provider_lineup.get("startXI", []):
        player = item.get("player", {})
        players.append(
            {
                "name": player.get("name", "Unknown"),
                "position": _position(player.get("pos")),
                "status": "starter",
                "rating": 78,
                "fitness": 0.96,
                "expected_minutes": 90,
            }
        )
    for item in provider_lineup.get("substitutes", [])[:8]:
        player = item.get("player", {})
        players.append(
            {
                "name": player.get("name", "Unknown"),
                "position": _position(player.get("pos")),
                "status": "substitute",
                "rating": 74,
                "fitness": 0.95,
                "expected_minutes": 0,
            }
        )

    return {
        "match_id": match_id,
        "team_id": local_team_id,
        "status": "confirmed" if players else "probable",
        "source": "api_football",
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "formation": provider_lineup.get("formation"),
        "players": players,
    }


def _save(records: list[dict]) -> str:
    output = data.IMPORT_DIR / "lineups_active.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if output.exists():
        with output.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
    incoming_keys = {(row["match_id"], row["team_id"]) for row in records}
    merged = [row for row in existing if (row.get("match_id"), row.get("team_id")) not in incoming_keys]
    merged.extend(records)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)
    data.clear_caches()
    return str(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", required=True, help="Local match id, e.g. fwc26-001")
    args = parser.parse_args()

    if not (os.getenv("API_FOOTBALL_KEY") or os.getenv("APISPORTS_KEY")):
        print("ERROR: Missing API_FOOTBALL_KEY or APISPORTS_KEY.")
        print("API-Football/API-Sports is the recommended provider for lineups/live stats.")
        return 1

    match = data.matches().get(args.match)
    if not match:
        print(f"ERROR: Unknown match_id {args.match}")
        return 1
    home = data.teams()[match.home_team_id]
    away = data.teams()[match.away_team_id]
    print(f"Searching provider fixture: {home.name} vs {away.name}")

    research = api_football_match_research(home.name, away.name, match.date[:10])
    if research.get("status") != "API_FOOTBALL_RESEARCH_READY":
        print(json.dumps(research, ensure_ascii=False, indent=2))
        return 0

    lineups = research.get("detail", {}).get("lineups", [])
    if not lineups:
        print("Lineups are not available yet. Try again 30-60 minutes before kickoff.")
        return 0

    records = []
    for lineup in lineups:
        provider_name = str(lineup.get("team", {}).get("name", "")).casefold()
        local_team_id = match.home_team_id if home.name.casefold() in provider_name or provider_name in home.name.casefold() else match.away_team_id
        records.append(_convert_lineup(args.match, local_team_id, lineup))

    output = _save(records)
    print(f"Saved {len(records)} lineups to {output}")
    for record in records:
        starters = [player["name"] for player in record["players"] if player["status"] == "starter"]
        print(f"- {record['team_id']}: {record.get('formation') or '?'} | {', '.join(starters[:6])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
