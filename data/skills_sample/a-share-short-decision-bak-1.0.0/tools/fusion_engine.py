"""Signal fusion engine for short-term stock decisions."""

from __future__ import annotations

from typing import Any, Dict, List

from .debug_utils import resolve_debug, with_debug
from .indicators import clamp
from .market_data import get_market_sentiment, get_sector_rotation, scan_strong_stocks
from .money_flow import analyze_capital_flow
from .risk_control import short_term_risk_control


def _calc_sector_score(top_sectors: List[dict[str, Any]]) -> float:
    if not top_sectors:
        return 0.0
    top3 = top_sectors[:3]
    return sum(float(x.get("strength", 0.0)) for x in top3) / len(top3)


def _calc_stock_volume_score(stocks: List[dict[str, Any]]) -> float:
    if not stocks:
        return 0.0
    top = stocks[0]
    ratio = float(top.get("volume_ratio", 0.0))
    change = float(top.get("change_pct", 0.0))
    return clamp(ratio / 3.0 * 60 + change / 10.0 * 40, 0, 100)


def _calc_capital_score(capital: dict[str, Any]) -> float:
    main_flow = float(capital.get("main_flow", 0.0))
    inflow_days = float(capital.get("northbound_inflow_days", 0.0))
    score = clamp(main_flow / 300_000_000 * 70, 0, 70) + clamp(inflow_days / 5 * 30, 0, 30)
    return clamp(score, 0, 100)


def _calc_technical_score(stocks: List[dict[str, Any]]) -> float:
    if not stocks:
        return 0.0
    top = stocks[0]
    ratio = float(top.get("volume_ratio", 0.0))
    return clamp(55 + ratio * 10, 0, 100)


def _build_no_recommendation_message(
    signal: str,
    stocks: List[dict[str, Any]],
    top_sectors: List[dict[str, Any]],
    sentiment_score: float,
) -> str:
    if signal == "SHORT_BUY" and stocks:
        return "已筛选到可跟踪标的，请结合盘中量能确认后执行。"
    if sentiment_score < 40:
        return "当前市场情绪偏弱，建议禁止开新仓，等待情绪修复。"
    if not top_sectors:
        return "未获取到可靠板块轮动数据，建议今日观望，等待数据恢复。"
    if not stocks:
        return "当前未筛选到满足短线条件的真实标的，建议继续观望。"
    return "当前不满足短线开仓条件，建议观望。"


def short_term_signal_engine(analysis_date: str | None = None, debug: bool = False) -> Dict[str, Any]:
    """Build weighted short-term signal."""
    debug = resolve_debug(debug)
    sentiment = get_market_sentiment(analysis_date=analysis_date, debug=debug)
    sector_info = get_sector_rotation(top_n=5, analysis_date=analysis_date, debug=debug)
    sector_names = [x["name"] for x in sector_info.get("top_sectors", [])]
    stocks = scan_strong_stocks(sectors=sector_names, top_n=5, analysis_date=analysis_date, debug=debug)
    target_symbol = stocks[0]["code"] if stocks else None
    capital = analyze_capital_flow(symbol=target_symbol, analysis_date=analysis_date, debug=debug)
    risk = short_term_risk_control(float(sentiment.get("market_sentiment_score", 0.0)))

    sentiment_score = float(sentiment.get("market_sentiment_score", 0.0))
    sector_score = _calc_sector_score(sector_info.get("top_sectors", []))
    stock_score = _calc_stock_volume_score(stocks)
    capital_score = _calc_capital_score(capital)
    technical_score = _calc_technical_score(stocks)

    score = (
        sentiment_score * 0.25
        + sector_score * 0.25
        + stock_score * 0.20
        + capital_score * 0.20
        + technical_score * 0.10
    )
    score = round(clamp(score, 0, 100), 2)

    if score >= 75 and risk["market_filter"] and len(stocks) > 0:
        signal = "SHORT_BUY"
        confidence = clamp(score / 100.0 * 0.9, 0.0, 0.95)
        holding_days = "1-3"
    elif score >= 60 and risk["market_filter"]:
        signal = "WATCHLIST"
        confidence = clamp(score / 100.0 * 0.75, 0.0, 0.85)
        holding_days = "1-2"
    else:
        signal = "NO_TRADE"
        confidence = clamp(score / 100.0 * 0.6, 0.0, 0.7)
        holding_days = "0"

    no_msg = _build_no_recommendation_message(signal, stocks, sector_info.get("top_sectors", []), sentiment_score)

    payload = {
        "analysis_date": sentiment.get("analysis_date", analysis_date),
        "score": score,
        "signal": signal,
        "holding_days": holding_days,
        "confidence": round(confidence, 2),
        "risk_control": risk,
        "market_sentiment": sentiment,
        "top_sectors": sector_info.get("top_sectors", []),
        "candidates": stocks,
        "capital_flow": capital,
        "has_recommendation": len(stocks) > 0 and signal == "SHORT_BUY",
        "no_recommendation_message": no_msg,
        "factor_breakdown": {
            "market_sentiment": round(sentiment_score, 2),
            "sector_strength": round(sector_score, 2),
            "stock_volume_strength": round(stock_score, 2),
            "capital_inflow": round(capital_score, 2),
            "technical_structure": round(technical_score, 2),
        },
    }
    if not debug:
        return payload
    debug_info = {
        "module": "short_term_signal_engine",
        "selected_symbol": target_symbol,
        "sources": {
            "market_sentiment": sentiment.get("data_source", "unknown"),
            "sector_rotation": sector_info.get("data_source", "unknown"),
            "capital_flow": capital.get("data_source", "unknown"),
        },
    }
    return with_debug(payload, debug, debug_info)
