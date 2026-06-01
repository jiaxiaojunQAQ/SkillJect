"""Value Objects Module

Exports value objects used by domain layer

Note: GenerationStrategy and TestGenerationConfig have been migrated to
src.domain.testing.value_objects.execution_config
"""

from .injection_strategy import (
    InjectionStrategy,
    InjectionStrategyType,
)

__all__ = [
    "InjectionStrategy",
    "InjectionStrategyType",
]
