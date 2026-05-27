# How To Train And Improve The Predictor

The model improves by saving predictions before the result is known, then comparing those probabilities with final outcomes.

## Data To Capture

For every match:

- fixture id, league, season, kickoff time
- home and away teams
- prematch odds by bookmaker
- model probabilities before kickoff
- lineups and absences
- live score/minute snapshots
- live shots, shots on target, corners, red cards and odds when available
- final score and settled markets

## Minimum Samples

- 300 completed matches: basic 1X2 calibration.
- 1000 completed matches: stronger market calibration.
- Historical odds snapshots: required for ROI/value validation.

## Workflow

1. Before kickoff, run the model and save the prediction.
2. Import odds and lineups.
3. During the match, save live snapshots every 10-15 minutes.
4. After full time, settle the snapshot with final score.
5. Run backtests and calibration reports.
6. Lower trust where the model is overconfident.

## Providers

Supported/started:

- StatsBomb Open Data: historical event/xG data where open competitions exist.
- football-data.org: fixtures/results/form via `FOOTBALL_DATA_API_KEY`.
- The Odds API: prematch odds via `THE_ODDS_API_KEY`.
- API-Football/API-Sports: live scores, events, statistics, lineups, predictions and odds via `API_FOOTBALL_KEY`.

The app should never pretend it has data it does not have. If a provider key is missing or coverage is weak, the model must lower confidence.
