"""Risk control rules for short-term strategy."""

from __future__ import annotations

from typing import Any, Dict


def short_term_risk_control(market_sentiment_score: float) -> Dict[str, Any]:
    """
    Return strict short-term risk controls.

    Rules:
    - max position <= 15%
    - stop loss -6%
    - if market sentiment < 40, block opening new positions
    """
    market_filter = market_sentiment_score >= 40
    return {
        "max_position": 0.15,
        "stop_loss": -6,
        "take_profit": 12,
        "break_ma5_stop": True,
        "market_filter": market_filter,
        "risk_note": "no new position when sentiment score < 40",
    }


def validate_trade_plan(plan: Dict[str, Any], market_sentiment_score: float) -> Dict[str, Any]:
    """Validate a candidate trade plan against risk control rules."""
    rc = short_term_risk_control(market_sentiment_score)
    position = float(plan.get("position", 0))
    stop_loss = float(plan.get("stop_loss", 0))

    violations: list[str] = []
    if position > rc["max_position"]:
        violations.append("position_over_limit")
    if stop_loss < rc["stop_loss"]:
        violations.append("stop_loss_too_wide")
    if not rc["market_filter"]:
        violations.append("market_sentiment_blocked")

    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "risk_control": rc,
    }
