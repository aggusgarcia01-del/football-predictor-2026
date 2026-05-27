import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import LineupImportRequest
from app.services.prematch import import_lineups


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/import_lineups.py path\\to\\lineups.json")
        return 1

    path = Path(sys.argv[1]).resolve()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    result = import_lineups(LineupImportRequest(**payload))
    print(f"Lineups received: {result.lineups_received}")
    print(f"Lineups written: {result.lineups_written}")
    print(f"Output file: {result.output_file}")
    print(f"Status: {result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
