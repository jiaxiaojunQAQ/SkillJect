"""Market data access and stock scanning tools for short-term strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
import re
from typing import Any, Dict

from .debug_utils import is_fallback_enabled, resolve_debug, with_debug
from .indicators import clamp, trend_up, volume_ratio
from .settings import get_screener_config

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover
    ak = None  # type: ignore

TEST_STOCK_NAMES = {"DemoTech", "ChipStar", "RoboCore"}


@dataclass
class StockCandidate:
    code: str
    name: str
    change_pct: float
    volume_ratio: float
    strength_rank: int
    sector: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "change_pct": round(self.change_pct, 2),
            "volume_ratio": round(self.volume_ratio, 2),
            "strength_rank": self.strength_rank,
            "sector": self.sector,
        }


def _to_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None or pd is None:
        return []
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    return frame.to_dict(orient="records")


def _num(row: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            try:
                return float(row[key])
            except Exception:
                continue
    return default


def _str(row: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
    return default


def _normalize_number(value: Any) -> float:
    if value in ("", None):
        return 0.0
    if isinstance(value, (int, float)):
        out = float(value)
        return out if math.isfinite(out) else 0.0
    text = str(value).strip().replace(",", "")
    if text in ("-", "--"):
        return 0.0

    unit = 1.0
    if text.endswith("亿"):
        unit = 100_000_000.0
        text = text[:-1]
    elif text.endswith("万"):
        unit = 10_000.0
        text = text[:-1]

    try:
        out = float(text) * unit
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def _num_unit(row: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    for key in keys:
        if key in row:
            parsed = _normalize_number(row[key])
            if parsed != 0.0 or row[key] in (0, "0", "0.0"):
                return parsed
    return default


def _parse_board_height(raw: Any) -> int:
    if raw in ("", None):
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip()
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _parse_analysis_date(analysis_date: str | None) -> tuple[str, date]:
    if not analysis_date:
        d = datetime.now().date()
        return d.strftime("%Y%m%d"), d
    cleaned = analysis_date.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            d = datetime.strptime(cleaned, fmt).date()
            return d.strftime("%Y%m%d"), d
        except ValueError:
            pass
    d = datetime.now().date()
    return d.strftime("%Y%m%d"), d


def _recent_trade_dates(anchor: date | None = None, days: int = 10) -> list[str]:
    base = anchor or datetime.now().date()
    dates: list[str] = []
    for offset in range(days):
        d = base - timedelta(days=offset)
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
    return dates


def _fallback_market_sentiment(debug: bool = False, debug_info: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "limit_up": 0,
        "limit_down": 0,
        "max_height": 0,
        "break_rate": 0.0,
        "turnover": 0,
        "market_sentiment_score": 0.0,
        "data_source": "fallback",
        "error": "real_data_required",
    }
    return with_debug(payload, debug, debug_info or {"reason": "fallback_empty_market_sentiment"})


def get_market_sentiment(analysis_date: str | None = None, debug: bool = False) -> dict[str, Any]:
    debug = resolve_debug(debug)
    screener_cfg = get_screener_config()
    fallback_ok = is_fallback_enabled(default=False)
    target_ymd, target_date = _parse_analysis_date(analysis_date)

    dbg: dict[str, Any] = {
        "module": "get_market_sentiment",
        "analysis_date": target_ymd,
        "akshare_available": ak is not None,
        "pandas_available": pd is not None,
        "fallback_enabled": fallback_ok,
    }
    if ak is None or pd is None:
        dbg["fallback_reason"] = "akshare_or_pandas_missing"
        return _fallback_market_sentiment(debug=debug, debug_info=dbg) if fallback_ok else with_debug(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "limit_up": 0,
                "limit_down": 0,
                "max_height": 0,
                "break_rate": 0.0,
                "turnover": 0,
                "market_sentiment_score": 0.0,
                "data_source": "unavailable",
                "error": "real_data_required",
            },
            debug,
            dbg,
        )

    chosen_date = ""
    zt_records: list[dict[str, Any]] = []
    dt_records: list[dict[str, Any]] = []
    zb_records: list[dict[str, Any]] = []

    date_candidates = [target_ymd] if analysis_date else _recent_trade_dates(anchor=target_date)
    dbg["date_candidates"] = date_candidates
    dbg["api_calls"] = []

    for date_text in date_candidates:
        try:
            zt_df = ak.stock_zt_pool_em(date=date_text)
            records = _to_records(zt_df)
            dbg["api_calls"].append({"api": "stock_zt_pool_em", "date": date_text, "ok": True, "rows": len(records)})
            if records:
                chosen_date = date_text
                zt_records = records
                break
        except Exception:
            dbg["api_calls"].append({"api": "stock_zt_pool_em", "date": date_text, "ok": False})

    if not zt_records:
        dbg["fallback_reason"] = "empty_limit_up_pool"
        return _fallback_market_sentiment(debug=debug, debug_info=dbg) if fallback_ok else with_debug(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "limit_up": 0,
                "limit_down": 0,
                "max_height": 0,
                "break_rate": 0.0,
                "turnover": 0,
                "market_sentiment_score": 0.0,
                "data_source": "unavailable",
                "error": "real_data_required",
            },
            debug,
            dbg,
        )

    try:
        dt_records = _to_records(ak.stock_zt_pool_dtgc_em(date=chosen_date))
        dbg["api_calls"].append({"api": "stock_zt_pool_dtgc_em", "date": chosen_date, "ok": True, "rows": len(dt_records)})
    except Exception:
        dbg["api_calls"].append({"api": "stock_zt_pool_dtgc_em", "date": chosen_date, "ok": False})

    try:
        if hasattr(ak, "stock_zt_pool_zbgc_em"):
            zb_records = _to_records(ak.stock_zt_pool_zbgc_em(date=chosen_date))
            dbg["api_calls"].append({"api": "stock_zt_pool_zbgc_em", "date": chosen_date, "ok": True, "rows": len(zb_records)})
    except Exception:
        dbg["api_calls"].append({"api": "stock_zt_pool_zbgc_em", "date": chosen_date, "ok": False})

    limit_up = len(zt_records)
    limit_down = len(dt_records)
    max_height = 0
    for row in zt_records:
        max_height = max(max_height, _parse_board_height(_str(row, ["连板数", "连板", "连板高度", "几天几板"], "1")))

    break_count = len(zb_records)
    if break_count == 0:
        for row in zt_records:
            state = _str(row, ["状态", "涨停状态", "封板状态"], "")
            if state and state not in ("封板", "涨停"):
                break_count += 1

    total_lu_events = limit_up + break_count
    break_rate = break_count / total_lu_events if total_lu_events else 0.0

    turnover = 0.0
    try:
        spot_records = _to_records(ak.stock_zh_a_spot_em())
        dbg["api_calls"].append({"api": "stock_zh_a_spot_em", "ok": True, "rows": len(spot_records)})
        for row in spot_records:
            turnover += _num_unit(row, ["成交额", "成交额(元)", "amount"], 0.0)
    except Exception:
        dbg["api_calls"].append({"api": "stock_zh_a_spot_em", "ok": False})

    score = (
        clamp(limit_up / 70 * 45, 0, 45)
        + clamp((12 - limit_down) / 12 * 20, 0, 20)
        + clamp(max_height / 6 * 20, 0, 20)
        + clamp((0.35 - break_rate) / 0.35 * 15, 0, 15)
    )

    payload = {
        "date": f"{chosen_date[:4]}-{chosen_date[4:6]}-{chosen_date[6:8]}",
        "analysis_date": target_date.strftime("%Y-%m-%d"),
        "limit_up": limit_up,
        "limit_down": limit_down,
        "max_height": max_height,
        "break_rate": round(break_rate, 4),
        "turnover": int(turnover),
        "market_sentiment_score": round(score, 2),
        "data_source": "akshare-live",
    }
    dbg["derived"] = {"break_count": break_count, "total_lu_events": total_lu_events}
    return with_debug(payload, debug, dbg)


def _fallback_sector_rotation(debug: bool = False, debug_info: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "top_sectors": [],
        "data_source": "fallback",
        "error": "real_data_required",
    }
    return with_debug(payload, debug, debug_info or {"reason": "fallback_empty_sector_rotation"})


def get_sector_rotation(top_n: int = 5, analysis_date: str | None = None, debug: bool = False) -> dict[str, Any]:
    debug = resolve_debug(debug)
    screener_cfg = get_screener_config()
    fallback_ok = is_fallback_enabled(default=False)
    target_ymd, target_date = _parse_analysis_date(analysis_date)

    dbg: dict[str, Any] = {"module": "get_sector_rotation", "analysis_date": target_ymd, "api_calls": [], "fallback_enabled": fallback_ok}
    if ak is None or pd is None:
        dbg["fallback_reason"] = "akshare_or_pandas_missing"
        return _fallback_sector_rotation(debug=debug, debug_info=dbg) if fallback_ok else with_debug(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "top_sectors": [],
                "data_source": "unavailable",
                "error": "real_data_required",
            },
            debug,
            dbg,
        )

    # AkShare board endpoints are snapshot-style, no stable historical-by-date endpoint.
    if analysis_date and target_date != datetime.now().date():
        dbg["fallback_reason"] = "historical_sector_snapshot_unavailable"
        return with_debug(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "top_sectors": [],
                "data_source": "unavailable",
                "error": "historical_sector_data_unavailable",
            },
            debug,
            dbg,
        )

    sector_rows: list[dict[str, Any]] = []
    
    # 优先使用新浪板块数据（更稳定）
    if hasattr(ak, "stock_sector_spot"):
        try:
            sector_rows = _to_records(ak.stock_sector_spot())
            dbg["api_calls"].append({"api": "stock_sector_spot", "ok": True, "rows": len(sector_rows)})
        except Exception:
            dbg["api_calls"].append({"api": "stock_sector_spot", "ok": False})

    # 备用：东方财富
    if not sector_rows:
        try:
            sector_rows = _to_records(ak.stock_board_industry_name_em())
            dbg["api_calls"].append({"api": "stock_board_industry_name_em", "ok": True, "rows": len(sector_rows)})
        except Exception:
            dbg["api_calls"].append({"api": "stock_board_industry_name_em", "ok": False})

    if not sector_rows and hasattr(ak, "stock_board_concept_name_em"):
        try:
            sector_rows = _to_records(ak.stock_board_concept_name_em())
            dbg["api_calls"].append({"api": "stock_board_concept_name_em", "ok": True, "rows": len(sector_rows)})
        except Exception:
            dbg["api_calls"].append({"api": "stock_board_concept_name_em", "ok": False})

    # 备用：同花顺 API
    if not sector_rows and hasattr(ak, "stock_board_industry_name_ths"):
        try:
            sector_rows = _to_records(ak.stock_board_industry_name_ths())
            dbg["api_calls"].append({"api": "stock_board_industry_name_ths", "ok": True, "rows": len(sector_rows)})
        except Exception:
            dbg["api_calls"].append({"api": "stock_board_industry_name_ths", "ok": False})

    if not sector_rows and hasattr(ak, "stock_board_concept_name_ths"):
        try:
            sector_rows = _to_records(ak.stock_board_concept_name_ths())
            dbg["api_calls"].append({"api": "stock_board_concept_name_ths", "ok": True, "rows": len(sector_rows)})
        except Exception:
            dbg["api_calls"].append({"api": "stock_board_concept_name_ths", "ok": False})

    if not sector_rows:
        dbg["fallback_reason"] = "no_sector_rows"
        return _fallback_sector_rotation(debug=debug, debug_info=dbg) if fallback_ok else with_debug(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "top_sectors": [],
                "data_source": "unavailable",
                "error": "real_data_required",
            },
            debug,
            dbg,
        )

    sectors: list[dict[str, Any]] = []
    max_turnover = max(_num_unit(row, ["成交额", "总成交额", "总市值", "总成交额"], 0.0) for row in sector_rows) or 1.0

    for row in sector_rows:
        name = _str(row, ["板块名称", "名称", "板块"], "UNKNOWN")
        change_pct = _num(row, ["涨跌幅", "涨跌幅%"], 0.0)
        turnover = _num_unit(row, ["成交额", "总成交额", "总市值", "总成交额"], 0.0)
        up_count = int(_num(row, ["上涨家数", "公司家数"], 0.0))
        limit_up_count = int(_num(row, ["涨停家数"], 0.0))
        if limit_up_count == 0 and up_count > 0:
            limit_up_count = int(up_count * 0.08)

        strength = (
            clamp(change_pct / 7 * 45, 0, 45)
            + clamp(turnover / max_turnover * 25, 0, 25)
            + clamp(limit_up_count / 12 * 30, 0, 30)
        )

        sectors.append(
            {
                "name": name,
                "change_pct": round(change_pct, 2),
                "turnover": int(turnover),
                "limit_up_count": limit_up_count,
                "board_code": _str(row, ["板块代码", "代码", "label"], ""),
                "strength": round(strength, 2),
            }
        )

    sectors.sort(key=lambda x: x["strength"], reverse=True)
    payload = {
        "date": target_date.strftime("%Y-%m-%d"),
        "top_sectors": sectors[:top_n],
        "data_source": "akshare-live",
    }
    dbg["derived"] = {"input_rows": len(sector_rows), "returned_rows": min(top_n, len(sectors))}
    return with_debug(payload, debug, dbg)


def _fallback_scan_strong_stocks(
    sectors: list[str] | None = None, top_n: int = 10, debug: bool = False, debug_info: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    return []


def _scan_from_hist_candidates(
    rows: list[dict[str, Any]],
    analysis_ymd: str,
    sectors: list[str] | None,
    top_n: int,
    debug_info: dict[str, Any],
    screener_cfg: dict[str, Any],
    historical_mode: bool = False,
) -> list[dict[str, Any]]:
    candidates: list[StockCandidate] = []
    for row in rows:
        code = _str(row, ["代码", "股票代码"], "")
        if not code:
            continue
        name = _str(row, ["名称", "股票名称"], "")
        if name in TEST_STOCK_NAMES:
            continue
        sector = _str(row, ["所属行业", "行业", "所属板块"], "UNKNOWN")
        if sectors and sector not in sectors:
            continue

        try:
            start_date = (datetime.strptime(analysis_ymd, "%Y%m%d").date() - timedelta(days=45)).strftime("%Y%m%d")
            hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=analysis_ymd, adjust="qfq")
            records = _to_records(hist)
            debug_info.setdefault("api_calls", []).append({"api": "stock_zh_a_hist", "symbol": code, "ok": True, "rows": len(records)})
        except Exception:
            debug_info.setdefault("api_calls", []).append({"api": "stock_zh_a_hist", "symbol": code, "ok": False})
            continue

        if len(records) < int(screener_cfg.get("min_history_days", 6)):
            continue

        closes = [_num(x, ["收盘"], 0.0) for x in records]
        opens = [_num(x, ["开盘"], 0.0) for x in records]
        volumes = [_num(x, ["成交量"], 0.0) for x in records]
        change_pct = _num(records[-1], ["涨跌幅"], 0.0)

        min_change = float(screener_cfg.get("min_change_pct", 5.0))
        if historical_mode:
            min_change = float(screener_cfg.get("historical_mode", {}).get("min_change_pct", min_change))
        if change_pct <= min_change:
            continue
        trend_lb = int(screener_cfg.get("trend_lookback", 3))
        if historical_mode:
            trend_lb = int(screener_cfg.get("historical_mode", {}).get("trend_lookback", trend_lb))
        if not trend_up(closes, lookback=trend_lb):
            continue

        base_days = int(screener_cfg.get("volume_baseline_days", 5))
        baseline = sum(volumes[-(base_days + 1):-1]) / max(len(volumes[-(base_days + 1):-1]), 1)
        vol_ratio = volume_ratio(volumes[-1], baseline)
        min_vr = float(screener_cfg.get("min_volume_ratio", 1.5))
        if historical_mode:
            min_vr = float(screener_cfg.get("historical_mode", {}).get("min_volume_ratio", min_vr))
        if vol_ratio <= min_vr:
            continue

        prev_close = closes[-2] if len(closes) > 1 else 0.0
        last_day_change = ((closes[-1] - prev_close) / prev_close * 100) if prev_close else 0.0
        drop_th = float(screener_cfg.get("high_volume_bearish_drop_pct", -2.0))
        vol_th = float(screener_cfg.get("high_volume_bearish_vol_ratio", 2.2))
        if historical_mode:
            drop_th = float(screener_cfg.get("historical_mode", {}).get("high_volume_bearish_drop_pct", drop_th))
            vol_th = float(screener_cfg.get("historical_mode", {}).get("high_volume_bearish_vol_ratio", vol_th))
        high_volume_bearish = opens[-1] > closes[-1] and last_day_change < drop_th and vol_ratio > vol_th
        if high_volume_bearish:
            continue

        candidates.append(
            StockCandidate(
                code=code,
                name=name,
                change_pct=change_pct,
                volume_ratio=vol_ratio,
                strength_rank=0,
                sector=sector,
            )
        )

    candidates.sort(key=lambda x: (x.change_pct, x.volume_ratio), reverse=True)
    ranked: list[dict[str, Any]] = []
    rank_counter = 1
    for item in candidates:
        if item.name in TEST_STOCK_NAMES:
            continue
        item.strength_rank = rank_counter
        ranked.append(item.to_dict())
        rank_counter += 1
        if len(ranked) >= top_n:
            break
    return ranked


def scan_strong_stocks(
    sectors: list[str] | None = None,
    top_n: int = 10,
    analysis_date: str | None = None,
    debug: bool = False,
) -> list[dict[str, Any]]:
    debug = resolve_debug(debug)
    screener_cfg = get_screener_config()
    fallback_ok = is_fallback_enabled(default=False)
    analysis_ymd, analysis_day = _parse_analysis_date(analysis_date)
    dbg: dict[str, Any] = {
        "module": "scan_strong_stocks",
        "analysis_date": analysis_ymd,
        "api_calls": [],
        "sectors_filter": sectors or [],
        "fallback_enabled": fallback_ok,
    }

    if ak is None or pd is None:
        dbg["fallback_reason"] = "akshare_or_pandas_missing"
        return _fallback_scan_strong_stocks(sectors, top_n, debug=debug, debug_info=dbg) if fallback_ok else []

    # Historical-date mode: use that date's limit-up pool as universe, then verify with historical bars.
    if analysis_date and analysis_day != datetime.now().date():
        try:
            zt_rows = _to_records(ak.stock_zt_pool_em(date=analysis_ymd))
            dbg["api_calls"].append({"api": "stock_zt_pool_em", "date": analysis_ymd, "ok": True, "rows": len(zt_rows)})
        except Exception:
            zt_rows = []
            dbg["api_calls"].append({"api": "stock_zt_pool_em", "date": analysis_ymd, "ok": False})

        if not zt_rows:
            return []

        ranked = _scan_from_hist_candidates(zt_rows, analysis_ymd, sectors=sectors, top_n=top_n, debug_info=dbg, screener_cfg=screener_cfg, historical_mode=True)
        if debug:
            dbg["derived"] = {"historical_mode": True, "universe": len(zt_rows), "candidates": len(ranked)}
            return [dict(item, debug_info=dbg) for item in ranked]
        return ranked

    # Realtime mode
    try:
        spot_df = ak.stock_zh_a_spot_em()
        dbg["api_calls"].append({"api": "stock_zh_a_spot_em", "ok": True})
    except Exception:
        dbg["api_calls"].append({"api": "stock_zh_a_spot_em", "ok": False})
        dbg["fallback_reason"] = "spot_api_failed"
        return _fallback_scan_strong_stocks(sectors, top_n, debug=debug, debug_info=dbg) if fallback_ok else []

    rows = _to_records(spot_df)
    if not rows:
        dbg["fallback_reason"] = "spot_rows_empty"
        return _fallback_scan_strong_stocks(sectors, top_n, debug=debug, debug_info=dbg) if fallback_ok else []

    pre_filtered = []
    for row in rows:
        code = _str(row, ["代码", "股票代码"], "")
        name = _str(row, ["名称", "股票名称"], "")
        change_pct = _num(row, ["涨跌幅"], 0.0)
        if name in TEST_STOCK_NAMES:
            continue
        if change_pct > float(screener_cfg.get("prefilter_change_pct", 4.5)) and code:
            pre_filtered.append(row)

    pre_filtered.sort(key=lambda x: _num(x, ["涨跌幅"], 0.0), reverse=True)
    universe = pre_filtered[:120]
    ranked = _scan_from_hist_candidates(universe, analysis_ymd, sectors=sectors, top_n=top_n, debug_info=dbg, screener_cfg=screener_cfg, historical_mode=False)

    if not debug:
        return ranked
    dbg["derived"] = {
        "historical_mode": False,
        "spot_rows": len(rows),
        "pre_filtered": len(pre_filtered),
        "universe": len(universe),
        "candidates": len(ranked),
    }
    return [dict(item, debug_info=dbg) for item in ranked]
