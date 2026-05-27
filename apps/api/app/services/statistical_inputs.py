from app.models.schemas import ModelDataCoverage, TeamDataCoverage
from app.services import data


CORE_METRICS = [
    "npxg_for_per90",
    "npxg_against_per90",
    "shots_on_target_for_per90",
    "recent_form_points_per_match",
]

BASELINES = {
    "npxg_for_per90": 1.25,
    "npxg_against_per90": 1.15,
    "opponent_adjusted_npxg_for_per90": 1.25,
    "opponent_adjusted_npxg_against_per90": 1.15,
    "shots_on_target_for_per90": 4.0,
    "corners_for_per90": 4.7,
    "cards_per90": 1.9,
    "recent_form_points_per_match": 1.5,
    "clean_sheet_rate": 0.28,
    "failed_to_score_rate": 0.22,
}

QUALITY_WEIGHTS = {
    "opta": 1.0,
    "statsperform": 1.0,
    "statsbomb_open_data": 0.88,
    "sofascore_manual": 0.74,
    "fbref_manual": 0.72,
    "manual_verified": 0.68,
    "manual": 0.55,
    "demo": 0.18,
    "fallback": 0.05,
}


def metric_source(metrics: dict) -> str:
    return str(metrics.get("data_quality") or metrics.get("source") or "fallback").lower()


def reliability(metrics: dict | None) -> float:
    if not metrics:
        return 0.05

    source = metric_source(metrics)
    quality_weight = QUALITY_WEIGHTS.get(source, 0.35)
    sample_size = int(metrics.get("sample_size_matches", 0) or 0)
    sample_weight = min(sample_size / 12, 1.0)
    real_bonus = 0.1 if metrics.get("is_real_data") else 0.0
    return round(min(1.0, max(0.05, quality_weight * (0.35 + 0.65 * sample_weight) + real_bonus)), 4)


def adjusted_metric(team_id: str, key: str) -> tuple[float, float, str]:
    metrics = data.team_metrics().get(team_id)
    baseline = BASELINES[key]
    if not metrics or key not in metrics:
        return baseline, 0.05, "fallback_global_baseline"

    raw = float(metrics[key])
    rel = reliability(metrics)
    adjusted = (raw * rel) + (baseline * (1 - rel))
    return adjusted, rel, str(metrics.get("source_name") or metrics.get("source") or "unknown")


def preferred_adjusted_metric(team_id: str, key: str) -> tuple[float, float, str, str]:
    """Use richer opponent-adjusted fields when the import has them."""
    metrics = data.team_metrics().get(team_id) or {}
    preferred_key = {
        "npxg_for_per90": "opponent_adjusted_npxg_for_per90",
        "npxg_against_per90": "opponent_adjusted_npxg_against_per90",
    }.get(key, key)
    if preferred_key in metrics:
        value, rel, source = adjusted_metric(team_id, preferred_key)
        return value, rel, source, preferred_key
    value, rel, source = adjusted_metric(team_id, key)
    return value, rel, source, key


def uncertainty(team_id: str) -> float:
    metrics = data.team_metrics().get(team_id)
    rel = reliability(metrics)
    return round(1 - rel, 4)


def coverage() -> ModelDataCoverage:
    teams = data.teams()
    rows: list[TeamDataCoverage] = []
    real_count = 0
    demo_count = 0
    reliability_total = 0.0

    for team_id, team in teams.items():
        metrics = data.team_metrics().get(team_id)
        rel = reliability(metrics)
        reliability_total += rel
        quality = metric_source(metrics or {})
        if metrics and quality not in {"demo", "fallback"}:
            real_count += 1
        else:
            demo_count += 1

        rows.append(
            TeamDataCoverage(
                team_id=team_id,
                team_name=team.name,
                has_team_metrics=metrics is not None,
                source=str((metrics or {}).get("source_name") or (metrics or {}).get("source") or "fallback"),
                source_url=(metrics or {}).get("source_url"),
                data_quality=quality,
                sample_size_matches=int((metrics or {}).get("sample_size_matches", 0) or 0),
                reliability=rel,
                missing_core_metrics=[key for key in CORE_METRICS if not metrics or key not in metrics],
            )
        )

    return ModelDataCoverage(
        teams_total=len(teams),
        teams_with_real_or_manual_metrics=real_count,
        teams_with_demo_or_fallback_metrics=demo_count,
        average_reliability=round(reliability_total / max(len(teams), 1), 4),
        teams=sorted(rows, key=lambda row: (row.reliability, row.team_name)),
    )
