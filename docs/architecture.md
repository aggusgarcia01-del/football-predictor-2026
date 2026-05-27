# Architecture

## Components

- `apps/api`: FastAPI service for prediction, value detection, simulation, ingestion, and model health.
- `apps/web`: Next.js dashboard for match predictions, value opportunities, tournament simulation, player/referee panels, and model health.
- `data/seed`: local demo data used until real provider integrations are added.
- `data/imports`: local imported datasets waiting for review/promotion.
- `infra`: Docker Compose for Postgres, Redis, API, and web.

## Data Flow

1. Seed or imported data is loaded by the API data service.
2. Prediction service computes a baseline ELO/Poisson-inspired demo probability.
3. Value service compares model probability against best market odds.
4. Backtest service evaluates Brier score, log loss, ROI, and production gate status.
5. Simulation service runs a local Monte Carlo tournament approximation over available seed teams.
6. Web dashboard or CLI scripts consume API endpoints and label all outputs as demo/not production validated.

## No-Docker Development Mode

Current development prioritizes the prediction engine. The system runs from Python, JSON seed data, and CLI/API endpoints. Docker/Postgres/Redis can be added later without changing the model contracts.

## Production Gate

The system must stay in demo mode until real historical data and odds pass the defined backtesting thresholds: Brier score, log loss, ROI, and calibration checks.
