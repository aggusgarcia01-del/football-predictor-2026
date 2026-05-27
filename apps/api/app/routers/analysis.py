from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.schemas import MatchAnalysis, MatchQueryRequest
from app.services.analysis import analyze_match, analyze_question
from app.services.model_health import current_model_health
from app.services.value import fixed_bet_for_match, odds_board_for_match
from app.routers.model import get_match_readiness, get_prediction_trust

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{match_id}", response_model=MatchAnalysis)
def get_match_analysis(match_id: str) -> MatchAnalysis:
    try:
        return analyze_match(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/query", response_model=MatchAnalysis)
def post_match_query(request: MatchQueryRequest) -> MatchAnalysis:
    try:
        return analyze_question(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/query/report", response_class=PlainTextResponse)
def post_match_query_report(request: MatchQueryRequest) -> str:
    try:
        return analyze_question(request).report_markdown
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{match_id}/cockpit")
def get_match_cockpit(match_id: str) -> dict:
    try:
        analysis = analyze_match(match_id)
        return {
            "analysis": analysis.model_dump(),
            "trust": get_prediction_trust(match_id),
            "readiness": get_match_readiness(match_id),
            "fixed_bet": fixed_bet_for_match(match_id).model_dump(),
            "odds_board": odds_board_for_match(match_id),
            "model_health": current_model_health().model_dump(),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
