import unicodedata

from app.models.schemas import EvidenceItem, MatchAnalysis, MatchQueryRequest
from app.services import data
from app.services.prediction import predict_match, predict_team_pair
from app.services.statistical_inputs import preferred_adjusted_metric, reliability
from app.services.value import fixed_bet_for_match


def _fmt_pct(value: float) -> str:
    return f"{round(value * 100, 1)}%"


def _fmt_signed(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{round(value, 2)}"


def _normalize(value: str) -> str:
    cleaned = unicodedata.normalize("NFKD", value)
    return "".join(char for char in cleaned if not unicodedata.combining(char)).lower()


def _selection_name(selection: str, home: str, away: str) -> str:
    return {
        "Home": home,
        "Draw": "Empate",
        "Away": away,
    }.get(selection, selection)


def _format_report(analysis: MatchAnalysis) -> str:
    prediction = analysis.prediction
    match = analysis.resolved_match
    home = match.home_team.name
    away = match.away_team.name
    one_x_two = prediction.markets["1X2"]
    lines = [
        f"# {home} vs {away}",
        "",
        f"Estado: {prediction.status}",
        "",
        "## Pronostico",
        f"- Goles esperados: {home} {prediction.expected_goals_home} - {away} {prediction.expected_goals_away}",
    ]

    for row in one_x_two:
        ev_text = f", EV {_fmt_pct(row.ev)}" if row.ev is not None else ""
        odds_text = f", odds {row.odds}" if row.odds is not None else ""
        selection_label = _selection_name(row.selection, home, away)
        lines.append(f"- {selection_label}: {_fmt_pct(row.probability)}{odds_text}{ev_text}")

    lines.extend(["", "## Marcadores exactos mas probables"])
    for row in prediction.top_exact_scores:
        lines.append(f"- {row.score}: {_fmt_pct(row.probability)}")

    lines.extend(["", "## Estado prepartido"])
    lines.append(f"- Readiness: {prediction.prematch_status.overall_readiness}")
    lines.append(
        f"- {home} lineup: {prediction.prematch_status.home_lineup_status} "
        f"({prediction.prematch_status.home_lineup_freshness})"
    )
    lines.append(
        f"- {away} lineup: {prediction.prematch_status.away_lineup_status} "
        f"({prediction.prematch_status.away_lineup_freshness})"
    )
    lines.extend(f"- {note}" for note in prediction.prematch_status.notes)

    lines.extend(["", "## Evidencias"])
    for item in analysis.evidence:
        lines.append(f"- {item.category}: {item.signal}. {item.value}. Impacto: {item.impact}")

    lines.extend(["", "## Razonamiento"])
    lines.extend(f"- {item}" for item in analysis.reasoning)
    if match.id in data.matches():
        fixed = fixed_bet_for_match(match.id)
        lines.extend(["", "## Apuesta fija"])
        lines.append(f"- Estado: {fixed.status}")
        lines.append(f"- Seleccion: {_selection_name(fixed.selection, home, away)} ({_fmt_pct(fixed.model_probability)})")
        if fixed.best_odds:
            lines.append(f"- Mejor cuota importada: {fixed.best_bookmaker} @ {fixed.best_odds}, EV {_fmt_pct(fixed.ev or 0)}")
            lines.append(f"- Kelly fraccional sugerido: {_fmt_pct(fixed.recommended_fractional_kelly)}")
        lines.extend(f"- {item}" for item in fixed.rationale)
    lines.extend(["", "## Recomendacion", analysis.recommendation])
    lines.extend(["", "## Limitaciones"])
    lines.extend(f"- {item}" for item in analysis.limitations)
    return "\n".join(lines)


def _team_metric(team_id: str, key: str, fallback: float = 0.0) -> float:
    return float(data.team_metrics().get(team_id, {}).get(key, fallback))


def _metric_label(metrics: dict, key: str, fallback: float) -> str:
    if key in metrics:
        return str(metrics[key])
    return f"{fallback} fallback"


def _availability_label(availability: dict) -> tuple[str, str]:
    return (
        str(availability.get("key_absences", 0)),
        str(availability.get("fatigue_risk", "unknown")),
    )


def _team_hits_from_question(question: str) -> list[str]:
    normalized = _normalize(question)
    hits: list[tuple[int, str]] = []
    for team_id, team in data.teams().items():
        aliases = [team_id.lower(), _normalize(team.name)]
        aliases.extend(_normalize(alias) for alias in data.team_aliases().get(team_id, []))
        positions = [normalized.find(alias) for alias in aliases if alias and normalized.find(alias) >= 0]
        if positions:
            hits.append((min(positions), team_id))
    return [team_id for _, team_id in sorted(hits, key=lambda item: item[0])]


def _resolve_match_from_question(question: str) -> str:
    normalized = _normalize(question)
    team_hits = [
        team_id for team_id in _team_hits_from_question(question)
    ]

    for match in data.matches().values():
        if match.home_team_id in team_hits and match.away_team_id in team_hits:
            return match.id

    for match_id in data.matches():
        if match_id.lower() in normalized:
            return match_id

    raise KeyError("No seeded match could be resolved from the question.")


def analyze_match(match_id: str, question: str | None = None) -> MatchAnalysis:
    prediction = predict_match(match_id)
    return _analysis_from_prediction(prediction, question)


def _analysis_from_prediction(prediction, question: str | None = None) -> MatchAnalysis:
    match = prediction.match
    home = match.home_team
    away = match.away_team
    home_metrics = data.team_metrics().get(home.id, {})
    away_metrics = data.team_metrics().get(away.id, {})
    home_availability = data.availability().get(home.id, {})
    away_availability = data.availability().get(away.id, {})

    elo_gap = home.elo - away.elo
    npxg_gap = _team_metric(home.id, "npxg_for_per90", 1.35) - _team_metric(away.id, "npxg_for_per90", 1.15)
    defensive_gap = _team_metric(away.id, "npxg_against_per90", 1.10) - _team_metric(home.id, "npxg_against_per90", 1.10)
    form_gap = _team_metric(home.id, "recent_form_points_per_match", 1.5) - _team_metric(
        away.id,
        "recent_form_points_per_match",
        1.5,
    )
    home_absences, home_fatigue = _availability_label(home_availability)
    away_absences, away_fatigue = _availability_label(away_availability)
    home_stat_reliability = reliability(home_metrics)
    away_stat_reliability = reliability(away_metrics)
    home_adj_attack, _, _, home_attack_key = preferred_adjusted_metric(home.id, "npxg_for_per90")
    away_adj_attack, _, _, away_attack_key = preferred_adjusted_metric(away.id, "npxg_for_per90")

    best_market = max(
        prediction.markets["1X2"],
        key=lambda row: row.probability,
    )
    positive_ev = [
        row
        for row in prediction.markets["1X2"]
        if row.ev is not None and row.ev > 0.03
    ]
    altitude_impact = (
        "Altitude above 1500m reduces expected goals in the model."
        if match.venue.altitude_meters > 1500
        else "No altitude penalty applied; venue is below the 1500m threshold."
    )

    evidence = [
        EvidenceItem(
            category="Team strength",
            signal="International ELO prior",
            source="teams.json seed profile",
            value=f"{home.name} {home.elo} vs {away.name} {away.elo} ({_fmt_signed(elo_gap)} gap)",
            impact="Raises the baseline probability for the higher-rated side.",
            confidence="medium_demo",
        ),
        EvidenceItem(
            category="Chance creation",
            signal="npxG for per 90, opponent-adjusted when available",
            source=str(home_metrics.get("source", "missing")) + " / " + str(away_metrics.get("source", "missing")),
            value=f"{home.name} {_metric_label(home_metrics, 'npxg_for_per90', 1.35)} vs {away.name} {_metric_label(away_metrics, 'npxg_for_per90', 1.15)}",
            impact=(
                f"Raw attacking gap: {_fmt_signed(npxg_gap)} npxG/90. "
                f"Reliability-adjusted attack: {home.name} {home_adj_attack:.2f}, {away.name} {away_adj_attack:.2f}. "
                f"Model fields: {home_attack_key}/{away_attack_key}."
            ),
            confidence=str(home_metrics.get("data_quality", "missing")),
        ),
        EvidenceItem(
            category="Sample quality",
            signal="Recency, sample size and opponent level",
            source="StatsBomb sync metadata or manual import metadata",
            value=(
                f"{home.name}: {home_metrics.get('sample_size_matches', 0)} matches, "
                f"{home_metrics.get('sample_start', 'n/a')} to {home_metrics.get('sample_end', 'n/a')}, "
                f"avg opp ELO {home_metrics.get('average_opponent_elo', 'n/a')}; "
                f"{away.name}: {away_metrics.get('sample_size_matches', 0)} matches, "
                f"{away_metrics.get('sample_start', 'n/a')} to {away_metrics.get('sample_end', 'n/a')}, "
                f"avg opp ELO {away_metrics.get('average_opponent_elo', 'n/a')}"
            ),
            impact="Better samples get more weight; weak or old samples are shrunk toward baseline.",
            confidence="model_internal",
        ),
        EvidenceItem(
            category="Data quality",
            signal="Statistical input reliability",
            source="source metadata + sample_size_matches",
            value=f"{home.name} reliability {home_stat_reliability:.2f}; {away.name} reliability {away_stat_reliability:.2f}",
            impact="Low reliability forces the model to shrink xG/form inputs toward neutral international baselines.",
            confidence="model_internal",
        ),
        EvidenceItem(
            category="Defensive resistance",
            signal="npxG conceded per 90",
            source=str(home_metrics.get("source", "missing")) + " / " + str(away_metrics.get("source", "missing")),
            value=f"{home.name} {_metric_label(home_metrics, 'npxg_against_per90', 1.10)} vs {away.name} {_metric_label(away_metrics, 'npxg_against_per90', 1.10)}",
            impact=f"Defensive gap favors the team with lower xG conceded by {_fmt_signed(defensive_gap)}.",
            confidence=str(home_metrics.get("data_quality", "missing")),
        ),
        EvidenceItem(
            category="Defensive profile",
            signal="Clean sheet and failed-to-score rates",
            source=str(home_metrics.get("source", "missing")) + " / " + str(away_metrics.get("source", "missing")),
            value=(
                f"{home.name}: clean sheets {home_metrics.get('clean_sheet_rate', 'n/a')}, "
                f"failed to score {home_metrics.get('failed_to_score_rate', 'n/a')}; "
                f"{away.name}: clean sheets {away_metrics.get('clean_sheet_rate', 'n/a')}, "
                f"failed to score {away_metrics.get('failed_to_score_rate', 'n/a')}"
            ),
            impact="These rates slightly suppress or lift expected goals beyond raw xG.",
            confidence=str(home_metrics.get("data_quality", "missing")),
        ),
        EvidenceItem(
            category="Recent form",
            signal="Points per match proxy",
            source=str(home_metrics.get("sample", "missing")),
            value=f"{home.name} {_metric_label(home_metrics, 'recent_form_points_per_match', 1.5)} vs {away.name} {_metric_label(away_metrics, 'recent_form_points_per_match', 1.5)}",
            impact=f"Recent-form proxy gap: {_fmt_signed(form_gap)} points/match.",
            confidence=str(home_metrics.get("data_quality", "missing")),
        ),
        EvidenceItem(
            category="Venue",
            signal="Altitude and environment",
            source="venues.json seed profile",
            value=f"{match.venue.city}: {match.venue.altitude_meters}m, {match.venue.avg_temp_c}C, {match.venue.avg_humidity}% humidity",
            impact=altitude_impact,
            confidence="medium_demo",
        ),
        EvidenceItem(
            category="Availability",
            signal="Key absences and fatigue risk",
            source=str(home_availability.get("source", "missing")) + " / " + str(away_availability.get("source", "missing")),
            value=(
                f"{home.name}: {home_absences} absences, "
                f"{home_fatigue} fatigue; "
                f"{away.name}: {away_absences} absences, "
                f"{away_fatigue} fatigue"
            ),
            impact="Key absences and fatigue risk adjust each team's attacking expectation.",
            confidence="low_demo",
        ),
        EvidenceItem(
            category="Prematch lineups",
            signal="Confirmed/probable XI freshness",
            source="lineups.json plus data/imports/lineups_active.json",
            value=(
                f"{home.name}: {prediction.prematch_status.home_lineup_status} "
                f"({prediction.prematch_status.home_lineup_freshness}); "
                f"{away.name}: {prediction.prematch_status.away_lineup_status} "
                f"({prediction.prematch_status.away_lineup_freshness})"
            ),
            impact="Lineup quality, fitness and expected minutes directly adjust expected goals.",
            confidence=(
                "high_when_confirmed"
                if prediction.prematch_status.overall_readiness == "READY_CONFIRMED_LINEUPS"
                else "medium_or_low_until_confirmed"
            ),
        ),
    ]

    if positive_ev:
        ev_text = ", ".join(
            f"{_selection_name(row.selection, home.name, away.name)} EV {_fmt_pct(row.ev or 0)} at odds {row.odds}"
            for row in positive_ev
        )
    else:
        ev_text = "No +EV 1X2 selection above the 3% threshold in seeded odds."

    reasoning = [
        f"Most likely 1X2 outcome: {_selection_name(best_market.selection, home.name, away.name)} at {_fmt_pct(best_market.probability)} model probability.",
        f"Expected goals: {home.name} {prediction.expected_goals_home} - {away.name} {prediction.expected_goals_away}.",
        f"Market check: {ev_text}",
        "The current result is an evidence report over seeded data, not a live recommendation.",
    ]

    recommendation = (
        f"Lean: {_selection_name(best_market.selection, home.name, away.name)}. Treat as demo-only until real team news, odds history, "
        "calibration, and backtesting are connected."
    )

    analysis = MatchAnalysis(
        question=question,
        resolved_match=match,
        prediction=prediction,
        evidence=evidence,
        reasoning=reasoning,
        recommendation=recommendation,
        report_markdown="",
        limitations=[
            "Seed data is illustrative and not a verified provider feed.",
            "Lineups can be imported manually now; automated live providers are not connected yet.",
            "No automated referee assignment, line movement, or injury provider is connected yet.",
            "The model is not calibrated against historical World Cup, Euro, Copa America, and qualifier data yet.",
            "Bookmaker odds must be imported legally/manually or through an allowed API; the app does not scrape betting sites.",
            "Do not use this output as betting advice until the production validation gate passes.",
        ],
        next_data_needed=[
            "Historical match results with xG and opponent strength.",
            "Historical and live odds snapshots by bookmaker.",
            "Confirmed squads, injuries, expected lineups, and player minutes.",
            "Referee assignments and card profiles.",
        ],
    )
    analysis.report_markdown = _format_report(analysis)
    return analysis


def analyze_question(request: MatchQueryRequest) -> MatchAnalysis:
    try:
        match_id = _resolve_match_from_question(request.question)
        return analyze_match(match_id, request.question)
    except KeyError:
        team_hits = _team_hits_from_question(request.question)
        if len(team_hits) >= 2:
            prediction = predict_team_pair(team_hits[0], team_hits[1])
            return _analysis_from_prediction(prediction, request.question)
        raise
