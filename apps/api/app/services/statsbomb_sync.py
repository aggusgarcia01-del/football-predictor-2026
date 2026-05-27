import json
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models.schemas import StatsBombCompetitionSelection, StatsBombSyncRequest, StatsBombSyncResult
from app.services import data


RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
ROOT = Path(__file__).resolve().parents[4]
CACHE_DIR = ROOT / "data" / "statsbomb_cache"
IMPORTS_DIR = ROOT / "data" / "imports"
DEFAULT_COMPETITIONS = [
    StatsBombCompetitionSelection(competition_id=43, season_id=106, label="FIFA World Cup 2022"),
    StatsBombCompetitionSelection(competition_id=55, season_id=282, label="UEFA Euro 2024"),
    StatsBombCompetitionSelection(competition_id=223, season_id=282, label="Copa America 2024"),
]


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _team_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for team_id, team in data.teams().items():
        lookup[_normalize(team.name)] = team_id
        for alias in data.team_aliases().get(team_id, []):
            lookup[_normalize(alias)] = team_id
    return lookup


def _fetch_json(relative_path: str) -> Any:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / relative_path.replace("/", "__")
    if cache_file.exists():
        with cache_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    url = f"{RAW_BASE}/{relative_path}"
    with urllib.request.urlopen(url, timeout=40) as response:
        payload = json.load(response)

    with cache_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return payload


def _shot_on_target(event: dict[str, Any]) -> bool:
    outcome = event.get("shot", {}).get("outcome", {}).get("name", "")
    return outcome in {"Goal", "Saved", "Saved to Post"}


def _selection_label(selection: StatsBombCompetitionSelection) -> str:
    return f"{selection.label} ({selection.competition_id}/{selection.season_id})"


def _team_elo(team_id: str | None) -> int:
    if not team_id:
        return 1600
    team = data.teams().get(team_id)
    return team.elo if team else 1600


def _opponent_adjustment(opponent_id: str | None) -> float:
    elo_gap = _team_elo(opponent_id) - 1600
    return 1 + max(min(elo_gap / 2200, 0.22), -0.22)


def _recency_weight(already_counted: int, decay: float) -> float:
    return 1 / (1 + max(decay, 0.0) * already_counted)


def _new_stats_row() -> dict[str, Any]:
    return {
        "matches": set(),
        "match_dates": [],
        "weighted_matches": 0.0,
        "xg_for": 0.0,
        "xg_against": 0.0,
        "opponent_adjusted_xg_for": 0.0,
        "opponent_adjusted_xg_against": 0.0,
        "shots_on_target": 0.0,
        "corners": 0.0,
        "cards": 0.0,
        "goals_for": 0.0,
        "goals_against": 0.0,
        "clean_sheets": 0.0,
        "failed_to_score": 0.0,
        "points": 0.0,
        "opponent_elo_weighted": 0.0,
        "sources": set(),
    }


