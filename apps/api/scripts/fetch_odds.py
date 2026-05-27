#!/usr/bin/env python3
"""
Fetch prematch odds via The Odds API.

Setup:
  $env:THE_ODDS_API_KEY="your_key"

Run from apps/api:
  .\\.venv\\Scripts\\python.exe scripts\\fetch_odds.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.odds_provider import import_the_odds_api


def main() -> int:
    if not os.getenv("THE_ODDS_API_KEY"):
        print("ERROR: Missing THE_ODDS_API_KEY.")
        print("Get a key at https://the-odds-api.com/ and set it in your environment.")
        print("Free plans can be useful for prematch odds testing.")
        return 1

    print("Dry run: checking available World Cup odds...")
    dry = import_the_odds_api(
        sport="soccer_fifa_world_cup",
        regions="us,eu,uk",
        markets="h2h",
        dry_run=True,
    )
    print(f"Events received: {dry['events_received']}")
    print(f"Local records matched: {dry['records_matched']}")

    if dry.get("unmatched_events"):
        print("Unmatched events:")
        for event in dry["unmatched_events"][:8]:
            print(f"- {event['home_team']} vs {event['away_team']} ({event.get('commence_time', '?')})")

    if dry["records_matched"] == 0:
        print("No matching odds available yet. This is normal before markets are published.")
        return 0

    print("Importing matched odds...")
    result = import_the_odds_api(
        sport="soccer_fifa_world_cup",
        regions="us,eu,uk",
        markets="h2h",
        dry_run=False,
    )
    print(f"Status: {result['status']}")
    print(f"Records imported: {result['records_matched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
