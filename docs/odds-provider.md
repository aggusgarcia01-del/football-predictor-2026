# Odds Provider

The app can import prematch odds through The Odds API. It does not scrape bookmaker websites.

## Setup

Create an API key at `https://the-odds-api.com/`, then set:

```powershell
$env:THE_ODDS_API_KEY="your_api_key"
```

## Import

From the UI press `Importar cuotas API`, or call:

```text
POST /data/odds-provider/the-odds-api?sport=soccer_fifa_world_cup&regions=us,eu,uk&markets=h2h
```

The connector imports only events that match local fixtures and converts `h2h` into local `1X2` selections:

- `Home`
- `Draw`
- `Away`

World Cup 2026 markets may not be available until bookmakers/provider publish them. Until then, use manual odds import.

## Alert Rules

Prematch alerts are available at:

```text
GET /value-bets/prematch-alerts
```

Alerts require a combination of model probability, imported price, data reliability and lineup readiness. They are not guarantees and should be rechecked 30-40 minutes before kickoff.
