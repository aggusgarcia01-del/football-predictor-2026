import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.value import all_value_bets


def main() -> int:
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
    opportunities = all_value_bets(threshold)
    if not opportunities:
        print("No +EV opportunities above threshold.")
        return 0

    for item in opportunities:
        print(
            f"{item.match.home_team.name} vs {item.match.away_team.name} | "
            f"{item.market} {item.selection} | P={item.model_probability:.1%} | "
            f"odds={item.odds:.2f} | EV={item.ev:.1%} | stake={item.recommended_fractional_kelly:.2%} | "
            f"{item.confidence_tier}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
