from app.models.schemas import BookmakerPrice, FixedBetCandidate, ValueOpportunity
from app.services import data
from app.services.prediction import predict_match
from app.services.statistical_inputs import reliability


SELECTION_ORDER = ("Home", "Draw", "Away")
SAFER_MARKETS = {"Double Chance", "Over/Under 2.5", "BTTS"}


def _kelly_fraction(probability: float, odds: float) -> float:
    if odds <= 1:
        return 0.0
    return max(0.0, (probability * odds - 1) / (odds - 1))


def _tier(ev: float) -> str:
    if ev > 0.08:
        return "HIGH CONVICTION"
    if ev >= 0.04:
        return "MEDIUM"
    return "SPECULATIVE"


def _selection_label(selection: str, home: str, away: str) -> str:
    return {"Home": home, "Draw": "Draw", "Away": away}.get(selection, selection)


def _bookmaker_prices(match_id: str, market: str, selection: str, model_probability: float) -> list[BookmakerPrice]:
    prices: list[BookmakerPrice] = []
    for row in data.odds():
        if row.get("match_id") != match_id or row.get("market") != market or row.get("selection") != selection:
            continue
        odds = float(row["decimal_odds"])
        prices.append(
            BookmakerPrice(
                bookmaker=str(row.get("bookmaker", "unknown")),
                market=market,
                selection=selection,
                odds=odds,
                implied_probability=round(1 / odds, 4),
                ev=round(model_probability * odds - 1, 4),
            )
        )
    return sorted(prices, key=lambda item: item.odds, reverse=True)


def value_bets_for_match(match_id: str, threshold: float = 0.03) -> list[ValueOpportunity]:
    prediction = predict_match(match_id)
    opportunities: list[ValueOpportunity] = []

    for row in prediction.markets["1X2"]:
        if row.odds is None or row.ev is None or row.ev <= threshold:
            continue

        kelly = _kelly_fraction(row.probability, row.odds)
        opportunities.append(
            ValueOpportunity(
                match=prediction.match,
                market="1X2",
                selection=row.selection,
                model_probability=row.probability,
                odds=row.odds,
                implied_probability=row.implied_probability or round(1 / row.odds, 4),
                ev=row.ev,
                kelly_fraction=round(kelly, 4),
                recommended_fractional_kelly=round(min(kelly * 0.25, 0.05), 4),
                confidence_tier=_tier(row.ev),
                status="DEMO_NOT_PRODUCTION_VALIDATED",
            )
        )

    return opportunities


def all_value_bets(threshold: float = 0.03) -> list[ValueOpportunity]:
    opportunities: list[ValueOpportunity] = []
    for match_id in data.matches():
        opportunities.extend(value_bets_for_match(match_id, threshold))
    return sorted(opportunities, key=lambda item: item.ev, reverse=True)


def fixed_bet_for_match(match_id: str, min_probability: float = 0.55, min_ev: float = 0.02) -> FixedBetCandidate:
    prediction = predict_match(match_id)
    home_metrics = data.team_metrics().get(prediction.match.home_team.id)
    away_metrics = data.team_metrics().get(prediction.match.away_team.id)
    avg_reliability = (reliability(home_metrics) + reliability(away_metrics)) / 2
    readiness = prediction.prematch_status.overall_readiness

    ranked = sorted(prediction.markets["1X2"], key=lambda item: item.probability, reverse=True)
    best = ranked[0]
    prices = _bookmaker_prices(match_id, "1X2", best.selection, best.probability)
    best_price = prices[0] if prices else None
    ev = best_price.ev if best_price else None
    odds = best_price.odds if best_price else None
    implied = best_price.implied_probability if best_price else None
    kelly = _kelly_fraction(best.probability, odds) if odds else 0.0

    status = "NO_BET"
    tier = "WAIT"
    if odds is None:
        status = "WAITING_FOR_REAL_ODDS"
        tier = "NO_ODDS"
    elif best.probability >= min_probability and ev is not None and ev >= min_ev and avg_reliability >= 0.55:
        status = "FIXED_BET_CANDIDATE"
        tier = _tier(ev)
    elif best.probability >= min_probability and ev is not None and ev >= min_ev:
        status = "WATCHLIST_DATA_RISK"
        tier = "DATA_RISK"
    elif best.probability >= min_probability:
        status = "LIKELY_OUTCOME_BAD_PRICE"
        tier = "LOW_VALUE"

    rationale = [
        f"Model top selection: {_selection_label(best.selection, prediction.match.home_team.name, prediction.match.away_team.name)} at {round(best.probability * 100, 1)}%.",
        f"Average data reliability: {avg_reliability:.2f}.",
        f"Prematch readiness: {readiness}.",
    ]
    if best_price:
        rationale.append(
            f"Best imported price: {best_price.bookmaker} @ {best_price.odds} with EV {round(best_price.ev * 100, 1)}%."
        )
    else:
        rationale.append("No real bookmaker odds imported yet for this selection.")
    if readiness != "READY_CONFIRMED_LINEUPS":
        rationale.append("Treat as provisional until confirmed lineups are imported 30-40 minutes before kickoff.")

    return FixedBetCandidate(
        match=prediction.match,
        market="1X2",
        selection=best.selection,
        model_probability=best.probability,
        best_odds=odds,
        best_bookmaker=best_price.bookmaker if best_price else None,
        implied_probability=implied,
        ev=ev,
        recommended_fractional_kelly=round(min(kelly * 0.20, 0.03), 4),
        confidence_tier=tier,
        status=status,
        rationale=rationale,
        bookmaker_prices=prices,
    )


