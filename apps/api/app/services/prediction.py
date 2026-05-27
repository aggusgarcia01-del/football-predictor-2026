from math import exp, factorial

from app.models.schemas import ExactScoreProbability, MarketProbability, MatchView, ModelAdjustment, Prediction
from app.services import data
from app.services.prematch import lineup_multiplier, prematch_status
from app.services.statistical_inputs import adjusted_metric, preferred_adjusted_metric, uncertainty


DISCLAIMER = (
    "Demo statistical model. Not production validated. Past performance does not "
    "guarantee future results. Bet only what you can afford to lose."
)


def _tier(ev: float | None) -> str | None:
    if ev is None or ev <= 0.03:
        return None
    if ev > 0.08:
        return "HIGH CONVICTION"
    if ev >= 0.04:
        return "MEDIUM"
    return "SPECULATIVE"


def _market_with_odds(match_id: str, market: str, probs: dict[str, float]) -> list[MarketProbability]:
    market_odds: dict[str, dict] = {}
    for row in data.odds():
        if row["match_id"] != match_id or row["market"] != market:
            continue
        current = market_odds.get(row["selection"])
        if current is None or float(row["decimal_odds"]) > float(current["decimal_odds"]):
            market_odds[row["selection"]] = row
    result: list[MarketProbability] = []
    for selection, probability in probs.items():
        row = market_odds.get(selection)
        decimal_odds = float(row["decimal_odds"]) if row else None
        implied = 1 / decimal_odds if decimal_odds else None
        ev = probability * decimal_odds - 1 if decimal_odds else None
        result.append(
            MarketProbability(
                selection=selection,
                probability=round(probability, 4),
                odds=decimal_odds,
                implied_probability=round(implied, 4) if implied else None,
                ev=round(ev, 4) if ev is not None else None,
                confidence_tier=_tier(ev),
            )
        )
    return result


def _metric(team_id: str, key: str, fallback: float) -> float:
    return float(data.team_metrics().get(team_id, {}).get(key, fallback))


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _availability_penalty(team_id: str) -> float:
    availability = data.availability().get(team_id, {})
    key_absences = int(availability.get("key_absences", 0))
    fatigue_risk = str(availability.get("fatigue_risk", "low"))
    fatigue_penalty = {"low": 0.0, "medium": 0.03, "high": 0.07}.get(fatigue_risk, 0.0)
    return min(0.18, key_absences * 0.04 + fatigue_penalty)


def _poisson_probability(lam: float, goals: int) -> float:
    return (exp(-lam) * lam**goals) / factorial(goals)


def _dixon_coles_multiplier(home_xg: float, away_xg: float, home_goals: int, away_goals: int, rho: float = -0.06) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1 - (home_xg * away_xg * rho)
    if home_goals == 0 and away_goals == 1:
        return 1 + (home_xg * rho)
    if home_goals == 1 and away_goals == 0:
        return 1 + (away_xg * rho)
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _score_matrix(home_xg: float, away_xg: float, max_goals: int = 7) -> dict[tuple[int, int], float]:
    matrix: dict[tuple[int, int], float] = {}
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            base_probability = _poisson_probability(home_xg, home_goals) * _poisson_probability(
                away_xg,
                away_goals,
            )
            matrix[(home_goals, away_goals)] = base_probability * _dixon_coles_multiplier(
                home_xg,
                away_xg,
                home_goals,
                away_goals,
            )

    # Normalize truncated tail so market probabilities sum to 1.
    total = sum(matrix.values())
    return {score: probability / total for score, probability in matrix.items()}


def _line_probability(matrix: dict[tuple[int, int], float], line: float, over: bool) -> float:
    if over:
        return sum(probability for (home, away), probability in matrix.items() if home + away > line)
    return sum(probability for (home, away), probability in matrix.items() if home + away < line)


def _btts_probability(matrix: dict[tuple[int, int], float]) -> float:
    return sum(probability for (home, away), probability in matrix.items() if home > 0 and away > 0)


def _top_scores(matrix: dict[tuple[int, int], float], limit: int = 6) -> list[ExactScoreProbability]:
    ranked = sorted(matrix.items(), key=lambda item: item[1], reverse=True)[:limit]
    return [
        ExactScoreProbability(score=f"{home}-{away}", probability=round(probability, 4))
        for (home, away), probability in ranked
    ]


