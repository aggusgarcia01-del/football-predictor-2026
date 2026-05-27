import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.backtesting import run_backtest


def main() -> int:
    dataset = sys.argv[1] if len(sys.argv) > 1 else "seed_backtest_demo"
    result = run_backtest(dataset)
    print(f"Dataset: {result.dataset}")
    print(f"Matches evaluated: {result.matches_evaluated}")
    print(f"Flagged bets: {result.flagged_bets}")
    print(f"ROI: {result.roi:.2%}")
    print(f"Brier score: {result.brier_score}")
    print(f"Log loss: {result.log_loss}")
    print(f"Production gate: {result.production_gate_status}")
    for note in result.notes:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
