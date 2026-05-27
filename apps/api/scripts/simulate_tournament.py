import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.simulation import run_tournament_simulation


def main() -> int:
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    result = run_tournament_simulation(iterations=iterations)
    print(f"Simulation status: {result.status}")
    print(f"Iterations: {result.iterations}")
    for team in result.teams:
        print(
            f"{team.team_name}: win {team.win_world_cup:.1%}, "
            f"final {team.final:.1%}, semis {team.semi_finals:.1%}, "
            f"R16 {team.round_of_16:.1%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
