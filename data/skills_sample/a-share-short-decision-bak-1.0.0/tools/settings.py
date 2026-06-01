"""Configuration loader for strategy thresholds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_SCREENER_CONFIG: Dict[str, Any] = {
    "prefilter_change_pct": 4.5,
    "min_change_pct": 5.0,
    "min_volume_ratio": 1.5,
    "trend_lookback": 3,
    "min_history_days": 6,
    "volume_baseline_days": 5,
    "high_volume_bearish_drop_pct": -2.0,
    "high_volume_bearish_vol_ratio": 2.2,
    "historical_mode": {
        "min_change_pct": 3.0,
        "trend_lookback": 2,
        "min_volume_ratio": 1.2,
        "high_volume_bearish_drop_pct": -3.0,
        "high_volume_bearish_vol_ratio": 2.8,
        "relaxed_pick_from_pool_when_empty": True,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> Dict[str, Any]:
    cfg_path = Path(__file__).resolve().parents[1] / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_screener_config() -> Dict[str, Any]:
    cfg = load_config()
    user_cfg = cfg.get("strategy", {}).get("screener", {})
    if not isinstance(user_cfg, dict):
        user_cfg = {}
    return _deep_merge(DEFAULT_SCREENER_CONFIG, user_cfg)
