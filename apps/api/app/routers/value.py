from fastapi import APIRouter

from app.models.schemas import FixedBetCandidate, ValueOpportunity
from app.services.value import all_value_bets, best_fixed_bets, betting_decision_for_match, fixed_bet_for_match, odds_board_for_match, prematch_alerts, price_targets_for_match, value_bets_for_match

router = APIRouter(prefix="/value-bets", tags=["value-bets"])


@router.get("/today", response_model=list[ValueOpportunity])
def get_value_bets_today(threshold: float = 0.03) -> list[ValueOpportunity]:
    return all_value_bets(threshold)


@router.get("/match/{match_id}", response_model=list[ValueOpportunity])
def get_value_bets_for_match(match_id: str, threshold: float = 0.03) -> list[ValueOpportunity]:
    return value_bets_for_match(match_id, threshold)


@router.get("/fixed", response_model=list[FixedBetCandidate])
def get_fixed_bet_candidates(limit: int = 5) -> list[FixedBetCandidate]:
    return best_fixed_bets(limit)


@router.get("/fixed/{match_id}", response_model=FixedBetCandidate)
def get_fixed_bet_for_match(match_id: str) -> FixedBetCandidate:
    return fixed_bet_for_match(match_id)


@router.get("/odds-board/{match_id}")
def get_odds_board_for_match(match_id: str) -> dict:
    return odds_board_for_match(match_id)


@router.get("/prematch-alerts")
def get_prematch_alerts(limit: int = 5) -> dict:
    return prematch_alerts(limit)


@router.get("/decision/{match_id}")
def get_betting_decision_for_match(match_id: str) -> dict:
    return betting_decision_for_match(match_id)


@router.get("/price-targets/{match_id}")
def get_price_targets_for_match(match_id: str, min_edge: float = 0.04) -> dict:
    return price_targets_for_match(match_id, min_edge)
