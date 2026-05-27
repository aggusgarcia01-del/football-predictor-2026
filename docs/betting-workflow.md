# Betting workflow

This project does not scrape betting websites. Odds should be entered manually, uploaded from a CSV/JSON you are allowed to use, or pulled from an API with permission.

## Apuesta fija

Endpoint:

```text
GET /value-bets/fixed
GET /value-bets/fixed/{match_id}
```

The app marks a fixed-bet candidate only when:

- the model top 1X2 selection is at least 55%;
- the best imported decimal odd has positive expected value;
- average data reliability for both teams is at least 0.55;
- the report still warns when confirmed lineups are missing.

Statuses:

- `FIXED_BET_CANDIDATE`: probability, price and data quality are aligned.
- `WATCHLIST_DATA_RISK`: price looks good, but data reliability is weak.
- `LIKELY_OUTCOME_BAD_PRICE`: the result is likely, but the odd is too low.
- `WAITING_FOR_REAL_ODDS`: no bookmaker odds have been imported.
- `NO_BET`: no edge.

## Import odds

Use:

```text
POST /data/import/odds
```

Payload example: `data/samples/odds_bookmakers_schema.json`.

Selections for `1X2` are:

- `Home`
- `Draw`
- `Away`

The predictor uses the best imported odd by selection across bookmakers. Keep `captured_at` in the records so later versions can analyze line movement.

## Practical use

1. Sync StatsBomb data.
2. Ask for the match analysis.
3. Import real odds from several bookmakers.
4. Import confirmed lineups 30-40 minutes before kickoff.
5. Re-run `/analysis/query/report` and `/value-bets/fixed/{match_id}`.

Never treat the output as guaranteed betting advice. The model is still a decision-support tool and needs historical odds validation before real-money use.
