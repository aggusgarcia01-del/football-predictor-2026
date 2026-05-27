#!/usr/bin/env python3
"""
Sync a broader StatsBomb Open Data sample.

Run from apps/api:
  .\\.venv\\Scripts\\python.exe scripts\\sync_statsbomb_full.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import StatsBombCompetitionSelection, StatsBombSyncRequest
from app.services.statsbomb_sync import sync_statsbomb_metrics


COMPETITIONS = [
    StatsBombCompetitionSelection(competition_id=43, season_id=106, label="FIFA World Cup 2022"),
    StatsBombCompetitionSelection(competition_id=55, season_id=282, label="UEFA Euro 2024"),
    StatsBombCompetitionSelection(competition_id=223, season_id=282, label="Copa America 2024"),
    StatsBombCompetitionSelection(competition_id=43, season_id=3, label="FIFA World Cup 2018"),
    # Kept as opportunistic: if StatsBomb publishes/changes this path, the sync will use it.
    StatsBombCompetitionSelection(competition_id=72, season_id=282, label="AFCON 2023"),
]


def main() -> int:
    request = StatsBombSyncRequest(
        competitions=COMPETITIONS,
        max_matches_total=300,
        max_matches_per_team=15,
        recency_decay=0.08,
    )
    print("Syncing expanded StatsBomb Open Data sample...")
    result = sync_statsbomb_metrics(request)
    print(f"Competitions scanned: {result.competitions_scanned}")
    print(f"Matches scanned: {result.matches_scanned}")
    print(f"Matches used: {result.matches_used}")
    print(f"Team records written: {result.records_written}")
    print(f"Status: {result.status}")
    print(f"Output: {result.output_file}")
    for note in result.notes:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
