"""Simple CLI for the A-share short-term decision skill."""

from __future__ import annotations

import argparse
import json
import os

from tools.decision_eval import compare_prediction_with_market, run_prediction_for_date
from tools.fusion_engine import short_term_signal_engine
from tools.market_data import get_market_sentiment, get_sector_rotation, scan_strong_stocks
from tools.money_flow import analyze_capital_flow
from tools.reporting import generate_daily_report
from tools.risk_control import short_term_risk_control


def _print(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="A-share short-term decision tools")
    parser.add_argument(
        "tool",
        choices=[
            "get_market_sentiment",
            "get_sector_rotation",
            "scan_strong_stocks",
            "analyze_capital_flow",
            "short_term_signal_engine",
            "short_term_risk_control",
            "generate_daily_report",
            "run_prediction_for_date",
            "compare_prediction_with_market",
        ],
    )
    parser.add_argument("--symbol", default=None, help="stock symbol for capital flow tool")
    parser.add_argument("--score", type=float, default=50, help="market sentiment score for risk control tool")
    parser.add_argument("--date", default=None, help="analysis date, format YYYY-MM-DD or YYYYMMDD")
    parser.add_argument("--prediction-date", default=None, help="prediction date for comparison, format YYYY-MM-DD")
    parser.add_argument("--actual-date", default=None, help="actual comparison date, format YYYY-MM-DD")
    parser.add_argument("--debug", action="store_true", help="enable debug_info in outputs")
    args = parser.parse_args()

    debug = bool(args.debug)
    if debug:
        os.environ["SHORT_DECISION_DEBUG"] = "1"

    if args.tool == "get_market_sentiment":
        _print(get_market_sentiment(analysis_date=args.date, debug=debug))
    elif args.tool == "get_sector_rotation":
        _print(get_sector_rotation(analysis_date=args.date, debug=debug))
    elif args.tool == "scan_strong_stocks":
        _print(scan_strong_stocks(analysis_date=args.date, debug=debug))
    elif args.tool == "analyze_capital_flow":
        _print(analyze_capital_flow(symbol=args.symbol, analysis_date=args.date, debug=debug))
    elif args.tool == "short_term_signal_engine":
        _print(short_term_signal_engine(analysis_date=args.date, debug=debug))
    elif args.tool == "short_term_risk_control":
        _print(short_term_risk_control(args.score))
    elif args.tool == "generate_daily_report":
        _print(generate_daily_report(analysis_date=args.date, debug=debug))
    elif args.tool == "run_prediction_for_date":
        if not args.date:
            raise SystemExit("--date is required for run_prediction_for_date")
        _print(run_prediction_for_date(analysis_date=args.date, debug=debug))
    else:
        pred_date = args.prediction_date or args.date
        if not pred_date:
            raise SystemExit("--prediction-date (or --date) is required for compare_prediction_with_market")
        _print(
            compare_prediction_with_market(
                prediction_date=pred_date,
                actual_date=args.actual_date,
                auto_generate_if_missing=True,
                debug=debug,
            )
        )


if __name__ == "__main__":
    main()
