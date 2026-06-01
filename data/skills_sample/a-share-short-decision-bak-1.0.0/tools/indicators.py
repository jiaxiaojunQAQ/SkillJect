"""Reusable indicators for short-term A-share analysis."""

from __future__ import annotations

from typing import Iterable, List


def clamp(value: float, low: float, high: float) -> float:
    """Clamp value into [low, high]."""
    return max(low, min(high, value))


def safe_pct_change(current: float, previous: float) -> float:
    """Return percentage change. Return 0 when denominator is invalid."""
    if previous == 0:
        return 0.0
    return (current - previous) / abs(previous)


def volume_ratio(current_volume: float, baseline_volume: float) -> float:
    """Return current volume divided by baseline volume."""
    if baseline_volume <= 0:
        return 0.0
    return current_volume / baseline_volume


def moving_average(values: Iterable[float], window: int) -> float:
    """Calculate simple moving average on the latest window."""
    seq: List[float] = list(values)
    if not seq:
        return 0.0
    if window <= 0:
        return seq[-1]
    sliced = seq[-window:] if len(seq) >= window else seq
    return sum(sliced) / len(sliced)


def trend_up(values: Iterable[float], lookback: int = 3) -> bool:
    """Check whether latest lookback values are strictly improving."""
    seq: List[float] = list(values)
    if len(seq) < lookback:
        return False
    recent = seq[-lookback:]
    return all(recent[idx] > recent[idx - 1] for idx in range(1, len(recent)))


def score_bucket(value: float, bands: list[tuple[float, float]]) -> float:
    """
    Convert a raw value into score.

    bands format: [(threshold, score), ...], sorted by threshold descending.
    """
    for threshold, score in bands:
        if value >= threshold:
            return score
    return 0.0
