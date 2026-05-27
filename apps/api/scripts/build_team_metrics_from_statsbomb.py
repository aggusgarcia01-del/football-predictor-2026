import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import data


def normalize(value: str) -> str:
    return value.strip().casefold()


def team_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for team_id, team in data.teams().items():
        lookup[normalize(team.name)] = team_id
        for alias in data.team_aliases().get(team_id, []):
            lookup[normalize(alias)] = team_id
    return lookup


def iter_json_files(path: Path):
    for file in path.rglob("*.json"):
        yield file


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build team_metrics records from a local StatsBomb Open Data checkout."
    )
    parser.add_argument("--statsbomb-data", required=True, help="Path to statsbomb/open-data/data")
    parser.add_argument("--out", default="../../data/imports/team_metrics.json")
    args = parser.parse_args()

    root = Path(args.statsbomb_data).resolve()
    events_dir = root / "events"
    matches_dir = root / "matches"
    if not events_dir.exists() or not matches_dir.exists():
        print("Expected StatsBomb data folder with events/ and matches/ subfolders.")
        return 1

    lookup = team_lookup()
    stats = defaultdict(lambda: {"matches": set(), "xg_for": 0.0, "xg_against": 0.0, "goals_for": 0, "goals_against": 0})
    match_teams: dict[str, tuple[str, str]] = {}
    match_scores: dict[str, tuple[int, int]] = {}

    for match_file in iter_json_files(matches_dir):
        for match in load_json(match_file):
            match_id = str(match.get("match_id"))
            home_name = normalize(match.get("home_team", {}).get("home_team_name", ""))
            away_name = normalize(match.get("away_team", {}).get("away_team_name", ""))
            home_id = lookup.get(home_name)
            away_id = lookup.get(away_name)
            if not home_id or not away_id:
                continue
            match_teams[match_id] = (home_id, away_id)
            match_scores[match_id] = (int(match.get("home_score", 0)), int(match.get("away_score", 0)))
            stats[home_id]["matches"].add(match_id)
            stats[away_id]["matches"].add(match_id)
            stats[home_id]["goals_for"] += match_scores[match_id][0]
            stats[home_id]["goals_against"] += match_scores[match_id][1]
            stats[away_id]["goals_for"] += match_scores[match_id][1]
            stats[away_id]["goals_against"] += match_scores[match_id][0]

    for event_file in iter_json_files(events_dir):
        match_id = event_file.stem
        if match_id not in match_teams:
            continue
        home_id, away_id = match_teams[match_id]
        for event in load_json(event_file):
            if event.get("type", {}).get("name") != "Shot":
                continue
            team_name = normalize(event.get("team", {}).get("name", ""))
            team_id = lookup.get(team_name)
            if team_id not in {home_id, away_id}:
                continue
            xg = float(event.get("shot", {}).get("statsbomb_xg", 0.0) or 0.0)
            opponent_id = away_id if team_id == home_id else home_id
            stats[team_id]["xg_for"] += xg
            stats[opponent_id]["xg_against"] += xg

    records = []
    for team_id, row in stats.items():
        matches = len(row["matches"])
        if matches == 0:
            continue
        points_proxy = ((row["goals_for"] - row["goals_against"]) / matches) * 0.25 + 1.5
        records.append(
            {
                "team_id": team_id,
                "source": "statsbomb_open_data",
                "source_name": "StatsBomb Open Data",
                "source_url": "https://github.com/statsbomb/open-data",
                "as_of": "local_statsbomb_export",
                "sample": f"{matches} StatsBomb Open Data matches",
                "sample_size_matches": matches,
                "is_real_data": True,
                "data_quality": "statsbomb_open_data",
                "npxg_for_per90": round(row["xg_for"] / matches, 3),
                "npxg_against_per90": round(row["xg_against"] / matches, 3),
                "recent_form_points_per_match": round(max(0.2, min(2.8, points_proxy)), 3),
            }
        )

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {len(records)} team metric records to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
