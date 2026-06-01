"""
Injection Strategy Value Object

The generation pipeline now uses one fixed injection strategy.  The value object
is kept only for existing LLM request metadata and provider interfaces.
"""

from dataclasses import dataclass
from enum import Enum


class InjectionStrategyType(Enum):
    """Supported injection strategy type."""

    COMPREHENSIVE = "comprehensive"


@dataclass(frozen=True)
class InjectionStrategy:
    """Fixed injection strategy marker."""

    strategy_type: InjectionStrategyType = InjectionStrategyType.COMPREHENSIVE