def best_fixed_bets(limit: int = 5) -> list[FixedBetCandidate]:
    candidates = [fixed_bet_for_match(match_id) for match_id in data.matches()]
    priority = {
        "FIXED_BET_CANDIDATE": 0,
        "WATCHLIST_DATA_RISK": 1,
        "LIKELY_OUTCOME_BAD_PRICE": 2,
        "WAITING_FOR_REAL_ODDS": 3,
        "NO_BET": 4,
    }
    return sorted(
        candidates,
        key=lambda item: (
            priority.get(item.status, 9),
            -(item.ev if item.ev is not None else -1),
            -item.model_probability,
        ),
    )[: max(1, min(limit, 20))]


def odds_board_for_match(match_id: str) -> dict:
    prediction = predict_match(match_id)
    probabilities = {row.selection: row.probability for row in prediction.markets["1X2"]}
    rows = [row for row in data.odds() if row.get("match_id") == match_id and row.get("market") == "1X2"]

    by_bookmaker: dict[str, dict] = {}
    for row in rows:
        bookmaker = str(row.get("bookmaker") or "Manual")
        selection = str(row.get("selection"))
        odds = float(row.get("decimal_odds"))
        by_bookmaker.setdefault(bookmaker, {})[selection] = odds

    bookmakers: list[dict] = []
    best_by_selection: dict[str, dict | None] = {selection: None for selection in SELECTION_ORDER}
    for bookmaker, prices in sorted(by_bookmaker.items()):
        implied_total = sum(1 / float(prices[selection]) for selection in SELECTION_ORDER if selection in prices)
        selections: list[dict] = []
        for selection in SELECTION_ORDER:
            if selection not in prices:
                continue
            odds = float(prices[selection])
            ev = probabilities.get(selection, 0.0) * odds - 1
            item = {
                "selection": selection,
                "odds": odds,
                "model_probability": probabilities.get(selection),
                "implied_probability": round(1 / odds, 4),
                "ev": round(ev, 4),
            }
            selections.append(item)
            current = best_by_selection[selection]
            if current is None or odds > current["odds"]:
                best_by_selection[selection] = {"bookmaker": bookmaker, **item}
        bookmakers.append(
            {
                "bookmaker": bookmaker,
                "complete_1x2": all(selection in prices for selection in SELECTION_ORDER),
                "overround": round(implied_total - 1, 4) if implied_total else None,
                "selections": selections,
            }
        )

    return {
        "match": prediction.match.model_dump(),
        "market": "1X2",
        "bookmakers": bookmakers,
        "best_by_selection": best_by_selection,
        "notes": [
            "Overround near 0.03-0.08 is typical for many 1X2 markets; very high overround makes value harder.",
            "The model uses the best imported odd per selection when calculating EV.",
            "Use only odds you are allowed to enter manually or via a permitted API.",
        ],
    }


