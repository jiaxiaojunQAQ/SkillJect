"""Prediction logging and next-day comparison utilities."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover
    ak = None  # type: ignore

from .fusion_engine import short_term_signal_engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LOG_PATH = DATA_DIR / "decision_log.jsonl"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, item: dict[str, Any]) -> None:
    _ensure_data_dir()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def run_prediction_for_date(analysis_date: str, debug: bool = False) -> dict[str, Any]:
    signal = short_term_signal_engine(analysis_date=analysis_date, debug=debug)
    entry = {
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_date": signal.get("analysis_date", analysis_date),
        "signal": signal,
    }
    _append_jsonl(LOG_PATH, entry)
    return {
        "saved": True,
        "log_path": str(LOG_PATH),
        "analysis_date": entry["analysis_date"],
        "signal": signal,
    }


def _pick_entry(entries: list[dict[str, Any]], analysis_date: str) -> dict[str, Any] | None:
    for item in reversed(entries):
        if str(item.get("analysis_date", "")) == analysis_date:
            return item
    return None


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



def compare_prediction_with_market(
    prediction_date: str,
    actual_date: str | None = None,
    auto_generate_if_missing: bool = True,
    debug: bool = False,
) -> dict[str, Any]:
    entries = _load_entries(LOG_PATH)
    entry = _pick_entry(entries, prediction_date)

    if entry is None and auto_generate_if_missing:
        generated = run_prediction_for_date(prediction_date, debug=debug)
        entry = {
            "analysis_date": generated.get("analysis_date", prediction_date),
            "signal": generated.get("signal", {}),
            "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    if entry is None:
        return {
            "ok": False,
            "message": "未找到该日期预测记录，请先运行 run_prediction_for_date。",
            "prediction_date": prediction_date,
        }

    signal = entry.get("signal", {})
    candidates = signal.get("candidates", []) if isinstance(signal, dict) else []
    if not candidates:
        return {
            "ok": True,
            "prediction_date": prediction_date,
            "actual_date": actual_date or datetime.now().strftime("%Y-%m-%d"),
            "comparison": [],
            "summary": {
                "picked": 0,
                "hit_ratio": 0.0,
                "avg_return_pct": 0.0,
            },
            "message": "该日无可执行推荐标的，无法进行收益对比。",
            "signal": signal,
        }

    if ak is None or pd is None:
        return {
            "ok": False,
            "message": "akshare 或 pandas 不可用，无法做真实市场对比。",
            "prediction_date": prediction_date,
            "signal": signal,
        }

    pred_dt = datetime.strptime(prediction_date, "%Y-%m-%d")
    actual_dt = datetime.strptime(actual_date, "%Y-%m-%d") if actual_date else datetime.now()

    pred_ymd = pred_dt.strftime("%Y%m%d")
    actual_ymd = actual_dt.strftime("%Y%m%d")

    comparison: list[dict[str, Any]] = []
    for item in candidates:
        code = str(item.get("code", "")).strip()
        name = str(item.get("name", "")).strip()
        if not code:
            continue
        try:
            hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=pred_ymd, end_date=actual_ymd, adjust="qfq")
            rows = _to_records(hist)
        except Exception:
            rows = []

        if len(rows) < 2:
            comparison.append(
                {
                    "code": code,
                    "name": name,
                    "status": "no_data",
                    "return_pct": None,
                }
            )
            continue

        first = rows[0]
        last = rows[-1]
        buy_px = _num(first, ["收盘"], 0.0)
        sell_px = _num(last, ["收盘"], 0.0)
        ret = ((sell_px - buy_px) / buy_px * 100.0) if buy_px else 0.0

        comparison.append(
            {
                "code": code,
                "name": name,
                "buy_date": str(first.get("日期", prediction_date)),
                "buy_close": round(buy_px, 4),
                "eval_date": str(last.get("日期", actual_date or datetime.now().strftime("%Y-%m-%d"))),
                "eval_close": round(sell_px, 4),
                "return_pct": round(ret, 2),
                "hit": ret > 0,
            }
        )

    valid_returns = [x["return_pct"] for x in comparison if isinstance(x.get("return_pct"), (int, float))]
    hits = [x for x in comparison if x.get("hit") is True]

    avg_ret = sum(valid_returns) / len(valid_returns) if valid_returns else 0.0
    hit_ratio = len(hits) / len(valid_returns) if valid_returns else 0.0

    return {
        "ok": True,
        "prediction_date": prediction_date,
        "actual_date": actual_date or datetime.now().strftime("%Y-%m-%d"),
        "comparison": comparison,
        "summary": {
            "picked": len(candidates),
            "evaluated": len(valid_returns),
            "hit_ratio": round(hit_ratio, 4),
            "avg_return_pct": round(avg_ret, 4),
        },
        "signal": signal,
    }

