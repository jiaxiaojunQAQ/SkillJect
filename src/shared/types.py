"""
Shared Type Definitions Module

Provides common type definitions for cross-module use
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


# Attack type enum - 4 core attack payloads
class AttackType(str, Enum):
    """Attack type"""

    INFORMATION_DISCLOSURE = "information_disclosure"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    UNAUTHORIZED_WRITE = "unauthorized_write"
    BACKDOOR_INJECTION = "backdoor_injection"
    DIRECT = "direct"  # For direct_execution strategy
    BASELINE = "baseline"  # For baseline strategy (no attack)
    SCRIPT_MAPPING = "script_mapping"  # For mapping-mode skillject (one script per skill)

    @classmethod
    def core_types(cls) -> list["AttackType"]:
        """Return the 4 core attack payload types (excluding DIRECT and SCRIPT_MAPPING sentinels)"""
        return [t for t in cls if t not in (cls.DIRECT, cls.BASELINE, cls.SCRIPT_MAPPING)]


# Injection layer enum
class InjectionLayer(str, Enum):
    """Injection layer"""

    DESCRIPTION = "description"
    INSTRUCTION = "instruction"
    RESOURCE = "resource"
    DESCRIPTION_RESOURCE = "description_resource"
    INSTRUCTION_RESOURCE = "instruction_resource"
    ALL = "all"


# Severity level enum
class Severity(str, Enum):
    """Severity level"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Agent type enum
class AgentType(str, Enum):
    """Agent type"""

    CLAUDE_CODE = "claude-code"
    OPENCLAW = "openclaw"


# Test status enum
class TestStatus(str, Enum):
    """Test status"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    ERROR = "error"
    SKIPPED = "skipped"
    CLASSIFICATION_FAILED = "classification_failed"


# Index entry type
class SkillIndexEntry(dict):
    """Skill index entry"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'"
            ) from exc

    def __setattr__(self, key, value):
        self[key] = value


class TestIndexEntry(dict):
    """Test index entry"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'"
            ) from exc

    def __setattr__(self, key, value):
        self[key] = value


# Value objects
@dataclass(frozen=True)
class SkillMetadata:
    """Skill metadata value object"""

    name: str
    path: Path
    has_instruction: bool = False
    has_resources: bool = False
    size_bytes: int | None = None
    last_modified: datetime | None = None


@dataclass(frozen=True)
class TestMetadata:
    """Test metadata value object"""

    test_id: str
    skill_name: str
    layer: InjectionLayer
    attack_type: AttackType
    payload_name: str
    severity: Severity
    should_be_blocked: bool = True
    injection_points: list[str] | None = None

    def __post_init__(self):
        if self.injection_points is None:
            object.__setattr__(self, "injection_points", [])


@dataclass
class TestResult:
    """Test result entity"""

    test_id: str
    status: TestStatus
    detected_consequences: list[str] | None = None
    execution_time_seconds: float | None = None

    def __post_init__(self):
        if self.detected_consequences is None:
            self.detected_consequences = []

    def is_blocked(self) -> bool:
        return self.status == TestStatus.BLOCKED

    def is_passed(self) -> bool:
        return self.status in (TestStatus.PASSED, TestStatus.BLOCKED)


__all__ = [
    "AttackType",
    "InjectionLayer",
    "Severity",
    "AgentType",
    "TestStatus",
    "SkillIndexEntry",
    "TestIndexEntry",
    "SkillMetadata",
    "TestMetadata",
    "TestResult",
]
# mypy: disable-error-code="no-untyped-def"
