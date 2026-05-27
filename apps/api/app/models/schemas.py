from pydantic import BaseModel


class Team(BaseModel):
    id: str
    name: str
    confederation: str
    elo: int


class Venue(BaseModel):
    id: str
    city: str
    country: str
    altitude_meters: int
    avg_temp_c: int
    avg_humidity: int
    surface_type: str


class Match(BaseModel):
    id: str
    home_team_id: str
    away_team_id: str
    date: str
    stage: str
    venue_id: str
    is_neutral_ground: bool


class MatchView(BaseModel):
    id: str
    date: str
    stage: str
    home_team: Team
    away_team: Team
    venue: Venue


class MarketProbability(BaseModel):
    selection: str
    probability: float
    odds: float | None = None
    implied_probability: float | None = None
    ev: float | None = None
    confidence_tier: str | None = None


class ExactScoreProbability(BaseModel):
    score: str
    probability: float


class ModelAdjustment(BaseModel):
    name: str
    value: str
    effect: str


class PrematchStatus(BaseModel):
    home_lineup_status: str
    away_lineup_status: str
    home_lineup_updated_at: str | None
    away_lineup_updated_at: str | None
    home_lineup_freshness: str
    away_lineup_freshness: str
    overall_readiness: str
    notes: list[str]


class Prediction(BaseModel):
    match: MatchView
    status: str
    disclaimer: str
    expected_goals_home: float
    expected_goals_away: float
    markets: dict[str, list[MarketProbability]]
    top_exact_scores: list[ExactScoreProbability]
    adjustments: list[ModelAdjustment]
    prematch_status: PrematchStatus
    model_notes: list[str]


class MatchQueryRequest(BaseModel):
    question: str


class GenericMatchResearchRequest(BaseModel):
    home_team: str
    away_team: str
    match_date: str | None = None
    competition: str | None = None


class GenericPredictionSelection(BaseModel):
    market: str
    selection: str
    probability: float
    fair_odds: float
    minimum_odds_for_value: float


class GenericMatchResearchResult(BaseModel):
    status: str
    home_team: str
    away_team: str
    match_date: str | None
    data_sources: list[str]
    expected_goals_home: float | None = None
    expected_goals_away: float | None = None
    probabilities: list[GenericPredictionSelection]
    confidence: str
    evidence: list[str]
    limitations: list[str]
    next_steps: list[str]


class EvidenceItem(BaseModel):
    category: str
    signal: str
    source: str
    value: str
    impact: str
    confidence: str


class MatchAnalysis(BaseModel):
    question: str | None = None
    resolved_match: MatchView
    prediction: Prediction
    evidence: list[EvidenceItem]
    reasoning: list[str]
    recommendation: str
    report_markdown: str
    limitations: list[str]
    next_data_needed: list[str]


class ValueOpportunity(BaseModel):
    match: MatchView
    market: str
    selection: str
    model_probability: float
    odds: float
    implied_probability: float
    ev: float
    kelly_fraction: float
    recommended_fractional_kelly: float
    confidence_tier: str
    status: str


class BacktestResult(BaseModel):
    dataset: str
    matches_evaluated: int
    flagged_bets: int
    roi: float
    brier_score: float
    log_loss: float
    passed_roi_gate: bool
    passed_brier_gate: bool
    passed_log_loss_gate: bool
    production_gate_status: str
    notes: list[str]


class SimulationTeamResult(BaseModel):
    team_id: str
    team_name: str
    exit_group_stage: float
    round_of_16: float
    quarter_finals: float
    semi_finals: float
    final: float
    win_world_cup: float


class TournamentSimulation(BaseModel):
    iterations: int
    status: str
    teams: list[SimulationTeamResult]
    notes: list[str]


class ModelHealth(BaseModel):
    status: str
    brier_score: float | None
    log_loss: float | None
    roi: float | None
    matches_evaluated: int
    alerts: list[str]
    production_gate_status: str


class ImportDatasetRequest(BaseModel):
    records: list[dict]


class ImportDatasetResult(BaseModel):
    dataset_type: str
    records_received: int
    records_written: int
    output_file: str
    status: str


class TeamDataCoverage(BaseModel):
    team_id: str
    team_name: str
    has_team_metrics: bool
    source: str
    source_url: str | None = None
    data_quality: str
    sample_size_matches: int
    reliability: float
    missing_core_metrics: list[str]


class ModelDataCoverage(BaseModel):
    teams_total: int
    teams_with_real_or_manual_metrics: int
    teams_with_demo_or_fallback_metrics: int
    average_reliability: float
    teams: list[TeamDataCoverage]


class StatsBombCompetitionSelection(BaseModel):
    competition_id: int
    season_id: int
    label: str


class StatsBombSyncRequest(BaseModel):
    competitions: list[StatsBombCompetitionSelection] | None = None
    max_matches_total: int = 120
    max_matches_per_team: int = 10
    recency_decay: float = 0.12


class StatsBombSyncResult(BaseModel):
    competitions_scanned: int
    matches_scanned: int
    matches_used: int
    records_written: int
    output_file: str
    source_url: str
    status: str
    notes: list[str]


class BookmakerPrice(BaseModel):
    bookmaker: str
    market: str
    selection: str
    odds: float
    implied_probability: float
    ev: float


class FixedBetCandidate(BaseModel):
    match: MatchView
    market: str
    selection: str
    model_probability: float
    best_odds: float | None
    best_bookmaker: str | None
    implied_probability: float | None
    ev: float | None
    recommended_fractional_kelly: float
    confidence_tier: str
    status: str
    rationale: list[str]
    bookmaker_prices: list[BookmakerPrice]


class LineupPlayer(BaseModel):
    name: str
    position: str
    status: str
    rating: float
    fitness: float = 1.0
    expected_minutes: int = 90
    set_piece_role: str | None = None


class LineupUpdate(BaseModel):
    match_id: str
    team_id: str
    status: str
    source: str
    updated_at: str
    formation: str | None = None
    players: list[LineupPlayer]


class LineupImportRequest(BaseModel):
    lineups: list[LineupUpdate]


class LineupImportResult(BaseModel):
    lineups_received: int
    lineups_written: int
    output_file: str
    status: str
