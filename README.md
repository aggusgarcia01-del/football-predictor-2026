# Football Predictor 2026

Local MVP for FIFA World Cup 2026 match-by-match prediction.

This version is intentionally local and not production validated. It focuses on asking for one match, refreshing prematch data, and getting a justified analysis.

## Recommended Path: Run Locally Without Docker

Docker is optional. The current focus is the prediction and evidence engine, so the app can run with Python, Node, and local files.

### API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open the browser at `http://127.0.0.1:8000/`.

## Run with Docker

```bash
cd infra
docker compose up --build
```

API: `http://localhost:8000`

Web: `http://localhost:3000`

## Current Scope

- FIFA World Cup 2026 groups, teams, host venues, and initial official fixtures.
- `GET /health`
- `GET /matches`
- `GET /predictions/{match_id}`
- `GET /analysis/{match_id}`
- `POST /analysis/query`
- `POST /analysis/query/report`
- `GET /value-bets/today`
- `GET /value-bets/match/{match_id}`
- `POST /backtests/run`
- `GET /simulation/tournament`
- `GET /model/health`
- `POST /data/import/{dataset_type}`
- `GET /prematch/{match_id}/status`
- `POST /prematch/lineups/import`
- Browser web page at `GET /`.

## Ask for a Match Analysis

```bash
curl -X POST http://localhost:8000/analysis/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Analiza Mexico vs Sudafrica\"}"
```

The response includes prediction probabilities, evidence items, reasoning, limitations, and the next real datasets needed.

You can also get a readable Markdown report without using the web dashboard:

```bash
cd apps/api
python scripts/analyze_match.py "Analiza Mexico vs Sudafrica"
```

Or through the API:

```bash
curl -X POST http://localhost:8000/analysis/query/report ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Analiza Mexico vs Sudafrica\"}"
```

## Prediction Engine Commands

From `apps/api`:

```bash
python scripts/analyze_match.py "Analiza Mexico vs Sudafrica"
python scripts/analyze_match.py "Analiza Argentina vs Francia"
python scripts/import_lineups.py ..\..\data\samples\confirmed_lineups_m001.json
python scripts/import_team_metrics.py ..\..\data\samples\team_metrics_real_schema.json
python scripts/sync_statsbomb.py 120
python scripts/sync_statsbomb_full.py
python scripts/fetch_odds.py
python scripts/fetch_lineups.py --match fwc26-001
python scripts/train_once.py
python scripts/value_bets.py
python scripts/run_backtest.py
python scripts/simulate_tournament.py 5000
```

Optional provider keys:

- `THE_ODDS_API_KEY`: prematch bookmaker odds through The Odds API.
- `API_FOOTBALL_KEY` or `APISPORTS_KEY`: live scores, fixture statistics, events and lineups through API-Football/API-Sports.
- `FOOTBALL_DATA_API_KEY`: fixtures/results/form for generic match research through football-data.org.

If the requested teams exist but the fixture is not in `matches.json`, the engine creates a neutral custom matchup and still returns a full evidence report. Odds/EV are only shown when odds exist for that exact match id.

## Match-by-Match Prematch Workflow

The main workflow is not full-tournament simulation. Use it one match at a time:

1. Ask for the match any time: `python scripts/analyze_match.py "Analiza Mexico vs Sudafrica"`.
2. 30-40 minutes before kickoff, paste/import the real confirmed lineups.
3. Ask again. The report will show `READY_CONFIRMED_LINEUPS` when both teams have confirmed XI data.

Lineup import example:

```bash
cd apps/api
python scripts/import_lineups.py ..\..\data\samples\confirmed_lineups_m001.json
python scripts/analyze_match.py "Analiza Mexico vs Sudafrica"
```

The API version:

```bash
curl -X POST http://localhost:8000/prematch/lineups/import ^
  -H "Content-Type: application/json" ^
  --data-binary "@data/samples/confirmed_lineups_m001.json"
```

## Local Data Import

Docker/Postgres are intentionally optional for now. To park a dataset locally:

```bash
curl -X POST http://localhost:8000/data/import/odds ^
  -H "Content-Type: application/json" ^
  -d "{\"records\":[{\"match_id\":\"fwc26-001\",\"bookmaker\":\"Manual\",\"market\":\"1X2\",\"selection\":\"Home\",\"decimal_odds\":1.8}]}"
```

Imported files are written to `data/imports/`. For `odds`, `team_metrics`, and `availability`, imported records override seed records with the same keys and become active immediately. For other datasets they are parked locally for review.

## Production Validation Status

The API includes a backtesting gate and model-health endpoint, but the current seed dataset is intentionally tiny. Any `PASSED`/`BLOCKED` result from seed data is only a pipeline check. Real production validation still requires historical tournament results, xG, lineups, injuries, referee data, and odds snapshots.

## Real Statistical Data

The model now tracks source quality and sample size for team metrics. Weak/missing data is shrunk toward global international baselines instead of being trusted blindly.

See `docs/data-sources.md`.

## Fixture Sources

- FIFA official schedule page: full tournament runs from 11 June to 19 July 2026, with 104 matches.
- FIFA confirmed the opening match: Mexico v South Africa in Mexico City.
- FIFA group/fixture pages confirm Group A and Mexico fixtures.

The active local fixture currently includes all 48 teams/groups and the first official group-stage matchdays plus Group A. It is designed to be updated as the full FIFA page/export is imported.

## Responsible Use

This is a statistical demo. It is not validated for real betting or financial decisions. Past performance does not guarantee future results. Bet only what you can afford to lose.
