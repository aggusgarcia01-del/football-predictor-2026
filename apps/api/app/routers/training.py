from fastapi import APIRouter

from app.services.auto_training import list_training_runs, run_auto_training

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/run")
def post_training_run(include_live_provider: bool = True) -> dict:
    return run_auto_training(include_live_provider=include_live_provider)


@router.get("/runs")
def get_training_runs() -> list[dict]:
    return list_training_runs()
