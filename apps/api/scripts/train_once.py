import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auto_training import run_auto_training


def main() -> int:
    include_live = "--no-live" not in sys.argv
    result = run_auto_training(include_live_provider=include_live)
    print(f"Training run: {result['id']}")
    print(f"Status: {result['status']}")
    print(f"Rolling Brier: {result['backtests']['rolling_xg']['brier_score']}")
    print(f"Live provider: {result['live_provider_status']}")
    print("Recommendations:")
    for item in result["recommendations"]:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
