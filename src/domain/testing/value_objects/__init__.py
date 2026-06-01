"""
Test Domain Value Objects

Contains test-related value object definitions
"""

from .attack_type import AttackType
from .execution_config import (
    GenerationConfig,
    GenerationStrategy,
    GlobalConfig,
    LogLevel,
    Phase2ExecutionConfig,
    TwoPhaseExecutionConfig,
)
from .injection_layer import InjectionLayer
from .severity import Severity

__all__ = [
    # Existing value objects
    "AttackType",
    "InjectionLayer",
    "Severity",
    # New execution config value objects
    "GenerationConfig",
    "GenerationStrategy",
    "GlobalConfig",
    "LogLevel",
    "Phase2ExecutionConfig",
    "TwoPhaseExecutionConfig",
]