def price_targets_for_match(match_id: str, min_edge: float = 0.04) -> dict:
    prediction = predict_match(match_id)
    targets: list[dict] = []
    for market, selections in prediction.markets.items():
        for item in selections:
            fair_odds = 1 / item.probability if item.probability > 0 else None
            minimum_odds = fair_odds * (1 + min_edge) if fair_odds else None
            prices = _bookmaker_prices(match_id, market, item.selection, item.probability)
            best_price = prices[0] if prices else None
            targets.append(
                {
                    "market": market,
                    "selection": item.selection,
                    "model_probability": item.probability,
                    "fair_odds": round(fair_odds, 3) if fair_odds else None,
                    "minimum_odds_for_value": round(minimum_odds, 3) if minimum_odds else None,
                    "best_imported_odds": best_price.odds if best_price else item.odds,
                    "best_bookmaker": best_price.bookmaker if best_price else None,
                    "ev_at_best_odds": best_price.ev if best_price else item.ev,
                    "is_safer_market": market in SAFER_MARKETS and item.probability >= 0.62,
                }
            )
    return {
        "match": prediction.match.model_dump(),
        "min_edge": min_edge,
        "targets": sorted(targets, key=lambda row: (-row["model_probability"], row["market"], row["selection"])),
        "notes": [
            "Fair odds are the model's no-margin price.",
            "Minimum odds for value includes the requested edge. If the available price is lower, wait.",
            "Safer markets have higher probability, but they are not guaranteed.",
        ],
    }


def _best_safer_target(match_id: str) -> dict | None:
    candidates = [
        row
        for row in price_targets_for_match(match_id)["targets"]
        if row["is_safer_market"] and row["model_probability"] >= 0.65
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda row: (
            row["ev_at_best_odds"] is None,
            -(row["ev_at_best_odds"] or -99),
            -row["model_probability"],
        ),
    )[0]


def prematch_alerts(limit: int = 5) -> dict:
    alerts: list[dict] = []
    for match_id in data.matches():
        prediction = predict_match(match_id)
        home_metrics = data.team_metrics().get(prediction.match.home_team.id)
        away_metrics = data.team_metrics().get(prediction.match.away_team.id)
        avg_reliability = (reliability(home_metrics) + reliability(away_metrics)) / 2
        fixed = fixed_bet_for_match(match_id)
        top_probability = fixed.model_probability
        ev = fixed.ev or 0.0
        confidence_penalty = max(0.0, 0.65 - avg_reliability)
        required_ev = 0.03 + confidence_penalty * 0.12
        alert_status = "NO_ALERT"
        if fixed.status == "FIXED_BET_CANDIDATE" and ev >= required_ev:
            alert_status = "BETTABLE_WATCH"
        elif top_probability >= 0.62 and fixed.status in {"LIKELY_OUTCOME_BAD_PRICE", "WAITING_FOR_REAL_ODDS"}:
            alert_status = "HIGH_PROBABILITY_MONITOR_PRICE"
        elif fixed.status == "WATCHLIST_DATA_RISK":
            alert_status = "WATCHLIST_NEEDS_DATA"

        if alert_status == "NO_ALERT":
            continue
        alerts.append(
            {
                "match": fixed.match.model_dump(),
                "selection": fixed.selection,
                "model_probability": top_probability,
                "best_odds": fixed.best_odds,
                "best_bookmaker": fixed.best_bookmaker,
                "ev": fixed.ev,
                "required_ev_after_confidence": round(required_ev, 4),
                "alert_status": alert_status,
                "recommended_fractional_kelly": fixed.recommended_fractional_kelly if alert_status == "BETTABLE_WATCH" else 0.0,
                "rationale": fixed.rationale
                + [
                    f"Required EV after confidence penalty: {round(required_ev * 100, 1)}%.",
                    "Prematch alert only; rerun after lineups and fresh odds.",
                ],
            }
        )

    return {
        "status": "ALERTS_READY",
        "alerts": sorted(
            alerts,
            key=lambda row: (row["alert_status"] != "BETTABLE_WATCH", -(row["ev"] or 0), -row["model_probability"]),
        )[: max(1, min(limit, 20))],
        "notes": [
            "This is not a guarantee to win. It flags candidates where probability, price and data quality deserve attention.",
            "Use only prematch. Recheck 30-40 minutes before kickoff with confirmed lineups.",
        ],
    }


