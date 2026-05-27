from fastapi import APIRouter, HTTPException

from app.models.schemas import ModelHealth
from app.services import data
from app.services.calibration import seed_calibration_report
from app.services.model_health import current_model_health
from app.services.prematch import prematch_status
from app.services.prediction import predict_match
from app.services.statistical_inputs import reliability
from app.services.value import fixed_bet_for_match

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/health", response_model=ModelHealth)
def get_model_health() -> ModelHealth:
    return current_model_health()


@router.get("/calibration")
def get_model_calibration(dataset: str = "seed_backtest_demo") -> dict:
    return seed_calibration_report(dataset)


@router.get("/match-readiness/{match_id}")
def get_match_readiness(match_id: str) -> dict:
    match = data.matches().get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Unknown match_id: {match_id}")

    home_metrics = data.team_metrics().get(match.home_team_id)
    away_metrics = data.team_metrics().get(match.away_team_id)
    home_reliability = reliability(home_metrics)
    away_reliability = reliability(away_metrics)
    odds_rows = [row for row in data.odds() if row.get("match_id") == match_id]
    status = prematch_status(match_id, match.home_team_id, match.away_team_id)
    fixed = fixed_bet_for_match(match_id)

    blockers: list[str] = []
    if home_reliability < 0.55:
        blockers.append("Home team statistical reliability is below 0.55.")
    if away_reliability < 0.55:
        blockers.append("Away team statistical reliability is below 0.55.")
    if len(odds_rows) < 3:
        blockers.append("Import real 1X2 odds for Home, Draw and Away.")
    if status.overall_readiness != "READY_CONFIRMED_LINEUPS":
        blockers.append("Confirmed lineups are not active yet.")

    return {
        "match_id": match_id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "data_reliability": {
            "home": home_reliability,
            "away": away_reliability,
            "average": round((home_reliability + away_reliability) / 2, 4),
        },
        "odds_rows_imported": len(odds_rows),
        "prematch_readiness": status.model_dump(),
        "fixed_bet_status": fixed.status,
        "fixed_bet_confidence": fixed.confidence_tier,
        "blockers": blockers,
        "ready_for_strong_opinion": not blockers,
    }


@router.get("/trust/{match_id}")
def get_prediction_trust(match_id: str) -> dict:
    match = data.matches().get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Unknown match_id: {match_id}")

    prediction = predict_match(match_id)
    readiness = get_match_readiness(match_id)
    health = current_model_health()
    one_x_two = prediction.markets["1X2"]
    top = max(one_x_two, key=lambda row: row.probability)
    second = sorted(one_x_two, key=lambda row: row.probability, reverse=True)[1]
    margin = top.probability - second.probability

    data_score = readiness["data_reliability"]["average"] * 35
    lineup_score = 20 if readiness["prematch_readiness"]["overall_readiness"] == "READY_CONFIRMED_LINEUPS" else 10
    odds_score = 15 if readiness["odds_rows_imported"] >= 3 else 0
    validation_score = 15 if health.matches_evaluated >= 50 and health.brier_score and health.brier_score < 0.6 else 6
    separation_score = min(15, max(0, margin * 75))
    score = round(data_score + lineup_score + odds_score + validation_score + separation_score, 1)

    if score >= 75:
        grade = "HIGH_TRUST"
    elif score >= 58:
        grade = "MEDIUM_TRUST"
    elif score >= 42:
        grade = "LOW_TRUST"
    else:
        grade = "RESEARCH_ONLY"

    return {
        "match_id": match_id,
        "trust_score": score,
        "trust_grade": grade,
        "top_selection": top.selection,
        "top_probability": top.probability,
        "probability_margin_vs_second": round(margin, 4),
        "components": {
            "data_score": round(data_score, 1),
            "lineup_score": lineup_score,
            "odds_score": odds_score,
            "validation_score": validation_score,
            "separation_score": round(separation_score, 1),
        },
        "blockers": readiness["blockers"],
        "interpretation": [
            "HIGH_TRUST still does not mean guaranteed; it means data, lineups, odds and validation are aligned.",
            "A narrow probability margin lowers trust even when the top selection is slightly favored.",
            "For betting, only consider a selection when trust is medium/high and fixed-bet status is favorable.",
        ],
    }
