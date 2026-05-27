from fastapi import APIRouter

from app.models.schemas import GenericMatchResearchRequest, GenericMatchResearchResult
from app.services.generic_research import research_generic_match

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/match", response_model=GenericMatchResearchResult)
def post_research_match(request: GenericMatchResearchRequest) -> GenericMatchResearchResult:
    return research_generic_match(request)
