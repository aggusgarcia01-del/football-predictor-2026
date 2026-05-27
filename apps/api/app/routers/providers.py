from fastapi import APIRouter

from app.services.api_football_provider import (
    api_football_fixture_detail,
    api_football_live,
    api_football_match_research,
    api_football_training_instructions,
)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/api-football/live")
def get_api_football_live() -> dict:
    return api_football_live()


@router.get("/api-football/fixture/{fixture_id}")
def get_api_football_fixture(fixture_id: int) -> dict:
    return api_football_fixture_detail(fixture_id)


@router.get("/api-football/research")
def get_api_football_research(home_team: str, away_team: str, match_date: str | None = None) -> dict:
    return api_football_match_research(home_team, away_team, match_date)


@router.get("/training")
def get_training_instructions() -> dict:
    return api_football_training_instructions()
