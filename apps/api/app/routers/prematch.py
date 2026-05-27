from fastapi import APIRouter, HTTPException

from app.models.schemas import LineupImportRequest, LineupImportResult, PrematchStatus
from app.services import data
from app.services.prematch import import_lineups, prematch_status

router = APIRouter(prefix="/prematch", tags=["prematch"])


@router.get("/{match_id}/status", response_model=PrematchStatus)
def get_prematch_status(match_id: str) -> PrematchStatus:
    match = data.matches().get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return prematch_status(match.id, match.home_team_id, match.away_team_id)


@router.post("/lineups/import", response_model=LineupImportResult)
def post_import_lineups(request: LineupImportRequest) -> LineupImportResult:
    try:
        return import_lineups(request)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
