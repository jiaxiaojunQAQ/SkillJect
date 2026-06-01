"""Debug helpers for conditional verbose diagnostics."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def resolve_debug(debug: bool = False) -> bool:
    if debug:
        return True
    raw = os.getenv("SHORT_DECISION_DEBUG", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def with_debug(payload: dict[str, Any], debug: bool, debug_info: dict[str, Any]) -> dict[str, Any]:
    if not debug:
        return payload
    enriched = dict(payload)
    enriched["debug_info"] = debug_info
    return enriched


def is_fallback_enabled(default: bool = False) -> bool:
    """
    Resolve fallback behavior.

    Priority:
    1) env SHORT_DECISION_FALLBACK_ENABLED
    2) config.json data_source.fallback_enabled
    3) default
    """
    raw = os.getenv("SHORT_DECISION_FALLBACK_ENABLED", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False

    try:
        cfg_path = Path(__file__).resolve().parents[1] / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return bool(cfg.get("data_source", {}).get("fallback_enabled", default))
    except Exception:
        return default
