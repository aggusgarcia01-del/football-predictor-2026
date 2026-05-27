import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import ImportDatasetRequest
from app.services.ingestion import import_dataset


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/import_team_metrics.py path\\to\\team_metrics.json")
        return 1

    path = Path(sys.argv[1]).resolve()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    result = import_dataset("team_metrics", ImportDatasetRequest(**payload))
    print(f"Records received: {result.records_received}")
    print(f"Records written: {result.records_written}")
    print(f"Output file: {result.output_file}")
    print(f"Status: {result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
