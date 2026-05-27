from app.services import data
from app.services.statistical_inputs import CORE_METRICS, metric_source, reliability


def active_data_audit() -> dict:
    teams = data.teams()
    metrics = data.team_metrics()
    odds = data.odds()
    lineups = data.lineups()
    by_quality: dict[str, int] = {}
    weak_teams: list[dict] = []
    missing_metrics: list[dict] = []

    for team_id, team in teams.items():
        row = metrics.get(team_id)
        source = metric_source(row or {})
        by_quality[source] = by_quality.get(source, 0) + 1
        rel = reliability(row)
        missing = [key for key in CORE_METRICS if not row or key not in row]
        if rel < 0.55:
            weak_teams.append({"team_id": team_id, "team_name": team.name, "reliability": rel, "source": source})
        if missing:
            missing_metrics.append({"team_id": team_id, "team_name": team.name, "missing": missing})

    test_like_odds = [row for row in odds if str(row.get("match_id", "")).startswith("test") or row.get("match_id") == "x"]
    test_like_lineups = [
        row
        for row in lineups
        if str(row.get("match_id", "")).startswith("test") or str(row.get("source", "")).lower() == "test"
    ]

    return {
        "teams_total": len(teams),
        "team_metrics_records": len(metrics),
        "metrics_by_quality": dict(sorted(by_quality.items())),
        "weak_team_count": len(weak_teams),
        "weak_teams": sorted(weak_teams, key=lambda row: (row["reliability"], row["team_name"])),
        "missing_core_metrics_count": len(missing_metrics),
        "missing_core_metrics": missing_metrics,
        "odds_rows_active": len(odds),
        "lineups_rows_active": len(lineups),
        "test_like_odds_rows": test_like_odds,
        "test_like_lineup_rows": test_like_lineups,
        "warnings": [
            "Teams below 0.55 reliability should block strong betting opinions.",
            "Test-like rows should be removed from active imports before real analysis.",
            "Seed odds are useful for UI testing only; import real prematch odds before evaluating value.",
        ],
    }
