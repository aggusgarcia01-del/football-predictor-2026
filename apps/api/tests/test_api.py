from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_matches() -> None:
    response = client.get("/matches")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_prediction() -> None:
    response = client.get("/predictions/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DEMO_NOT_PRODUCTION_VALIDATED"
    assert "1X2" in body["markets"]
    assert "Double Chance" in body["markets"]
    assert len(body["top_exact_scores"]) >= 3
    assert len(body["adjustments"]) >= 4
    assert body["prematch_status"]["overall_readiness"] in {
        "PROVISIONAL_PROBABLE_LINEUPS",
        "READY_CONFIRMED_LINEUPS",
        "NOT_READY_MISSING_LINEUPS",
    }


def test_match_analysis() -> None:
    response = client.get("/analysis/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["resolved_match"]["id"] == "fwc26-001"
    assert len(body["evidence"]) >= 5
    assert "Lean:" in body["recommendation"]
    assert "## Evidencias" in body["report_markdown"]


def test_match_query_analysis() -> None:
    response = client.post("/analysis/query", json={"question": "Analiza Mexico vs Sudafrica"})
    assert response.status_code == 200
    assert response.json()["resolved_match"]["id"] == "fwc26-001"


def test_custom_match_query_analysis() -> None:
    response = client.post("/analysis/query", json={"question": "Analiza Argentina vs Francia"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolved_match"]["id"] == "custom-arg-fra"
    assert body["prediction"]["markets"]["1X2"][0]["odds"] is None


def test_match_query_report() -> None:
    response = client.post("/analysis/query/report", json={"question": "Analiza Mexico vs Sudafrica"})
    assert response.status_code == 200
    assert "Mexico vs South Africa" in response.text
    assert "## Pronostico" in response.text


def test_value_bets_today() -> None:
    response = client.get("/value-bets/today")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["ev"] > 0.03


def test_backtest_run() -> None:
    response = client.post("/backtests/run")
    assert response.status_code == 200
    body = response.json()
    assert body["matches_evaluated"] == 3
    assert "production_gate_status" in body


def test_tournament_simulation() -> None:
    response = client.get("/simulation/tournament?iterations=100")
    assert response.status_code == 200
    body = response.json()
    assert body["iterations"] == 100
    assert len(body["teams"]) >= 4


def test_model_health() -> None:
    response = client.get("/model/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"GREEN", "RED"}
    assert "production_gate_status" in body


def test_match_readiness() -> None:
    response = client.get("/model/match-readiness/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "fwc26-001"
    assert "data_reliability" in body
    assert "blockers" in body
    assert "ready_for_strong_opinion" in body


def test_prediction_trust() -> None:
    response = client.get("/model/trust/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "fwc26-001"
    assert 0 <= body["trust_score"] <= 100
    assert body["trust_grade"] in {"HIGH_TRUST", "MEDIUM_TRUST", "LOW_TRUST", "RESEARCH_ONLY"}
    assert "components" in body


def test_match_cockpit() -> None:
    response = client.get("/analysis/fwc26-001/cockpit")
    assert response.status_code == 200
    body = response.json()
    assert "analysis" in body
    assert "trust" in body
    assert "readiness" in body
    assert "odds_board" in body


def test_data_audit() -> None:
    response = client.get("/data/audit")
    assert response.status_code == 200
    body = response.json()
    assert "weak_team_count" in body
    assert "metrics_by_quality" in body


def test_rolling_backtest() -> None:
    response = client.post("/backtests/run?dataset=statsbomb_rolling_xg")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"] == "statsbomb_rolling_xg"
    assert "production_gate_status" in body


def test_prematch_alerts() -> None:
    response = client.get("/value-bets/prematch-alerts")
    assert response.status_code == 200
    body = response.json()
    assert "alerts" in body


def test_betting_decision() -> None:
    response = client.get("/value-bets/decision/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in {
        "NO_APOSTAR",
        "APUESTA_CANDIDATA",
        "ESPERAR_CONFIRMACION",
        "BUSCAR_CUOTA",
        "PROBABLE_PERO_SIN_VALOR",
    }
    assert "selection_label" in body
    assert "plain_language" in body


def test_price_targets() -> None:
    response = client.get("/value-bets/price-targets/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert "targets" in body
    assert any(row["market"] == "Double Chance" for row in body["targets"])


def test_research_local_match() -> None:
    response = client.post("/research/match", json={"home_team": "Mexico", "away_team": "South Africa"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "LOCAL_MODEL_MATCHED"
    assert len(body["probabilities"]) >= 3


def test_research_unknown_match_without_provider_key() -> None:
    response = client.post("/research/match", json={"home_team": "Team A Unknown", "away_team": "Team B Unknown"})
    assert response.status_code == 200
    assert response.json()["status"] in {"NEEDS_DATA_PROVIDER_KEY", "PROVIDER_NO_MATCH_FOUND"}


def test_live_lab_snapshot() -> None:
    response = client.post(
        "/live-lab/snapshot?save=false",
        json={"home_team": "Flamengo", "away_team": "Cusco FC", "minute": 51, "home_goals": 0, "away_goals": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "LIVE_RESEARCH_SNAPSHOT"
    assert "probabilities" in body


def test_api_football_live_without_key_or_data() -> None:
    response = client.get("/providers/api-football/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"MISSING_API_FOOTBALL_KEY", "LIVE_FIXTURES_IMPORTED_FROM_PROVIDER"}


def test_training_instructions() -> None:
    response = client.get("/providers/training")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "TRAINING_WORKFLOW"
    assert len(body["steps"]) >= 3


def test_odds_provider_without_key() -> None:
    response = client.post("/data/odds-provider/the-odds-api?dry_run=true")
    assert response.status_code == 200
    assert response.json()["status"] in {"MISSING_API_KEY", "DRY_RUN", "NO_MATCHED_ODDS", "IMPORTED"}


def test_odds_board() -> None:
    response = client.get("/value-bets/odds-board/fwc26-001")
    assert response.status_code == 200
    body = response.json()
    assert body["market"] == "1X2"
    assert "best_by_selection" in body


def test_prematch_status() -> None:
    response = client.get("/prematch/fwc26-001/status")
    assert response.status_code == 200
    body = response.json()
    assert body["home_lineup_status"] in {"probable", "confirmed", "official"}


def test_lineup_import() -> None:
    payload = {
        "lineups": [
            {
                "match_id": "test-match",
                "team_id": "arg",
                "status": "confirmed",
                "source": "test",
                "updated_at": "2026-06-12T20:20:00Z",
                "formation": "4-3-3",
                "players": [
                    {
                        "name": "Test Player",
                        "position": "FW",
                        "status": "starter",
                        "rating": 80,
                        "fitness": 1,
                        "expected_minutes": 90,
                    }
                ],
            }
        ]
    }
    response = client.post("/prematch/lineups/import", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "LINEUPS_IMPORTED_AND_ACTIVE"


def test_import_dataset() -> None:
    response = client.post(
        "/data/import/odds",
        json={"records": [{"match_id": "x", "market": "1X2", "selection": "Home", "decimal_odds": 2.0}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["records_written"] >= 1


def test_import_dataset_rejects_bad_odds() -> None:
    response = client.post(
        "/data/import/odds",
        json={"records": [{"match_id": "x", "market": "1X2", "selection": "Maybe", "decimal_odds": 2.0}]},
    )
    assert response.status_code == 400


def test_data_coverage() -> None:
    response = client.get("/data/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["teams_total"] >= 48
    assert "average_reliability" in body


def test_import_real_team_metrics() -> None:
    response = client.post(
        "/data/import/team_metrics",
        json={
            "records": [
                {
                    "team_id": "mex",
                    "source": "manual_verified",
                    "source_name": "Manual verified test",
                    "source_url": "https://example.com",
                    "as_of": "2026-06-10",
                    "sample_size_matches": 12,
                    "is_real_data": True,
                    "data_quality": "manual_verified",
                    "npxg_for_per90": 1.4,
                    "npxg_against_per90": 1.0,
                    "shots_on_target_for_per90": 4.5,
                    "recent_form_points_per_match": 1.8,
                }
            ]
        },
    )
    assert response.status_code == 200
    coverage = client.get("/data/coverage").json()
    mexico = next(row for row in coverage["teams"] if row["team_id"] == "mex")
    assert mexico["reliability"] > 0.5
