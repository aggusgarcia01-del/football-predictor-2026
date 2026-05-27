import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import MatchQueryRequest
from app.services.analysis import analyze_question


def main() -> int:
    if len(sys.argv) < 2:
        print('Uso: python scripts/analyze_match.py "Analiza Argentina vs Mexico"')
        return 1

    question = " ".join(sys.argv[1:])
    analysis = analyze_question(MatchQueryRequest(question=question))
    print(analysis.report_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
