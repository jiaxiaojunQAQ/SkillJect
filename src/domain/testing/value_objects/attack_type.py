"""
Test Domain Value Objects

Defines value objects in the test domain for encapsulating concepts.
"""

from dataclasses import dataclass
from enum import Enum

from src.shared.types import AttackType, InjectionLayer, Severity


class InjectionPoint(Enum):
    """Injection point location"""

    DESCRIPTION_FRONTMATTER = "description_frontmatter"
    DESCRIPTION_END = "description_end"
    INSTRUCTION_START = "instruction_start"
    INSTRUCTION_END = "instruction_end"
    RESOURCE_FILE = "resource_file"


@dataclass(frozen=True)
class Payload:
    """Attack payload (value object)"""

    name: str
    content: str
    attack_type: AttackType
    severity: Severity

    def __str__(self) -> str:
        return f"{self.attack_type.value}/{self.name}"


@dataclass(frozen=True)
class InjectionConfig:
    """Injection configuration (value object)"""

    layer: InjectionLayer
    injection_points: list[InjectionPoint]
    payload: Payload
    prefix: str = ""
    suffix: str = ""

    def is_multi_layer(self) -> bool:
        """Check if multi-layer injection"""
        return self.layer in (
            InjectionLayer.DESCRIPTION_RESOURCE,
            InjectionLayer.INSTRUCTION_RESOURCE,
            InjectionLayer.ALL,
        )


@dataclass(frozen=True)
class TestExpectation:
    """Test expectation (value object)"""

    should_be_blocked: bool
    expected_consequences: list[str]
    min_detection_confidence: float = 0.5

    def is_strict(self) -> bool:
        """Check if strict test (must detect all expected consequences)"""
        return len(self.expected_consequences) > 0


@dataclass(frozen=True)
class TestTimeout:
    """Test timeout configuration (value object)"""

    command_timeout: int = 120
    setup_timeout: int = 30
    teardown_timeout: int = 30

    def total_timeout(self) -> int:
        """Get total timeout"""
        return self.command_timeout + self.setup_timeout + self.teardown_timeout

    def validate(self) -> list[str]:
        """Validate timeout configuration"""
        errors = []
        if self.command_timeout < 1:
            errors.append("command_timeout must be greater than 0")
        if self.setup_timeout < 0:
            errors.append("setup_timeout cannot be negative")
        if self.teardown_timeout < 0:
            errors.append("teardown_timeout cannot be negative")
        return errors
