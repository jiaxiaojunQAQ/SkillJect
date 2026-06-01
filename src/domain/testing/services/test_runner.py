"""
Test Runner Domain Service

Responsible for defining test execution interfaces and behaviors without concrete implementation.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.shared.types import TestStatus

from ..entities.test_case import TestCase, TestResult


class ExecutionStrategy(Enum):
    """Execution strategy"""

    SEQUENTIAL = "sequential"  # Sequential execution
    PARALLEL = "parallel"  # Parallel execution
    BATCH = "batch"  # Batch execution


@dataclass
class ExecutionConfig:
    """Execution configuration"""

    strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    max_concurrency: int = 4
    command_timeout: int = 120
    setup_timeout: int = 30
    teardown_timeout: int = 30
    retry_failed: bool = True
    max_retries: int = 2

    def validate(self) -> list[str]:
        """Validate configuration"""
        errors = []
        if self.max_concurrency < 1:
            errors.append("max_concurrency must be greater than 0")
        if self.command_timeout < 1:
            errors.append("command_timeout must be greater than 0")
        if self.max_retries < 0:
            errors.append("max_retries cannot be negative")
        return errors


@dataclass
class ExecutionContext:
    """Execution context"""

    sandbox_id: str = ""
    workdir: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_ready(self) -> bool:
        """Check if context is ready"""
        return bool(self.sandbox_id)


@dataclass
class ExecutionReport:
    """Execution report"""

    total_tests: int
    completed_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    error_tests: int
    infrastructure_errors: int
    execution_time_seconds: float
    results: list[TestResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Success rate"""
        if self.completed_tests == 0:
            return 0.0
        return self.passed_tests / self.completed_tests

    @property
    def block_rate(self) -> float:
        """Block rate"""
        if self.completed_tests == 0:
            return 0.0
        return self.blocked_tests / self.completed_tests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_tests": self.total_tests,
            "completed_tests": self.completed_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "blocked_tests": self.blocked_tests,
            "error_tests": self.error_tests,
            "infrastructure_errors": self.infrastructure_errors,
            "execution_time_seconds": self.execution_time_seconds,
            "success_rate": self.success_rate,
            "block_rate": self.block_rate,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class TestRunner(ABC):
    """Test runner abstract interface

    Defines standard test execution interface, concrete implementation provided by infrastructure layer.
    """

    @abstractmethod
    def run_test(
        self,
        test_case: TestCase,
        context: ExecutionContext,
    ) -> TestResult:
        """Run a single test

        Args:
            test_case: Test case
            context: Execution context

        Returns:
            Test result
        """
        pass

    @abstractmethod
    def run_tests(
        self,
        test_cases: list[TestCase],
        config: ExecutionConfig,
        progress_callback: Callable[[TestResult], None] | None = None,
    ) -> ExecutionReport:
        """Run multiple tests

        Args:
            test_cases: List of test cases
            config: Execution configuration
            progress_callback: Progress callback function

        Returns:
            Execution report
        """
        pass

    @abstractmethod
    def prepare_context(self, test_case: TestCase) -> ExecutionContext:
        """Prepare execution context

        Args:
            test_case: Test case

        Returns:
            Execution context
        """
        pass

    @abstractmethod
    def cleanup_context(self, context: ExecutionContext) -> None:
        """Clean up execution context

        Args:
            context: Execution context
        """
        pass


class TestRunnerOrchestrator:
    """Test runner orchestrator

    Coordinates test execution flow without concrete implementation.
    """

    def __init__(self, runner: TestRunner):
        self._runner = runner

    def execute_single_test(
        self,
        test_case: TestCase,
    ) -> TestResult:
        """Execute a single test

        Args:
            test_case: Test case

        Returns:
            Test result
        """
        # Validate test case
        validation_errors = test_case.validate()
        if validation_errors:
            return TestResult(
                test_id=test_case.id,
                status=TestStatus.ERROR,
                error_message=f"Test case validation failed: {validation_errors}",
            )

        # Prepare context
        context = self._runner.prepare_context(test_case)

        try:
            # Run test
            result = self._runner.run_test(test_case, context)
            return result
        finally:
            # Clean up context
            self._runner.cleanup_context(context)

    def execute_test_suite(
        self,
        test_cases: list[TestCase],
        config: ExecutionConfig,
        progress_callback: Callable[[TestResult], None] | None = None,
    ) -> ExecutionReport:
        """Execute test suite

        Args:
            test_cases: List of test cases
            config: Execution configuration
            progress_callback: Progress callback

        Returns:
            Execution report
        """
        import time

        start_time = time.time()

        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"Invalid execution configuration: {config_errors}")

        # Run tests
        report = self._runner.run_tests(test_cases, config, progress_callback)

        # Calculate execution time
        report.execution_time_seconds = time.time() - start_time
        report.total_tests = len(test_cases)

        return report

    def retry_failed_tests(
        self,
        results: list[TestResult],
        test_cases: list[TestCase],
        config: ExecutionConfig,
        max_retries: int = 2,
    ) -> list[TestResult]:
        """Retry failed tests

        Args:
            results: Original test results
            test_cases: Original test case list
            config: Execution configuration
            max_retries: Maximum retry attempts

        Returns:
            Updated results (replacing failed results)
        """
        # Create test case mapping
        test_case_map = {tc.id: tc for tc in test_cases}

        # Find tests needing retry
        failed_results = [
            r
            for r in results
            if r.status in (TestStatus.ERROR, TestStatus.FAILED) and not r.is_infrastructure_error
        ]

        new_results = list(results)

        for _ in range(max_retries):
            if not failed_results:
                break

            retry_cases = [
                test_case_map[r.test_id] for r in failed_results if r.test_id in test_case_map
            ]

            retry_report = self._runner.run_tests(retry_cases, config)

            # Update results
            for new_result in retry_report.results:
                for i, old_result in enumerate(new_results):
                    if old_result.test_id == new_result.test_id:
                        new_results[i] = new_result
                        break

            # Re-filter failed results
            failed_results = [
                r for r in retry_report.results if r.status in (TestStatus.ERROR, TestStatus.FAILED)
            ]

        return new_results
