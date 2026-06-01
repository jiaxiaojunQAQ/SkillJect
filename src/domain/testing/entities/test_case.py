"""
Test Case Entity

Core domain entity representing a single security test case.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.shared.types import (
    AttackType,
    InjectionLayer,
    Severity,
    TestStatus,
)


class ErrorType(Enum):
    """Test error type classification"""

    # Infrastructure errors (should not count as security test failures)
    EXECD_CRASH = "execd_crash"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    CONTAINER_ERROR = "container_error"
    SANDBOX_NOT_AVAILABLE = "sandbox_not_available"
    AGENT_API_ERROR = "agent_api_error"

    # Security test related
    BLOCKED = "blocked"
    EXECUTED = "executed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TestCaseId:
    """Test case identifier (value object)

    Uses immutable type to ensure ID is not accidentally modified.
    """

    value: str

    def __post_init__(self):
        """Validate ID format"""
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Test ID cannot be empty")

    @classmethod
    def create(
        cls,
        skill_name: str,
        attack_type: AttackType,
    ) -> "TestCaseId":
        """Create test ID from components

        New format: {skill_name}_{attack_type}

        Args:
            skill_name: Skill name
            attack_type: Attack type

        Returns:
            TestCaseId instance
        """
        value = f"{skill_name}_{attack_type.value}"
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass
class TestCase:
    """Test case entity

    Represents a complete security test case containing all necessary information.
    """

    # Identification
    id: TestCaseId
    skill_name: str

    # Test configuration
    layer: InjectionLayer
    attack_type: AttackType
    payload_name: str
    severity: Severity

    # File paths
    skill_path: Path
    test_case_dir: Path
    source_skill_dir: Path | None = None  # Original skill directory (containing SKILL.md and related skill files)
    source_aux_dir: Path | None = None  # Optional auxiliary file directory for project injection
    dataset: str = "skills_from_skill0"  # Dataset membership, for dynamically building instruction path

    # Expected results
    should_be_blocked: bool = True

    # Additional information
    injected_resource_file: str = ""
    injection_points: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    payload_content: str = ""

    # Domain behaviors
    def is_multi_layer(self) -> bool:
        """Check if multi-layer injection"""
        return self.layer in (
            InjectionLayer.DESCRIPTION_RESOURCE,
            InjectionLayer.INSTRUCTION_RESOURCE,
            InjectionLayer.ALL,
        )

    def get_injection_layers(self) -> list[InjectionLayer]:
        """Get all injection layers"""
        if self.layer == InjectionLayer.ALL:
            return [
                InjectionLayer.DESCRIPTION,
                InjectionLayer.INSTRUCTION,
                InjectionLayer.RESOURCE,
            ]
        elif self.layer == InjectionLayer.DESCRIPTION_RESOURCE:
            return [InjectionLayer.DESCRIPTION, InjectionLayer.RESOURCE]
        elif self.layer == InjectionLayer.INSTRUCTION_RESOURCE:
            return [InjectionLayer.INSTRUCTION, InjectionLayer.RESOURCE]
        else:
            return [self.layer]

    def is_critical_severity(self) -> bool:
        """Check if critical severity"""
        return self.severity in (Severity.HIGH, Severity.CRITICAL)

    def validate(self) -> list[str]:
        """Validate test case

        Returns:
            Error list (empty list means valid)
        """
        errors = []

        if not self.skill_path.exists():
            errors.append(f"Skill file does not exist: {self.skill_path}")

        if not self.test_case_dir.exists():
            errors.append(f"Test directory does not exist: {self.test_case_dir}")

        return errors


@dataclass
class WorkspaceCopyStatus:
    """Tracks outcome of workspace copy operations from container."""

    skill_copied: bool = False
    project_copied: bool = False
    skill_copy_error: str = ""
    project_copy_error: str = ""


@dataclass
class TestResult:
    """Test result entity

    Records execution result of a single test.
    """

    # Associated test case
    test_id: TestCaseId

    # Execution status
    status: TestStatus = TestStatus.PENDING

    # Execution information
    agent_output: str = ""
    execution_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    # Analysis results
    blocked: bool = False
    detected_threat: bool = False
    executed_malicious: bool = False
    detected_consequences: list[str] = field(default_factory=list)

    # Diagnostic information
    error_type: ErrorType = ErrorType.UNKNOWN
    is_infrastructure_error: bool = False
    error_message: str = ""
    reasoning: str = ""

    # Retry tracking
    retry_count: int = 0  # Current retry count
    total_attempts: int = 1  # Total attempts (including first execution)

    # Additional data
    metadata: dict[str, Any] = field(default_factory=dict)
    # Runtime-only raw log payload used when persisting raw_logs.txt
    raw_log_source: str = ""
    raw_log_lines: list[str] = field(default_factory=list)

    # Domain behaviors
    def is_passed(self) -> bool:
        """Check if test passed (no malicious behavior)"""
        # Infrastructure errors don't count as pass/fail
        if self.is_infrastructure_error:
            return False

        # Simplified logic: only check for malicious behavior
        # executed_malicious=False means no harmful behavior = defense successful = PASSED
        return not self.executed_malicious

    def is_failed(self) -> bool:
        """Check if test failed (attack successful)"""
        # Simplified logic: executed_malicious=True means harmful behavior = attack successful = FAILED
        return self.executed_malicious and not self.is_infrastructure_error

    def is_attack_successful(self) -> bool:
        """Check if attack was successful (malicious behavior executed)"""
        return self.executed_malicious

    def is_blocked(self) -> bool:
        """Check if attack was blocked"""
        return self.blocked

    def has_consequences(self) -> bool:
        """Check if there are detectable consequences"""
        return len(self.detected_consequences) > 0

    def mark_infrastructure_error(self, error_type: ErrorType, message: str) -> None:
        """Mark as infrastructure error"""
        self.error_type = error_type
        self.is_infrastructure_error = True
        self.error_message = message
        self.status = TestStatus.ERROR

    def mark_blocked(self, reasoning: str = "") -> None:
        """Mark as blocked (no malicious behavior)"""
        self.blocked = True
        self.executed_malicious = False  # Ensure correct setting: blocked = no malicious behavior
        self.detected_threat = True
        self.status = TestStatus.BLOCKED
        self.reasoning = reasoning

    def mark_executed(self, reasoning: str = "") -> None:
        """Mark as executed"""
        self.blocked = False
        self.executed_malicious = True
        self.status = TestStatus.FAILED
        self.reasoning = reasoning

    def mark_passed(self, reasoning: str = "") -> None:
        """Mark as passed (no malicious behavior)"""
        self.blocked = True
        self.executed_malicious = False  # Ensure correct setting: passed = no malicious behavior
        self.detected_threat = True
        self.status = TestStatus.PASSED
        self.reasoning = reasoning

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON serialization)

        Returns:
            Dictionary containing all test result fields
        """
        return {
            "test_id": self.test_id.value,
            "status": self.status.value,
            "agent_output": self.agent_output,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp.isoformat(),
            "blocked": self.blocked,
            "detected_threat": self.detected_threat,
            "executed_malicious": self.executed_malicious,
            "detected_consequences": self.detected_consequences,
            "error_type": self.error_type.value,
            "is_infrastructure_error": self.is_infrastructure_error,
            "error_message": self.error_message,
            "reasoning": self.reasoning,
            "retry_count": self.retry_count,
            "total_attempts": self.total_attempts,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class TestStatistics:
    """Test statistics (value object)

    Immutable test statistics class for type-safe statistical information passing.
    """

    completed: int
    passed: int
    failed: int
    blocked: int
    error: int
    infra_errors: int

    # Retry statistics
    retried_tests: int = 0  # Number of tests that were retried
    total_retry_attempts: int = 0  # Total retry attempts

    def __iter__(self):
        """Support dictionary unpacking"""
        return iter(
            [
                ("completed", self.completed),
                ("passed", self.passed),
                ("failed", self.failed),
                ("blocked", self.blocked),
                ("error", self.error),
                ("infra_errors", self.infra_errors),
                ("retried_tests", self.retried_tests),
                ("total_retry_attempts", self.total_retry_attempts),
            ]
        )

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary"""
        return {
            "completed": self.completed,
            "passed": self.passed,
            "failed": self.failed,
            "blocked": self.blocked,
            "error": self.error,
            "infra_errors": self.infra_errors,
            "retried_tests": self.retried_tests,
            "total_retry_attempts": self.total_retry_attempts,
        }


@dataclass
class TestSuite:
    """Test suite entity

    Represents a group of related test cases.
    """

    name: str
    test_cases: list[TestCase] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    # Domain behaviors
    def add_test_case(self, test_case: TestCase) -> None:
        """Add test case"""
        self.test_cases.append(test_case)

    def remove_test_case(self, test_id: TestCaseId) -> bool:
        """Remove test case

        Returns:
            Whether successfully removed
        """
        for i, tc in enumerate(self.test_cases):
            if tc.id == test_id:
                self.test_cases.pop(i)
                return True
        return False

    def get_test_case(self, test_id: TestCaseId) -> TestCase | None:
        """Get test case"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        return None

    def filter_by_attack_type(self, attack_type: AttackType) -> "TestSuite":
        """Filter by attack type

        Returns:
            New test suite
        """
        filtered = [tc for tc in self.test_cases if tc.attack_type == attack_type]
        return TestSuite(
            name=f"{self.name}_{attack_type.value}",
            test_cases=filtered,
            description=f"Filtered from {self.name}",
        )

    def filter_by_severity(self, severity: Severity) -> "TestSuite":
        """Filter by severity

        Returns:
            New test suite
        """
        filtered = [tc for tc in self.test_cases if tc.severity == severity]
        return TestSuite(
            name=f"{self.name}_{severity.value}",
            test_cases=filtered,
            description=f"Filtered from {self.name}",
        )

    def filter_by_layer(self, layer: InjectionLayer) -> "TestSuite":
        """Filter by injection layer

        Returns:
            New test suite
        """
        filtered = [tc for tc in self.test_cases if tc.layer == layer]
        return TestSuite(
            name=f"{self.name}_{layer.value}",
            test_cases=filtered,
            description=f"Filtered from {self.name}",
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics"""
        by_attack: dict[AttackType, int] = dict.fromkeys(AttackType, 0)
        by_severity: dict[Severity, int] = dict.fromkeys(Severity, 0)
        by_layer: dict[InjectionLayer, int] = dict.fromkeys(InjectionLayer, 0)

        for tc in self.test_cases:
            by_attack[tc.attack_type] += 1
            by_severity[tc.severity] += 1
            by_layer[tc.layer] += 1

        return {
            "total_tests": len(self.test_cases),
            "by_attack_type": {k.value: v for k, v in by_attack.items()},
            "by_severity": {k.value: v for k, v in by_severity.items()},
            "by_layer": {k.value: v for k, v in by_layer.items()},
        }

    def is_empty(self) -> bool:
        """Check if empty"""
        return len(self.test_cases) == 0

    def __len__(self) -> int:
        return len(self.test_cases)

    def __iter__(self):
        return iter(self.test_cases)

    def __contains__(self, test_id: TestCaseId | str) -> bool:
        """Check if test case exists"""
        test_id_str = test_id.value if isinstance(test_id, TestCaseId) else test_id
        return any(tc.id.value == test_id_str for tc in self.test_cases)
# mypy: disable-error-code="no-untyped-def"
