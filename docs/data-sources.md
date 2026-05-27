# Data Sources For The Predictor

## Preferred Source Tiers

1. Opta / Stats Perform: best professional feed, but paid/licensed.
2. StatsBomb Open Data: open event data, good for real historical xG/event aggregation where teams/matches exist in the open dataset.
3. SofaScore manual export: useful if you manually collect stats, but this project should not scrape undocumented endpoints.
4. FBref/manual CSV: useful for team-level public summaries when licensing allows.
5. Seed/demo fallback: only for pipeline testing.

## Active Team Metrics Schema

Import records through `POST /data/import/team_metrics` or:

```bash
python scripts/import_team_metrics.py ..\..\data\samples\team_metrics_real_schema.json
```

Minimum useful fields:

- `team_id`
- `source`, `source_name`, `source_url`
- `as_of`
- `sample_size_matches`
- `is_real_data`
- `data_quality`
- `npxg_for_per90`
- `npxg_against_per90`
- `shots_on_target_for_per90`
- `recent_form_points_per_match`

Richer optional fields now used by the model when present:

- `opponent_adjusted_npxg_for_per90`
- `opponent_adjusted_npxg_against_per90`
- `clean_sheet_rate`
- `failed_to_score_rate`
- `average_opponent_elo`
- `sample_start`
- `sample_end`
- `recency_policy`

## StatsBomb Open Data

StatsBomb Open Data is available at `https://github.com/statsbomb/open-data`.

Fast path from the web app: press **Sincronizar StatsBomb Open Data**.

CLI fast path:

```bash
python scripts/sync_statsbomb.py 180
```

After downloading/cloning it, run:

```bash
python scripts/build_team_metrics_from_statsbomb.py --statsbomb-data C:\path\to\open-data\data
python scripts/analyze_match.py "Analiza Mexico vs Sudafrica"
```

The generated `data/imports/team_metrics.json` becomes active immediately. The current importer keeps the latest matches per team, applies recency weighting, and writes opponent-adjusted xG so a strong performance against a strong opponent is valued more than the same raw xG against a weak opponent.

## SofaScore / Opta

Use these as manual or licensed imports:

- Opta/Stats Perform: import licensed feed exports.
- SofaScore: manually export or enter values you are allowed to use. Avoid scraping undocumented/private endpoints.
