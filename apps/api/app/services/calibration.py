from app.services import data
from app.services.prediction import predict_match


def _bucket(probability: float) -> str:
    low = int(probability * 10) * 10
    high = low + 10
    return f"{low}-{high}%"


def _actual(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "Home"
    if home_goals < away_goals:
        return "Away"
    return "Draw"


def seed_calibration_report(dataset: str = "seed_backtest_demo") -> dict:
    rows = [row for row in data.historical_results() if row.get("dataset") == dataset]
    buckets: dict[str, dict] = {}
    for row in rows:
        prediction = predict_match(str(row["match_id"]))
        actual = _actual(int(row["home_goals"]), int(row["away_goals"]))
        for market in prediction.markets["1X2"]:
            bucket = _bucket(market.probability)
            entry = buckets.setdefault(bucket, {"predicted_total": 0.0, "count": 0, "hits": 0})
            entry["predicted_total"] += market.probability
            entry["count"] += 1
            entry["hits"] += 1 if market.selection == actual else 0

    result = []
    for bucket, entry in sorted(buckets.items()):
        count = entry["count"]
        result.append(
            {
                "bucket": bucket,
                "count": count,
                "avg_predicted_probability": round(entry["predicted_total"] / count, 4) if count else 0.0,
                "observed_hit_rate": round(entry["hits"] / count, 4) if count else 0.0,
                "calibration_error": round(abs((entry["predicted_total"] / count) - (entry["hits"] / count)), 4) if count else 0.0,
            }
        )

    return {
        "dataset": dataset,
        "status": "SMALL_SAMPLE_DIAGNOSTIC",
        "buckets": result,
        "notes": [
            "This calibration view is only as good as the historical dataset behind it.",
            "Use rolling StatsBomb and historical odds before trusting betting decisions.",
        ],
    }
