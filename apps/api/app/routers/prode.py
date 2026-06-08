from fastapi import APIRouter

from app.models.schemas import ProdeBoard
from app.services.prode import prode_predictions

router = APIRouter(prefix="/prode", tags=["prode"])


@router.get("/predictions", response_model=ProdeBoard)
def get_prode_predictions() -> ProdeBoard:
    return prode_predictions()
