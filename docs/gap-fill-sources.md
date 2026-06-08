# Recent form gap-fill sources

This file documents the manual gap-fill layer used when StatsBomb open data does not include a qualified 2026 national team.

## Method

- StatsBomb event-derived metrics remain the preferred source.
- Teams missing from StatsBomb are assigned `data_quality=recent_form_gap_fill`.
- These records use public recent results, qualification context, goals for/against and conservative opponent-strength judgement.
- The model gives this layer a lower reliability weight than event-level data, so it is useful for prode/testing but not enough for high-confidence betting.

## Sources checked on 2026-06-08

- Algeria: 11v11 Algeria fixtures and Algeria Football News fixture/results pages.
- Bosnia and Herzegovina: NFSBiH 2026 A-team results, 11v11 match record, Goal fixtures/results.
- Cape Verde: 11v11 Cape Verde Islands score tables, ESPN results.
- Cote d'Ivoire: 11v11 Ivory Coast fixtures, FIFA African qualification context.
- Curacao: 11v11 Curacao fixtures and scores, BBC scores/fixtures, qualification context.
- DR Congo: FIFA African qualifying review, Goal fixtures/results, playoff context.
- Haiti: National Football Teams 2026 page and CONCACAF qualification context.
- Iraq: Soccer Iraq fixtures/results, ESPN results, AFC qualification context.
- Jordan: 11v11 Jordan 2026 season table and fixtures.
- New Zealand: FIFA/FourFourTwo qualification context and recent friendly context.
- Norway: 11v11 Norway 2026 scores, ESPN results, UEFA qualifying context.
- South Africa: 11v11 South Africa fixtures, ESPN results, FourFourTwo squad/context.
- Uzbekistan: ESPN results, 11v11/qualification context.

## Caveat

These values are not raw xG. They are goals/form proxies shrunk toward international baselines by the reliability system. Before placing any serious prediction, import confirmed lineups 30-40 minutes before kickoff and refresh odds.
