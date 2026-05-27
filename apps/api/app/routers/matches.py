from fastapi import APIRouter, HTTPException

from app.models.schemas import MatchView, Prediction
from app.services.data import list_match_views
from app.services.prediction import predict_match

router = APIRouter()


@router.get("/matches", response_model=list[MatchView])
def get_matches() -> list[MatchView]:
    return list_match_views()


@router.get("/predictions/{match_id}", response_model=Prediction)
def get_prediction(match_id: str) -> Prediction:
    try:
        return predict_match(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match not found") from exc

