import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.api_football_provider import api_football_live
from app.services.backtesting import run_backtest
from app.services.calibration import seed_calibration_report
from app.services.data_audit import active_data_audit
from app.services.value import prematch_alerts


ROOT = Path(__file__).resolve().parents[4]
RUNS_FILE = ROOT / "data" / "imports" / "training_runs.json"


def _load_runs() -> list[dict[str, Any]]:
    if not RUNS_FILE.exists():
        return []
    with RUNS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_runs(rows: list[dict[str, Any]]) -> None:
    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)


def run_auto_training(include_live_provider: bool = True) -> dict[str, Any]:
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    audit = active_data_audit()
    seed_backtest = run_backtest("seed_backtest_demo").model_dump()
    statsbomb_backtest = run_backtest("statsbomb_open_data").model_dump()
    rolling_backtest = run_backtest("statsbomb_rolling_xg").model_dump()
    calibration = seed_calibration_report()
    alerts = prematch_alerts(limit=10)
    live_provider = api_football_live() if include_live_provider else {"status": "SKIPPED"}

    run = {
        "id": f"training-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "started_at": started_at,
        "finished_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "TRAINING_RUN_COMPLETED",
        "audit_summary": {
            "weak_team_count": audit["weak_team_count"],
            "odds_rows_active": audit["odds_rows_active"],
            "lineups_rows_active": audit["lineups_rows_active"],
            "test_like_odds_rows": len(audit["test_like_odds_rows"]),
            "test_like_lineup_rows": len(audit["test_like_lineup_rows"]),
        },
        "backtests": {
            "seed": seed_backtest,
            "statsbomb": statsbomb_backtest,
            "rolling_xg": rolling_backtest,
        },
        "calibration": calibration,
        "prematch_alert_count": len(alerts.get("alerts", [])),
        "live_provider_status": live_provider.get("status"),
        "recommendations": _recommendations(audit, rolling_backtest, live_provider),
    }
    rows = _load_runs()
    rows.append(run)
    _save_runs(rows[-200:])
    return run


def _recommendations(audit: dict[str, Any], rolling_backtest: dict[str, Any], live_provider: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if audit["weak_team_count"] > 0:
        recommendations.append("Complete or improve metrics for weak teams before trusting strong betting signals.")
    if rolling_backtest.get("passed_brier_gate") is not True:
        recommendations.append("Rolling xG backtest does not pass Brier gate; keep trust conservative.")
    if live_provider.get("status") == "MISSING_API_FOOTBALL_KEY":
        recommendations.append("Set API_FOOTBALL_KEY to collect live fixtures, lineups, events and statistics automatically.")
    if audit["odds_rows_active"] == 0:
        recommendations.append("Import real odds or configure THE_ODDS_API_KEY/API_FOOTBALL_KEY for value validation.")
    return recommendations or ["No critical training blockers detected."]


def list_training_runs() -> list[dict[str, Any]]:
    return _load_runs()
