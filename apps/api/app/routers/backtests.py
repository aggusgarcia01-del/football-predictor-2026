from fastapi import APIRouter

from app.models.schemas import BacktestResult
from app.services.backtesting import run_backtest

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestResult)
def post_run_backtest(dataset: str = "seed_backtest_demo") -> BacktestResult:
    return run_backtest(dataset)
