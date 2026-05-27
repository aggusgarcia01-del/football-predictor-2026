import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import StatsBombSyncRequest
from app.services.statsbomb_sync import sync_statsbomb_metrics


def main() -> int:
    max_matches = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    max_per_team = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    recency_decay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.12
    result = sync_statsbomb_metrics(
        StatsBombSyncRequest(
            max_matches_total=max_matches,
            max_matches_per_team=max_per_team,
            recency_decay=recency_decay,
        )
    )
    print(f"Competitions scanned: {result.competitions_scanned}")
    print(f"Matches scanned: {result.matches_scanned}")
    print(f"Matches used: {result.matches_used}")
    print(f"Records written: {result.records_written}")
    print(f"Output file: {result.output_file}")
    print(f"Status: {result.status}")
    for note in result.notes:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
