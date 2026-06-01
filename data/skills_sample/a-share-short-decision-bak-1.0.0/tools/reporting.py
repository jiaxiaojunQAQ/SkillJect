"""Daily report generation for A-share short-term strategy."""

from __future__ import annotations

from typing import Any, Dict, List

from .debug_utils import resolve_debug
from .fusion_engine import short_term_signal_engine


def _fmt_sectors(sectors: List[dict[str, Any]]) -> str:
    if not sectors:
        return "无"
    lines = []
    for idx, item in enumerate(sectors[:3], start=1):
        lines.append(f"{idx}. {item.get('name', 'UNKNOWN')} (strength {item.get('strength', 0)})")
    return "\n".join(lines)


def _fmt_candidates(cands: List[dict[str, Any]]) -> str:
    if not cands:
        return "暂无"
    lines = []
    for item in cands[:3]:
        lines.append(
            f"{item.get('code', '')} {item.get('name', '')} | "
            f"chg {item.get('change_pct', 0)}% | vol {item.get('volume_ratio', 0)}x"
        )
    return "\n".join(lines)


def generate_daily_report(analysis_date: str | None = None, debug: bool = False) -> Dict[str, Any]:
    debug = resolve_debug(debug)
    signal = short_term_signal_engine(analysis_date=analysis_date, debug=debug)
    m = signal["market_sentiment"]
    sectors = signal["top_sectors"]
    cands = signal["candidates"]
    risk = signal["risk_control"]
    friendly = signal.get("no_recommendation_message", "当前暂无推荐标的，建议观望。")

    report = (
        "【A股短线日报】\n\n"
        f"分析日期：{signal.get('analysis_date', m.get('date', ''))}\n"
        f"市场情绪：score={m.get('market_sentiment_score', 0)} "
        f"(涨停{m.get('limit_up', 0)} 跌停{m.get('limit_down', 0)} 炸板率{m.get('break_rate', 0)})\n"
        f"最高连板：{m.get('max_height', 0)}\n\n"
        f"强势板块：\n{_fmt_sectors(sectors)}\n\n"
        f"短线关注：\n{_fmt_candidates(cands)}\n\n"
        f"结论：\n{friendly}\n\n"
        "建议：\n"
        f"轻仓试错(<= {int(risk.get('max_position', 0) * 100)}%)\n"
        f"止损 {risk.get('stop_loss', -6)}%\n"
        f"止盈 {risk.get('take_profit', 12)}%\n\n"
        "风险：\n"
        f"{risk.get('risk_note', '')}"
    )

    return {
        "report": report,
        "signal": signal,
    }
