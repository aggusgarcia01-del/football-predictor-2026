from datetime import UTC, datetime

from app.models.schemas import ProdeBoard, ProdePrediction
from app.services import data
from app.services.prediction import predict_match
from app.services.statistical_inputs import reliability


def _probability(prediction, market: str, selection: str) -> float:
    for row in prediction.markets.get(market, []):
        if row.selection == selection:
            return row.probability
    return 0.0


def _confidence(max_probability: float, data_reliability: float) -> str:
    if data_reliability < 0.45:
        return "BAJA"
    if max_probability >= 0.62 and data_reliability >= 0.65:
        return "ALTA"
    if max_probability >= 0.5 and data_reliability >= 0.55:
        return "MEDIA"
    return "MEDIA-BAJA"


def _pick(home: float, draw: float, away: float) -> tuple[str, str, float]:
    options = [
        ("1", "Gana local", home),
        ("X", "Empate", draw),
        ("2", "Gana visitante", away),
    ]
    return max(options, key=lambda row: row[2])


def prode_predictions() -> ProdeBoard:
    rows: list[ProdePrediction] = []
    for match_id in data.matches():
        prediction = predict_match(match_id)
        home = _probability(prediction, "1X2", "Home")
        draw = _probability(prediction, "1X2", "Draw")
        away = _probability(prediction, "1X2", "Away")
        pick, pick_label, pick_probability = _pick(home, draw, away)
        exact_score = prediction.top_exact_scores[0].score if prediction.top_exact_scores else "0-0"
        home_metrics = data.team_metrics().get(prediction.match.home_team.id)
        away_metrics = data.team_metrics().get(prediction.match.away_team.id)
        data_reliability = round((reliability(home_metrics) + reliability(away_metrics)) / 2, 4)
        confidence = _confidence(pick_probability, data_reliability)
        warnings: list[str] = []
        if data_reliability < 0.55:
            warnings.append("Datos estadisticos incompletos o gap-fill; usar como pronostico conservador.")
        if prediction.prematch_status.overall_readiness != "READY":
            warnings.append("Formaciones no confirmadas; actualizar 30-40 minutos antes del partido.")
        if pick_probability < 0.45:
            warnings.append("Partido muy parejo; el signo del prode tiene baja separacion.")

        rows.append(
            ProdePrediction(
                match=prediction.match,
                pick=pick,
                pick_label=pick_label,
                exact_score=exact_score,
                confidence=confidence,
                home_win_probability=home,
                draw_probability=draw,
                away_win_probability=away,
                expected_goals_home=prediction.expected_goals_home,
                expected_goals_away=prediction.expected_goals_away,
                data_reliability=data_reliability,
                rationale=[
                    f"Probabilidad mas alta del 1X2: {pick_label} ({pick_probability:.1%}).",
                    f"xG esperado: {prediction.match.home_team.name} {prediction.expected_goals_home:.2f} - {prediction.expected_goals_away:.2f} {prediction.match.away_team.name}.",
                    f"Marcador exacto modal del Poisson/DC: {exact_score}.",
                ],
                warnings=warnings,
            )
        )

    rows.sort(key=lambda row: (row.match.date, row.match.id))
    return ProdeBoard(
        status="RESEARCH_PRODE_NOT_GUARANTEED",
        generated_at=datetime.now(UTC).isoformat(),
        predictions=rows,
        notes=[
            "El pick de prode usa el signo 1X2 con mayor probabilidad, no valor de cuota.",
            "El marcador exacto es el score modal, pero los marcadores exactos siempre tienen alta varianza.",
            "Recalcular despues de importar alineaciones reales y cuotas prematch.",
        ],
    )