def _predict_view(view: MatchView, odds_match_id: str | None = None) -> Prediction:
    analysis_match_id = odds_match_id or view.id
    elo_diff = view.home_team.elo - view.away_team.elo

    home_attack, home_attack_rel, home_attack_source, home_attack_key = preferred_adjusted_metric(view.home_team.id, "npxg_for_per90")
    away_attack, away_attack_rel, away_attack_source, away_attack_key = preferred_adjusted_metric(view.away_team.id, "npxg_for_per90")
    home_defense_allowed, home_def_rel, home_def_source, home_def_key = preferred_adjusted_metric(view.home_team.id, "npxg_against_per90")
    away_defense_allowed, away_def_rel, away_def_source, away_def_key = preferred_adjusted_metric(view.away_team.id, "npxg_against_per90")
    home_form, home_form_rel, _ = adjusted_metric(view.home_team.id, "recent_form_points_per_match")
    away_form, away_form_rel, _ = adjusted_metric(view.away_team.id, "recent_form_points_per_match")
    home_sot, _, _ = adjusted_metric(view.home_team.id, "shots_on_target_for_per90")
    away_sot, _, _ = adjusted_metric(view.away_team.id, "shots_on_target_for_per90")
    home_clean_sheet, _, _ = adjusted_metric(view.home_team.id, "clean_sheet_rate")
    away_clean_sheet, _, _ = adjusted_metric(view.away_team.id, "clean_sheet_rate")
    home_failed_to_score, _, _ = adjusted_metric(view.home_team.id, "failed_to_score_rate")
    away_failed_to_score, _, _ = adjusted_metric(view.away_team.id, "failed_to_score_rate")
    average_uncertainty = (uncertainty(view.home_team.id) + uncertainty(view.away_team.id)) / 2

    elo_home_multiplier = 1 + _bounded(elo_diff / 1800, -0.18, 0.18)
    elo_away_multiplier = 1 - _bounded(elo_diff / 1800, -0.18, 0.18)
    form_home_multiplier = 1 + _bounded((home_form - away_form) * 0.04, -0.08, 0.08)
    form_away_multiplier = 1 - _bounded((home_form - away_form) * 0.04, -0.08, 0.08)
    home_shot_pressure = 1 + _bounded((home_sot - 4.0) * 0.025, -0.08, 0.08)
    away_shot_pressure = 1 + _bounded((away_sot - 4.0) * 0.025, -0.08, 0.08)
    home_finishing_resilience = 1 - _bounded((home_failed_to_score - 0.22) * 0.12, -0.04, 0.06)
    away_finishing_resilience = 1 - _bounded((away_failed_to_score - 0.22) * 0.12, -0.04, 0.06)
    home_defensive_suppression = 1 - _bounded((away_clean_sheet - 0.28) * 0.18, -0.06, 0.06)
    away_defensive_suppression = 1 - _bounded((home_clean_sheet - 0.28) * 0.18, -0.06, 0.06)

    altitude_goal_multiplier = 0.92 if view.venue.altitude_meters > 1500 else 1.0
    home_availability_multiplier = 1 - _availability_penalty(view.home_team.id)
    away_availability_multiplier = 1 - _availability_penalty(view.away_team.id)
    home_lineup_multiplier, home_lineup_description = lineup_multiplier(analysis_match_id, view.home_team.id)
    away_lineup_multiplier, away_lineup_description = lineup_multiplier(analysis_match_id, view.away_team.id)

    expected_home = (
        ((home_attack * 0.62) + (away_defense_allowed * 0.38))
        * elo_home_multiplier
        * form_home_multiplier
        * altitude_goal_multiplier
        * home_availability_multiplier
        * home_lineup_multiplier
        * home_shot_pressure
        * home_finishing_resilience
        * home_defensive_suppression
    )
    expected_away = (
        ((away_attack * 0.62) + (home_defense_allowed * 0.38))
        * elo_away_multiplier
        * form_away_multiplier
        * altitude_goal_multiplier
        * away_availability_multiplier
        * away_lineup_multiplier
        * away_shot_pressure
        * away_finishing_resilience
        * away_defensive_suppression
    )

    expected_home = max(0.15, expected_home)
    expected_away = max(0.15, expected_away)

    matrix = _score_matrix(expected_home, expected_away)
    home = sum(probability for (home_goals, away_goals), probability in matrix.items() if home_goals > away_goals)
    draw = sum(probability for (home_goals, away_goals), probability in matrix.items() if home_goals == away_goals)
    away = sum(probability for (home_goals, away_goals), probability in matrix.items() if home_goals < away_goals)
    over_25 = _line_probability(matrix, 2.5, over=True)
    btts_yes = _btts_probability(matrix)
    double_chance = {
        "1X": home + draw,
        "12": home + away,
        "X2": draw + away,
    }

    adjustments = [
        ModelAdjustment(
            name="ELO prior",
            value=f"{elo_diff:+d} rating gap",
            effect=f"home xG multiplier {elo_home_multiplier:.3f}, away xG multiplier {elo_away_multiplier:.3f}",
        ),
        ModelAdjustment(
            name="xG blend",
            value=(
                f"{view.home_team.name} attack {home_attack:.2f} vs {view.away_team.name} conceded {away_defense_allowed:.2f}; "
                f"{view.away_team.name} attack {away_attack:.2f} vs {view.home_team.name} conceded {home_defense_allowed:.2f}"
            ),
            effect=(
                "base expected goals are built from attack and opponent defensive allowance; "
                f"reliability H attack {home_attack_rel:.2f}, H defense {home_def_rel:.2f}, "
                f"A attack {away_attack_rel:.2f}, A defense {away_def_rel:.2f}; "
                f"fields {home_attack_key}/{away_attack_key} and {home_def_key}/{away_def_key}"
            ),
        ),
        ModelAdjustment(
            name="Stat source reliability",
            value=(
                f"{view.home_team.name}: {home_attack_source}; "
                f"{view.away_team.name}: {away_attack_source}"
            ),
            effect="weak or missing statistical inputs are shrunk toward global international baselines",
        ),
        ModelAdjustment(
            name="Recent form",
            value=f"{home_form:.2f} vs {away_form:.2f} points per match proxy",
            effect=(
                f"home form multiplier {form_home_multiplier:.3f}, away form multiplier {form_away_multiplier:.3f}; "
                f"reliability {home_form_rel:.2f}/{away_form_rel:.2f}"
            ),
        ),
        ModelAdjustment(
            name="Shot pressure and defensive resistance",
            value=(
                f"SOT {view.home_team.name} {home_sot:.2f}, {view.away_team.name} {away_sot:.2f}; "
                f"clean sheets {view.home_team.name} {home_clean_sheet:.2f}, {view.away_team.name} {away_clean_sheet:.2f}; "
                f"failed to score {view.home_team.name} {home_failed_to_score:.2f}, {view.away_team.name} {away_failed_to_score:.2f}"
            ),
            effect=(
                f"shot multipliers {home_shot_pressure:.3f}/{away_shot_pressure:.3f}; "
                f"finishing resilience {home_finishing_resilience:.3f}/{away_finishing_resilience:.3f}; "
                f"defensive suppression {home_defensive_suppression:.3f}/{away_defensive_suppression:.3f}"
            ),
        ),
        ModelAdjustment(
            name="Venue altitude",
            value=f"{view.venue.altitude_meters}m",
            effect=f"goals multiplier {altitude_goal_multiplier:.2f}",
        ),
        ModelAdjustment(
            name="Availability",
            value="key absences and fatigue risk from local seed profile",
            effect=(
                f"home multiplier {home_availability_multiplier:.3f}, "
                f"away multiplier {away_availability_multiplier:.3f}"
            ),
        ),
        ModelAdjustment(
            name="Lineup quality and freshness",
            value=(
                f"{view.home_team.name}: {home_lineup_description}; "
                f"{view.away_team.name}: {away_lineup_description}"
            ),
            effect=(
                f"home lineup multiplier {home_lineup_multiplier:.3f}, "
                f"away lineup multiplier {away_lineup_multiplier:.3f}"
            ),
        ),
    ]

    return Prediction(
        match=view,
        status="DEMO_NOT_PRODUCTION_VALIDATED",
        disclaimer=DISCLAIMER,
        expected_goals_home=round(expected_home, 2),
        expected_goals_away=round(expected_away, 2),
        markets={
            "1X2": _market_with_odds(
                odds_match_id or "",
                "1X2",
                {"Home": home, "Draw": draw, "Away": away},
            ),
            "Double Chance": _market_with_odds(
                odds_match_id or "",
                "Double Chance",
                double_chance,
            ),
            "Over/Under 2.5": _market_with_odds(
                odds_match_id or "",
                "Over/Under 2.5",
                {"Over 2.5": over_25, "Under 2.5": 1 - over_25},
            ),
            "BTTS": _market_with_odds(
                odds_match_id or "",
                "BTTS",
                {"Yes": btts_yes, "No": 1 - btts_yes},
            ),
        },
        top_exact_scores=_top_scores(matrix),
        adjustments=adjustments,
        prematch_status=prematch_status(analysis_match_id, view.home_team.id, view.away_team.id),
        model_notes=[
            "Local no-Docker model: JSON seed data plus deterministic Python calculations.",
            "Score probabilities use a Poisson matrix with a Dixon-Coles low-score correction, truncated at 7 goals and normalized.",
            "Lineup data is used when available; confirmed lineups should be imported 30-40 minutes before kickoff.",
            f"Average statistical uncertainty for this match: {average_uncertainty:.2f}; high uncertainty reduces betting confidence.",
            "This is stronger than the initial scaffold, but still not calibrated on verified historical datasets.",
        ],
    )


def predict_match(match_id: str) -> Prediction:
    match = data.matches().get(match_id)
    if match is None:
        raise KeyError(match_id)

    return _predict_view(data.match_view(match), match_id)


def predict_team_pair(home_team_id: str, away_team_id: str, venue_id: str = "v04") -> Prediction:
    teams = data.teams()
    venues = data.venues()
    if home_team_id not in teams or away_team_id not in teams:
        raise KeyError("Unknown team id.")
    if venue_id not in venues:
        raise KeyError("Unknown venue id.")

    view = MatchView(
        id=f"custom-{home_team_id}-{away_team_id}",
        date="custom",
        stage="Custom analysis",
        home_team=teams[home_team_id],
        away_team=teams[away_team_id],
        venue=venues[venue_id],
    )
    return _predict_view(view, None)
