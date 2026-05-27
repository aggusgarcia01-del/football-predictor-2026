import json
from pathlib import Path

from app.models.schemas import ImportDatasetRequest, ImportDatasetResult
from app.services import data


ROOT = Path(__file__).resolve().parents[4]
IMPORT_DIR = ROOT / "data" / "imports"
ALLOWED_DATASETS = {
    "teams",
    "matches",
    "venues",
    "odds",
    "team_metrics",
    "availability",
    "historical_results",
}
MERGE_KEYS = {
    "odds": ("match_id", "bookmaker", "market", "selection"),
    "team_metrics": ("team_id",),
    "availability": ("team_id",),
}
ONE_X_TWO_SELECTIONS = {"Home", "Draw", "Away"}


def _require(row: dict, key: str, dataset_type: str) -> None:
    if key not in row or row[key] in {None, ""}:
        raise ValueError(f"{dataset_type}: missing required field '{key}'.")


def _as_float(row: dict, key: str, dataset_type: str, minimum: float | None = None) -> float:
    _require(row, key, dataset_type)
    try:
        value = float(row[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{dataset_type}: field '{key}' must be numeric.") from exc
    if minimum is not None and value <= minimum:
        raise ValueError(f"{dataset_type}: field '{key}' must be greater than {minimum}.")
    return value


def _validate_odds(records: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for row in records:
        _require(row, "match_id", "odds")
        _require(row, "market", "odds")
        _require(row, "selection", "odds")
        odds = _as_float(row, "decimal_odds", "odds", minimum=1.0)
        market = str(row["market"])
        selection = str(row["selection"])
        if market == "1X2" and selection not in ONE_X_TWO_SELECTIONS:
            raise ValueError("odds: 1X2 selection must be Home, Draw or Away.")
        normalized_row = dict(row)
        normalized_row["bookmaker"] = str(row.get("bookmaker") or "Manual")
        normalized_row["decimal_odds"] = round(odds, 4)
        normalized.append(normalized_row)
    return normalized


def _validate_team_metrics(records: list[dict]) -> list[dict]:
    numeric_fields = {
        "sample_size_matches",
        "npxg_for_per90",
        "npxg_against_per90",
        "opponent_adjusted_npxg_for_per90",
        "opponent_adjusted_npxg_against_per90",
        "shots_on_target_for_per90",
        "recent_form_points_per_match",
        "clean_sheet_rate",
        "failed_to_score_rate",
    }
    normalized: list[dict] = []
    valid_team_ids = set(data.teams())
    for row in records:
        _require(row, "team_id", "team_metrics")
        if row["team_id"] not in valid_team_ids:
            raise ValueError(f"team_metrics: unknown team_id '{row['team_id']}'.")
        normalized_row = dict(row)
        for key in numeric_fields:
            if key in normalized_row and normalized_row[key] not in {None, ""}:
                normalized_row[key] = float(normalized_row[key])
        normalized.append(normalized_row)
    return normalized


def _validate_records(dataset_type: str, records: list[dict]) -> list[dict]:
    if dataset_type == "odds":
        return _validate_odds(records)
    if dataset_type == "team_metrics":
        return _validate_team_metrics(records)
    return records


def _merge_existing(dataset_type: str, incoming: list[dict]) -> list[dict]:
    keys = MERGE_KEYS.get(dataset_type)
    if not keys:
        return incoming

    output = IMPORT_DIR / f"{dataset_type}.json"
    if output.exists():
        with output.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
    else:
        existing = []

    incoming_keys = {tuple(row.get(key) for key in keys) for row in incoming}
    merged = [
        row
        for row in existing
        if tuple(row.get(key) for key in keys) not in incoming_keys
    ]
    merged.extend(incoming)
    return merged


def import_dataset(dataset_type: str, request: ImportDatasetRequest) -> ImportDatasetResult:
    if dataset_type not in ALLOWED_DATASETS:
        raise KeyError(f"Unsupported dataset_type: {dataset_type}")

    incoming = _validate_records(dataset_type, request.records)

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = IMPORT_DIR / f"{dataset_type}.json"
    records = _merge_existing(dataset_type, incoming)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)

    data.clear_caches()
    return ImportDatasetResult(
        dataset_type=dataset_type,
        records_received=len(request.records),
        records_written=len(records),
        output_file=str(output),
        status="IMPORTED_LOCAL_JSON_ACTIVE_FOR_SUPPORTED_DATASETS",
    )
