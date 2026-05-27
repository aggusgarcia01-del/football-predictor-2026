import random

from app.models.schemas import SimulationTeamResult, TournamentSimulation
from app.services import data
from app.services.prediction import predict_match


def _sample_selection(probabilities: dict[str, float], rng: random.Random) -> str:
    draw = rng.random()
    cumulative = 0.0
    for selection in ("Home", "Draw", "Away"):
        cumulative += probabilities[selection]
        if draw <= cumulative:
            return selection
    return "Away"


def _prediction_probabilities(match_id: str) -> dict[str, float]:
    prediction = predict_match(match_id)
    return {item.selection: item.probability for item in prediction.markets["1X2"]}


def run_tournament_simulation(iterations: int = 5000, seed: int = 2026) -> TournamentSimulation:
    iterations = max(100, min(iterations, 50000))
    rng = random.Random(seed)
    teams = data.teams()
    counters = {
        team_id: {
            "exit_group_stage": 0,
            "round_of_16": 0,
            "quarter_finals": 0,
            "semi_finals": 0,
            "final": 0,
            "win_world_cup": 0,
        }
        for team_id in teams
    }

    scheduled_matches = list(data.matches().values())
    match_probs = {match.id: _prediction_probabilities(match.id) for match in scheduled_matches}

    for _ in range(iterations):
        points = {team_id: 0 for team_id in teams}
        goal_proxy = {team_id: 0.0 for team_id in teams}

        for match in scheduled_matches:
            selection = _sample_selection(match_probs[match.id], rng)
            if selection == "Home":
                points[match.home_team_id] += 3
                goal_proxy[match.home_team_id] += 1
            elif selection == "Away":
                points[match.away_team_id] += 3
                goal_proxy[match.away_team_id] += 1
            else:
                points[match.home_team_id] += 1
                points[match.away_team_id] += 1

        ranked = sorted(
            teams,
            key=lambda team_id: (points[team_id], goal_proxy[team_id], teams[team_id].elo),
            reverse=True,
        )
        qualifiers = ranked[: min(4, len(ranked))]

        for team_id in teams:
            if team_id not in qualifiers:
                counters[team_id]["exit_group_stage"] += 1
            else:
                counters[team_id]["round_of_16"] += 1
                counters[team_id]["quarter_finals"] += 1
                counters[team_id]["semi_finals"] += 1

        bracket = qualifiers[:]
        while len(bracket) > 1:
            next_round: list[str] = []
            for index in range(0, len(bracket), 2):
                a = bracket[index]
                b = bracket[index + 1]
                elo_prob_a = 1 / (1 + 10 ** ((teams[b].elo - teams[a].elo) / 400))
                winner = a if rng.random() <= elo_prob_a else b
                next_round.append(winner)

            for team_id in next_round:
                if len(next_round) == 2:
                    counters[team_id]["final"] += 1
                elif len(next_round) == 1:
                    counters[team_id]["win_world_cup"] += 1
            bracket = next_round

    results = [
        SimulationTeamResult(
            team_id=team_id,
            team_name=team.name,
            exit_group_stage=round(counters[team_id]["exit_group_stage"] / iterations, 4),
            round_of_16=round(counters[team_id]["round_of_16"] / iterations, 4),
            quarter_finals=round(counters[team_id]["quarter_finals"] / iterations, 4),
            semi_finals=round(counters[team_id]["semi_finals"] / iterations, 4),
            final=round(counters[team_id]["final"] / iterations, 4),
            win_world_cup=round(counters[team_id]["win_world_cup"] / iterations, 4),
        )
        for team_id, team in teams.items()
    ]

    return TournamentSimulation(
        iterations=iterations,
        status="DEMO_SIMULATION_NOT_FULL_2026_BRACKET",
        teams=sorted(results, key=lambda row: row.win_world_cup, reverse=True),
        notes=[
            "Uses seeded teams and scheduled matches only, not the full 48-team official draw.",
            "Knockout winners are sampled from ELO probabilities until the full bracket module is connected.",
        ],
    )
