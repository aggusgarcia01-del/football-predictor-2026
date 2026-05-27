from fastapi import APIRouter, HTTPException

from app.models.schemas import ImportDatasetRequest, ImportDatasetResult, ModelDataCoverage, StatsBombSyncRequest, StatsBombSyncResult
from app.services.data_audit import active_data_audit
from app.services.ingestion import import_dataset
from app.services.odds_provider import import_the_odds_api
from app.services.statistical_inputs import coverage
from app.services.statsbomb_sync import sync_statsbomb_metrics

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/import/{dataset_type}", response_model=ImportDatasetResult)
def post_import_dataset(dataset_type: str, request: ImportDatasetRequest) -> ImportDatasetResult:
    try:
        return import_dataset(dataset_type, request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/coverage", response_model=ModelDataCoverage)
def get_data_coverage() -> ModelDataCoverage:
    return coverage()


@router.get("/audit")
def get_data_audit() -> dict:
    return active_data_audit()


@router.post("/statsbomb/sync", response_model=StatsBombSyncResult)
def post_statsbomb_sync(request: StatsBombSyncRequest) -> StatsBombSyncResult:
    return sync_statsbomb_metrics(request)


@router.post("/odds-provider/the-odds-api")
def post_import_the_odds_api(
    sport: str = "soccer_fifa_world_cup",
    regions: str = "us,eu,uk",
    markets: str = "h2h",
    dry_run: bool = False,
) -> dict:
    return import_the_odds_api(sport=sport, regions=regions, markets=markets, dry_run=dry_run)
