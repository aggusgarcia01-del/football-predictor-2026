from app.models.schemas import ModelHealth
from app.services.backtesting import run_backtest


def current_model_health() -> ModelHealth:
    backtest = run_backtest()
    statsbomb_backtest = run_backtest("statsbomb_open_data")
    validation = statsbomb_backtest if statsbomb_backtest.matches_evaluated >= backtest.matches_evaluated else backtest
    alerts: list[str] = []

    if validation.matches_evaluated < 30:
        alerts.append("Insufficient validation sample: need real historical tournament dataset.")
    if not validation.passed_brier_gate:
        alerts.append("Brier score gate not passed.")
    if not validation.passed_log_loss_gate:
        alerts.append("Log loss gate not passed.")
    if not backtest.passed_roi_gate:
        alerts.append("ROI gate not passed or too few flagged bets with historical odds.")
    if statsbomb_backtest.production_gate_status == "RESEARCH_ONLY_NO_HISTORICAL_ODDS":
        alerts.append("StatsBomb calibration exists, but historical bookmaker odds are still missing.")

    status = "GREEN" if not alerts else "RED"
    return ModelHealth(
        status=status,
        brier_score=validation.brier_score,
        log_loss=validation.log_loss,
        roi=backtest.roi,
        matches_evaluated=validation.matches_evaluated,
        alerts=alerts,
        production_gate_status=statsbomb_backtest.production_gate_status if statsbomb_backtest.matches_evaluated else backtest.production_gate_status,
    )
