from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "demo",
        "production_gate": "blocked_until_backtests_pass",
    }

