"""A-share short-term decision tools package."""

from .decision_eval import compare_prediction_with_market, run_prediction_for_date
from .fusion_engine import short_term_signal_engine
from .market_data import get_market_sentiment, get_sector_rotation, scan_strong_stocks
from .money_flow import analyze_capital_flow
from .reporting import generate_daily_report
from .risk_control import short_term_risk_control

__all__ = [
    "get_market_sentiment",
    "get_sector_rotation",
    "scan_strong_stocks",
    "analyze_capital_flow",
    "short_term_signal_engine",
    "short_term_risk_control",
    "generate_daily_report",
    "run_prediction_for_date",
    "compare_prediction_with_market",
]