def betting_decision_for_match(match_id: str) -> dict:
    prediction = predict_match(match_id)
    fixed = fixed_bet_for_match(match_id)
    safer_target = _best_safer_target(match_id)
    home_metrics = data.team_metrics().get(prediction.match.home_team.id)
    away_metrics = data.team_metrics().get(prediction.match.away_team.id)
    avg_reliability = round((reliability(home_metrics) + reliability(away_metrics)) / 2, 4)
    readiness = prediction.prematch_status.overall_readiness
    top_probability = fixed.model_probability
    ev = fixed.ev

    decision = "NO_APOSTAR"
    color = "red"
    action = "No hay apuesta recomendable ahora."
    stake = 0.0
    target_market = "1X2"
    target_selection = fixed.selection
    target_label = _selection_label(fixed.selection, prediction.match.home_team.name, prediction.match.away_team.name)
    target_probability = top_probability
    minimum_odds_for_value = None
    if safer_target:
        target_market = safer_target["market"]
        target_selection = safer_target["selection"]
        target_label = f"{safer_target['market']} - {safer_target['selection']}"
        target_probability = safer_target["model_probability"]
        minimum_odds_for_value = safer_target["minimum_odds_for_value"]

    if fixed.status == "FIXED_BET_CANDIDATE" and ev is not None and ev >= 0.04 and readiness == "READY_CONFIRMED_LINEUPS":
        decision = "APUESTA_CANDIDATA"
        color = "green"
        action = "Candidata para stake pequeño si aceptas el riesgo."
        stake = fixed.recommended_fractional_kelly
    elif safer_target and safer_target["ev_at_best_odds"] is not None and safer_target["ev_at_best_odds"] >= 0.04 and avg_reliability >= 0.50:
        decision = "APUESTA_CANDIDATA"
        color = "green"
        action = "Mercado de mayor probabilidad con valor positivo. Usar stake pequeño y revalidar lineups."
        stake = 0.01
    elif safer_target:
        decision = "BUSCAR_CUOTA"
        color = "blue"
        action = f"Buscar cuota minima {minimum_odds_for_value} para {target_label}."
    elif fixed.status in {"FIXED_BET_CANDIDATE", "WATCHLIST_DATA_RISK"} and ev is not None and ev > 0:
        decision = "ESPERAR_CONFIRMACION"
        color = "yellow"
        action = "Hay señal de valor, pero faltan datos o lineups."
    elif top_probability >= 0.60 and fixed.best_odds is None:
        decision = "BUSCAR_CUOTA"
        color = "blue"
        action = "Resultado probable, pero falta importar cuota real."
    elif top_probability >= 0.60 and (ev is None or ev < 0):
        decision = "PROBABLE_PERO_SIN_VALOR"
        color = "yellow"
        action = "Puede salir, pero la cuota no paga lo suficiente."

    blockers: list[str] = []
    if avg_reliability < 0.55:
        blockers.append("La confiabilidad media de datos es baja.")
    if readiness != "READY_CONFIRMED_LINEUPS":
        blockers.append("Faltan formaciones confirmadas.")
    if fixed.best_odds is None:
        blockers.append("Faltan cuotas reales importadas.")
    elif ev is not None and ev <= 0:
        blockers.append("La mejor cuota importada no tiene valor esperado positivo.")

    return {
        "match": fixed.match.model_dump(),
        "decision": decision,
        "color": color,
        "action": action,
        "market": target_market,
        "selection": target_selection,
        "selection_label": target_label,
        "model_probability": target_probability,
        "best_odds": fixed.best_odds,
        "best_bookmaker": fixed.best_bookmaker,
        "ev": ev,
        "minimum_odds_for_value": minimum_odds_for_value,
        "suggested_bankroll_fraction": stake,
        "data_reliability": avg_reliability,
        "prematch_readiness": readiness,
        "blockers": blockers,
        "plain_language": [
            f"Modelo: {target_label} tiene {round(target_probability * 100, 1)}% de probabilidad.",
            "Si el 1X2 no tiene valor, buscar mercados de mayor probabilidad como doble oportunidad, under/over o BTTS.",
            action,
        ],
        "responsible_note": "No es garantia ni consejo financiero. Usa stake bajo y solo con dinero que puedas perder.",
    }