def sync_statsbomb_metrics(request: StatsBombSyncRequest) -> StatsBombSyncResult:
    competitions = request.competitions or DEFAULT_COMPETITIONS
    max_matches_total = max(1, min(request.max_matches_total, 300))
    max_matches_per_team = max(1, min(request.max_matches_per_team, 30))
    recency_decay = max(0.0, min(request.recency_decay, 0.6))
    lookup = _team_lookup()
    stats = defaultdict(_new_stats_row)
    selected_matches: list[dict[str, Any]] = []
    matches_scanned = 0
    notes: list[str] = []

    for selection in competitions:
        try:
            matches = _fetch_json(f"matches/{selection.competition_id}/{selection.season_id}.json")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Could not fetch {_selection_label(selection)}: {exc}")
            continue

        matches_scanned += len(matches)
        for match in matches:
            home_name = _normalize(match.get("home_team", {}).get("home_team_name", ""))
            away_name = _normalize(match.get("away_team", {}).get("away_team_name", ""))
            home_id = lookup.get(home_name)
            away_id = lookup.get(away_name)
            if not home_id and not away_id:
                continue
            selected_matches.append(
                {
                    "match_id": str(match.get("match_id")),
                    "match_date": match.get("match_date", ""),
                    "home_id": home_id,
                    "away_id": away_id,
                    "home_score": int(match.get("home_score", 0)),
                    "away_score": int(match.get("away_score", 0)),
                    "label": _selection_label(selection),
                }
            )

    selected_matches.sort(key=lambda row: row["match_date"], reverse=True)
    selected_matches = selected_matches[:max_matches_total]

    team_match_counts: dict[str, int] = defaultdict(int)
    matches_used = 0
    for match in selected_matches:
        home_id = match["home_id"]
        away_id = match["away_id"]
        weight_by_team: dict[str, float] = {}
        if home_id and team_match_counts[home_id] < max_matches_per_team:
            weight_by_team[home_id] = _recency_weight(team_match_counts[home_id], recency_decay)
        if away_id and team_match_counts[away_id] < max_matches_per_team:
            weight_by_team[away_id] = _recency_weight(team_match_counts[away_id], recency_decay)
        if not weight_by_team:
            continue

        try:
            events = _fetch_json(f"events/{match['match_id']}.json")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Could not fetch events for match {match['match_id']}: {exc}")
            continue

        matches_used += 1
        if home_id in weight_by_team:
            weight = weight_by_team[home_id]
            row = stats[home_id]
            row["matches"].add(match["match_id"])
            row["match_dates"].append(match["match_date"])
            row["weighted_matches"] += weight
            row["goals_for"] += match["home_score"] * weight
            row["goals_against"] += match["away_score"] * weight
            row["clean_sheets"] += (1 if match["away_score"] == 0 else 0) * weight
            row["failed_to_score"] += (1 if match["home_score"] == 0 else 0) * weight
            row["points"] += (3 if match["home_score"] > match["away_score"] else 1 if match["home_score"] == match["away_score"] else 0) * weight
            row["opponent_elo_weighted"] += _team_elo(away_id) * weight
            row["sources"].add(match["label"])
            team_match_counts[home_id] += 1
        if away_id in weight_by_team:
            weight = weight_by_team[away_id]
            row = stats[away_id]
            row["matches"].add(match["match_id"])
            row["match_dates"].append(match["match_date"])
            row["weighted_matches"] += weight
            row["goals_for"] += match["away_score"] * weight
            row["goals_against"] += match["home_score"] * weight
            row["clean_sheets"] += (1 if match["home_score"] == 0 else 0) * weight
            row["failed_to_score"] += (1 if match["away_score"] == 0 else 0) * weight
            row["points"] += (3 if match["away_score"] > match["home_score"] else 1 if match["away_score"] == match["home_score"] else 0) * weight
            row["opponent_elo_weighted"] += _team_elo(home_id) * weight
            row["sources"].add(match["label"])
            team_match_counts[away_id] += 1

        for event in events:
            team_name = _normalize(event.get("team", {}).get("name", ""))
            team_id = lookup.get(team_name)
            if not team_id or team_id not in weight_by_team:
                continue

            opponent_id = away_id if team_id == home_id else home_id if team_id == away_id else None
            weight = weight_by_team[team_id]
            event_type = event.get("type", {}).get("name", "")
            if event_type == "Shot":
                shot = event.get("shot", {})
                if shot.get("type", {}).get("name") == "Penalty":
                    continue
                xg = float(shot.get("statsbomb_xg", 0.0) or 0.0)
                stats[team_id]["xg_for"] += xg * weight
                stats[team_id]["opponent_adjusted_xg_for"] += xg * weight * _opponent_adjustment(opponent_id)
                if opponent_id and opponent_id in weight_by_team:
                    opponent_weight = weight_by_team[opponent_id]
                    defensive_adjustment = 1 / _opponent_adjustment(team_id)
                    stats[opponent_id]["xg_against"] += xg * opponent_weight
                    stats[opponent_id]["opponent_adjusted_xg_against"] += xg * opponent_weight * defensive_adjustment
                if _shot_on_target(event):
                    stats[team_id]["shots_on_target"] += weight
            elif event_type == "Pass" and event.get("pass", {}).get("type", {}).get("name") == "Corner":
                stats[team_id]["corners"] += weight
            elif event_type in {"Foul Committed", "Bad Behaviour"}:
                if event.get("foul_committed", {}).get("card") or event.get("bad_behaviour", {}).get("card"):
                    stats[team_id]["cards"] += weight

    records: list[dict[str, Any]] = []
    for team_id, row in stats.items():
        matches = len(row["matches"])
        weighted_matches = float(row["weighted_matches"])
        if matches <= 0 or weighted_matches <= 0:
            continue
        match_dates = sorted(row["match_dates"])
        records.append(
            {
                "team_id": team_id,
                "source": "statsbomb_open_data",
                "source_name": "StatsBomb Open Data",
                "source_url": "https://github.com/statsbomb/open-data",
                "as_of": datetime.now(UTC).date().isoformat(),
                "sample": ", ".join(sorted(row["sources"])),
                "sample_size_matches": matches,
                "weighted_sample_matches": round(weighted_matches, 3),
                "sample_start": match_dates[0] if match_dates else None,
                "sample_end": match_dates[-1] if match_dates else None,
                "recency_policy": f"latest {max_matches_per_team} per team, decay {recency_decay}",
                "is_real_data": True,
                "data_quality": "statsbomb_open_data",
                "npxg_for_per90": round(row["xg_for"] / weighted_matches, 3),
                "npxg_against_per90": round(row["xg_against"] / weighted_matches, 3),
                "opponent_adjusted_npxg_for_per90": round(row["opponent_adjusted_xg_for"] / weighted_matches, 3),
                "opponent_adjusted_npxg_against_per90": round(row["opponent_adjusted_xg_against"] / weighted_matches, 3),
                "shots_on_target_for_per90": round(row["shots_on_target"] / weighted_matches, 3),
                "corners_for_per90": round(row["corners"] / weighted_matches, 3),
                "cards_per90": round(row["cards"] / weighted_matches, 3),
                "recent_form_points_per_match": round(row["points"] / weighted_matches, 3),
                "goals_for_per90": round(row["goals_for"] / weighted_matches, 3),
                "goals_against_per90": round(row["goals_against"] / weighted_matches, 3),
                "clean_sheet_rate": round(row["clean_sheets"] / weighted_matches, 3),
                "failed_to_score_rate": round(row["failed_to_score"] / weighted_matches, 3),
                "average_opponent_elo": round(row["opponent_elo_weighted"] / weighted_matches, 1),
            }
        )

    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = IMPORTS_DIR / "team_metrics.json"
    with output.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
    data.clear_caches()

    return StatsBombSyncResult(
        competitions_scanned=len(competitions),
        matches_scanned=matches_scanned,
        matches_used=matches_used,
        records_written=len(records),
        output_file=str(output),
        source_url="https://github.com/statsbomb/open-data",
        status="STATSBOMB_METRICS_IMPORTED_ACTIVE",
        notes=notes or [
            "StatsBomb metrics imported and active for matching World Cup 2026 teams.",
            f"Recency policy: latest {max_matches_per_team} matches per team with decay {recency_decay}.",
            "Opponent-adjusted xG fields are now available for the prediction model.",
        ],
    )
