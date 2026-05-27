import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.schemas import Match, MatchView, Team, Venue


def _default_seed_dir() -> Path:
    configured = os.getenv("FOOTBALL_PREDICTOR_DATA_DIR")
    if configured:
        return Path(configured)

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "seed"
        if candidate.exists():
            return candidate

    return Path("/data/seed")


SEED_DIR = _default_seed_dir()
IMPORT_DIR = SEED_DIR.parent / "imports"


def _load_json(name: str) -> list[dict[str, Any]]:
    with (SEED_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_imported_json(name: str) -> list[dict[str, Any]]:
    imported_file = IMPORT_DIR / name
    if not imported_file.exists():
        return []
    with imported_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _merge_records(seed: list[dict[str, Any]], imported: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    imported_keys = {tuple(row.get(key) for key in keys) for row in imported}
    merged = [
        row
        for row in seed
        if tuple(row.get(key) for key in keys) not in imported_keys
    ]
    merged.extend(imported)
    return merged


def clear_caches() -> None:
    for func in (
        teams,
        team_aliases,
        venues,
        matches,
        historical_results,
        tournament_groups,
    ):
        func.cache_clear()


@lru_cache
def teams() -> dict[str, Team]:
    return {row["id"]: Team(**row) for row in _load_json("teams.json")}


@lru_cache
def team_aliases() -> dict[str, list[str]]:
    with (SEED_DIR / "team_aliases.json").open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return {team_id: list(aliases) for team_id, aliases in raw.items()}


@lru_cache
def venues() -> dict[str, Venue]:
    return {row["id"]: Venue(**row) for row in _load_json("venues.json")}


@lru_cache
def matches() -> dict[str, Match]:
    return {row["id"]: Match(**row) for row in _load_json("matches.json")}


def odds() -> list[dict[str, Any]]:
    return _merge_records(
        _load_json("odds.json"),
        _load_imported_json("odds.json"),
        ("match_id", "bookmaker", "market", "selection"),
    )


def team_metrics() -> dict[str, dict[str, Any]]:
    records = _merge_records(
        _load_json("team_metrics.json"),
        _load_imported_json("team_metrics.json"),
        ("team_id",),
    )
    return {row["team_id"]: row for row in records}


def availability() -> dict[str, dict[str, Any]]:
    records = _merge_records(
        _load_json("availability.json"),
        _load_imported_json("availability.json"),
        ("team_id",),
    )
    return {row["team_id"]: row for row in records}


@lru_cache
def historical_results() -> list[dict[str, Any]]:
    return _load_json("historical_results.json")


@lru_cache
def tournament_groups() -> list[dict[str, Any]]:
    return _load_json("tournament_groups.json")


def lineups() -> list[dict[str, Any]]:
    seed_lineups = _load_json("lineups.json")
    imported_file = IMPORT_DIR / "lineups_active.json"
    if not imported_file.exists():
        return seed_lineups

    with imported_file.open("r", encoding="utf-8") as handle:
        imported = json.load(handle)

    imported_keys = {(row.get("match_id"), row.get("team_id")) for row in imported}
    merged = [
        row
        for row in seed_lineups
        if (row.get("match_id"), row.get("team_id")) not in imported_keys
    ]
    merged.extend(imported)
    return merged


def lineup_for(match_id: str, team_id: str) -> dict[str, Any] | None:
    candidates = [
        row
        for row in lineups()
        if row.get("match_id") == match_id and row.get("team_id") == team_id
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: str(row.get("updated_at", "")), reverse=True)[0]


def match_view(match: Match) -> MatchView:
    return MatchView(
        id=match.id,
        date=match.date,
        stage=match.stage,
        home_team=teams()[match.home_team_id],
        away_team=teams()[match.away_team_id],
        venue=venues()[match.venue_id],
    )


def list_match_views() -> list[MatchView]:
    return [match_view(match) for match in matches().values()]
