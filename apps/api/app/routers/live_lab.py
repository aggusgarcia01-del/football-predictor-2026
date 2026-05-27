from fastapi import APIRouter, HTTPException

from app.services.live_lab import list_live_snapshots, live_prediction_snapshot, settle_live_snapshot

router = APIRouter(prefix="/live-lab", tags=["live-lab"])


@router.post("/snapshot")
def post_live_snapshot(payload: dict, save: bool = True) -> dict:
    return live_prediction_snapshot(payload, save=save)


@router.get("/snapshots")
def get_live_snapshots() -> list[dict]:
    return list_live_snapshots()


@router.post("/settle/{snapshot_id}")
def post_settle_live_snapshot(snapshot_id: str, final_home_goals: int, final_away_goals: int) -> dict:
    try:
        return settle_live_snapshot(snapshot_id, final_home_goals, final_away_goals)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown snapshot_id: {snapshot_id}") from exc
