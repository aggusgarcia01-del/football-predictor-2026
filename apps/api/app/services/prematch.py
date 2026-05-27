import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models.schemas import LineupImportRequest, LineupImportResult, PrematchStatus
from app.services import data


ROOT = Path(__file__).resolve().parents[4]
ACTIVE_LINEUPS = ROOT / "data" / "imports" / "lineups_active.json"
CONFIRMED_STATUSES = {"confirmed", "official"}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _freshness(updated_at: str | None, now: datetime | None = None) -> str:
    parsed = _parse_datetime(updated_at)
    if parsed is None:
        return "missing"
    now = now or datetime.now(UTC)
    age_minutes = (now - parsed).total_seconds() / 60
    if age_minutes < 0:
        return "scheduled_pre_match"
    if age_minutes <= 60:
        return "fresh"
    if age_minutes <= 240:
        return "usable_but_aging"
    return "stale"


def _lineup_status(match_id: str, team_id: str) -> tuple[str, str | None, str]:
    lineup = data.lineup_for(match_id, team_id)
    if lineup is None:
        return "missing", None, "missing"
    updated_at = str(lineup.get("updated_at", ""))
    return str(lineup.get("status", "unknown")), updated_at, _freshness(updated_at)


def prematch_status(match_id: str, home_team_id: str, away_team_id: str) -> PrematchStatus:
    home_status, home_updated, home_freshness = _lineup_status(match_id, home_team_id)
    away_status, away_updated, away_freshness = _lineup_status(match_id, away_team_id)

    notes: list[str] = []
    if home_status not in CONFIRMED_STATUSES or away_status not in CONFIRMED_STATUSES:
        notes.append("Lineups are not fully confirmed yet; rerun analysis 30-40 minutes before kickoff.")
    if "stale" in {home_freshness, away_freshness} or "missing" in {home_freshness, away_freshness}:
        notes.append("One or both lineup feeds are stale/missing; confidence is reduced.")

    if home_status in CONFIRMED_STATUSES and away_status in CONFIRMED_STATUSES and not notes:
        readiness = "READY_CONFIRMED_LINEUPS"
    elif home_status == "missing" or away_status == "missing":
        readiness = "NOT_READY_MISSING_LINEUPS"
    else:
        readiness = "PROVISIONAL_PROBABLE_LINEUPS"

    return PrematchStatus(
        home_lineup_status=home_status,
        away_lineup_status=away_status,
        home_lineup_updated_at=home_updated,
        away_lineup_updated_at=away_updated,
        home_lineup_freshness=home_freshness,
        away_lineup_freshness=away_freshness,
        overall_readiness=readiness,
        notes=notes,
    )


def lineup_multiplier(match_id: str, team_id: str) -> tuple[float, str]:
    lineup = data.lineup_for(match_id, team_id)
    if lineup is None:
        return 1.0, "no lineup data"

    players = [player for player in lineup.get("players", []) if player.get("status") == "starter"]
    if not players:
        return 1.0, "lineup has no starters"

    avg_rating = sum(float(player.get("rating", 78.0)) for player in players) / len(players)
    avg_fitness = sum(float(player.get("fitness", 1.0)) for player in players) / len(players)
    minutes_factor = sum(float(player.get("expected_minutes", 90)) for player in players) / (len(players) * 90)
    status = str(lineup.get("status", "unknown"))
    confirmation_bonus = 0.01 if status in CONFIRMED_STATUSES else 0.0

    quality_component = max(min((avg_rating - 78.0) / 250.0, 0.08), -0.08)
    fitness_component = max(min((avg_fitness - 0.94) * 0.55, 0.04), -0.08)
    minutes_component = max(min((minutes_factor - 0.93) * 0.30, 0.03), -0.05)
    multiplier = max(0.82, min(1.14, 1 + quality_component + fitness_component + minutes_component + confirmation_bonus))

    description = (
        f"{status} lineup, avg rating {avg_rating:.1f}, avg fitness {avg_fitness:.2f}, "
        f"minutes factor {minutes_factor:.2f}"
    )
    return multiplier, description


def import_lineups(request: LineupImportRequest) -> LineupImportResult:
    ACTIVE_LINEUPS.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]]
    if ACTIVE_LINEUPS.exists():
        with ACTIVE_LINEUPS.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
    else:
        existing = []
    now_iso = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    incoming = []
    for lineup in request.lineups:
        row = lineup.model_dump()
        if str(row.get("updated_at", "")).upper() == "NOW":
            row["updated_at"] = now_iso
        incoming.append(row)

    merged = [
        row
        for row in existing
        if (row.get("match_id"), row.get("team_id")) not in {
            (lineup["match_id"], lineup["team_id"]) for lineup in incoming
        }
    ]
    merged.extend(incoming)

    with ACTIVE_LINEUPS.open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)

    data.clear_caches()
    return LineupImportResult(
        lineups_received=len(request.lineups),
        lineups_written=len(incoming),
        output_file=str(ACTIVE_LINEUPS),
        status="LINEUPS_IMPORTED_AND_ACTIVE",
    )
