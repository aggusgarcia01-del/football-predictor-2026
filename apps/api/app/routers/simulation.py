from fastapi import APIRouter

from app.models.schemas import TournamentSimulation
from app.services.simulation import run_tournament_simulation

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/tournament", response_model=TournamentSimulation)
def get_tournament_simulation(iterations: int = 5000, seed: int = 2026) -> TournamentSimulation:
    return run_tournament_simulation(iterations=iterations, seed=seed)
