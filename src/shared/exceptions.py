"""
Shared Exception Definitions Module

Provides common exception classes for cross-module use, including:
1. Domain exception classes
2. Test exception system with retry mechanism
3. Retry trace for infrastructure error tracking
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Domain Exception Classes (Original)
# =============================================================================


class EvaluationError(Exception):
    """Base class for evaluation errors"""

    pass


class ConfigurationError(EvaluationError):
    """Configuration error"""

    pass


class SkillNotFoundError(EvaluationError):
    """Skill not found error"""

    pass


class AgentNotFoundError(EvaluationError):
    """Agent not found error"""

    pass


class TestNotFoundError(EvaluationError):
    """Test not found error"""

    pass


class PayloadNotFoundError(EvaluationError):
    """Payload not found error"""

    pass


# ValidationError is defined below, merging two versions


# =============================================================================
# Error Classification System (Merged from src.exceptions.py)
# =============================================================================


class ErrorCategory(Enum):
    """Error category"""

    TRANSIENT = "transient"  # Temporary error, retryable
    PERMANENT = "permanent"  # Permanent error, should not retry
    TIMEOUT = "timeout"  # Timeout error, possibly retryable
    NETWORK = "network"  # Network error, possibly retryable
    VALIDATION = "validation"  # Validation error, should not retry


class SecurityTestError(EvaluationError):
    """Base exception for security testing framework

    Inherits from EvaluationError, supports error classification and retry determination.
    """

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.PERMANENT):
        self.message = message
        self.category = category
        super().__init__(self.message)

    def is_retryable(self) -> bool:
        """Check if the error is retryable"""
        return self.category in [
            ErrorCategory.TRANSIENT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
        ]


class SandboxError(SecurityTestError):
    """Sandbox-related error"""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.TRANSIENT):
        super().__init__(f"Sandbox error: {message}", category)


class TestExecutionError(SecurityTestError):
    """Test execution error"""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.PERMANENT):
        super().__init__(f"Test execution error: {message}", category)


class ConsequenceDetectionError(SecurityTestError):
    """Consequence detection error"""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.PERMANENT):
        super().__init__(f"Consequence detection error: {message}", category)


class LogCollectionError(SecurityTestError):
    """Log collection error"""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.TRANSIENT):
        super().__init__(f"Log collection error: {message}", category)


# Merge two versions of TimeoutError
class TimeoutError(SecurityTestError):
    """Timeout error"""

    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(f"Timeout after {timeout_seconds}s: {message}", ErrorCategory.TIMEOUT)
        self.timeout_seconds = timeout_seconds


# Use SecurityTestError as the base class for ValidationError
class ValidationError(SecurityTestError):
    """Validation error (with error classification)"""

    def __init__(self, message: str):
        super().__init__(f"Validation error: {message}", ErrorCategory.VALIDATION)


# =============================================================================
# Retry Configuration and Utilities
# =============================================================================


@dataclass
class RetryConfig:
    """Retry configuration"""

    max_attempts: int = 3  # Maximum number of attempts (including first)
    base_delay: float = 1.0  # Base delay (seconds)
    max_delay: float = 30.0  # Maximum delay (seconds)
    exponential_backoff: bool = True  # Whether to use exponential backoff
    jitter: bool = True  # Whether to add random jitter

    def get_delay(self, attempt: int) -> float:
        """
        Get the delay time for the Nth retry

        Args:
            attempt: Current retry count (starting from 1)

        Returns:
            Delay time in seconds
        """
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.base_delay

        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return float(delay)


@dataclass
class RetryTrace:
    """Structured record of retry attempts for an operation.

    Captures every attempt's error type, error message, and the delay before
    the next attempt.  Carried through ``metadata["retry_trace"]`` so it
    automatically flows into ``result.json`` and ``raw_logs.txt``.
    """

    operation_name: str
    attempts: list[dict[str, Any]] = field(default_factory=list)
    total_attempts: int = 1
    final_outcome: str = "success"  # success | retried_success | exhausted | non_retryable
    total_delay_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_name": self.operation_name,
            "attempts": self.attempts,
            "total_attempts": self.total_attempts,
            "final_outcome": self.final_outcome,
            "total_delay_seconds": round(self.total_delay_seconds, 2),
        }

    @property
    def retry_count(self) -> int:
        """Number of retries (total_attempts - 1)."""
        return max(0, self.total_attempts - 1)


# Retryable error categories
_RETRYABLE_CATEGORIES = frozenset({
    ErrorCategory.TRANSIENT,
    ErrorCategory.TIMEOUT,
    ErrorCategory.NETWORK,
})


def _is_retryable_category(category: ErrorCategory) -> bool:
    return category in _RETRYABLE_CATEGORIES


async def retry_with_trace(
    func: Callable,
    retry_config: RetryConfig | None = None,
    operation_name: str = "operation",
    should_retry_result: Callable[[Any], bool] | None = None,
    classify_result_error: Callable[[Any], ErrorCategory] | None = None,
) -> tuple[Any, RetryTrace]:
    """Execute *func* with exponential-backoff retry and return a
    ``(result, RetryTrace)`` tuple.

    Supports two failure modes:

    1. **Exception-based** – *func* raises and ``classify_result_error``
       (or ``classify_error``) decides whether the exception is retryable.
    2. **Result-based** – *func* returns an object whose ``success``
       attribute is falsy.  ``should_retry_result`` must be provided to
       inspect the result and decide whether to retry.

    Args:
        func: Async callable to execute.
        retry_config: Retry parameters (defaults to ``RetryConfig()``).
        operation_name: Human-readable label for log messages.
        should_retry_result: Optional predicate that inspects the return
            value and returns ``True`` when a retry is warranted.
        classify_result_error: Optional callable that inspects the return
            value and returns its ``ErrorCategory``.  Used together with
            *should_retry_result*.  Defaults to string-based classification.

    Returns:
        ``(result, trace)`` – *result* is whatever *func* returns;
        *trace* records every attempt.
    """
    if retry_config is None:
        retry_config = RetryConfig()

    trace = RetryTrace(operation_name=operation_name)
    total_delay = 0.0

    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            result = await func()

            # --- result-based retry check ---
            if should_retry_result is not None and should_retry_result(result):
                category = (
                    classify_result_error(result)
                    if classify_result_error
                    else ErrorCategory.TRANSIENT
                )
                error_msg = getattr(result, "error_message", "") or str(result)[:200]

                trace.attempts.append({
                    "attempt": attempt,
                    "error_type": category.value,
                    "error_message": error_msg[:200],
                })

                if not _is_retryable_category(category):
                    trace.total_attempts = attempt
                    trace.final_outcome = "non_retryable"
                    trace.total_delay_seconds = total_delay
                    return result, trace

                if attempt >= retry_config.max_attempts:
                    trace.total_attempts = attempt
                    trace.final_outcome = "exhausted"
                    trace.total_delay_seconds = total_delay
                    return result, trace

                delay = retry_config.get_delay(attempt)
                total_delay += delay
                logger.warning(
                    "[Retry] %s attempt %d/%d failed (result): %.100s, "
                    "retrying in %.1fs",
                    operation_name, attempt, retry_config.max_attempts,
                    error_msg, delay,
                )
                await asyncio.sleep(delay)
                continue

            # --- success ---
            trace.total_attempts = attempt
            trace.final_outcome = "success" if attempt == 1 else "retried_success"
            trace.total_delay_seconds = total_delay
            return result, trace

        except SecurityTestError as e:
            category = e.category
            trace.attempts.append({
                "attempt": attempt,
                "error_type": category.value,
                "error_message": str(e)[:200],
            })

            if not _is_retryable_category(category):
                trace.total_attempts = attempt
                trace.final_outcome = "non_retryable"
                trace.total_delay_seconds = total_delay
                raise

            if attempt >= retry_config.max_attempts:
                trace.total_attempts = attempt
                trace.final_outcome = "exhausted"
                trace.total_delay_seconds = total_delay
                raise

            delay = retry_config.get_delay(attempt)
            total_delay += delay
            logger.warning(
                "[Retry] %s attempt %d/%d raised %s: %.100s, "
                "retrying in %.1fs",
                operation_name, attempt, retry_config.max_attempts,
                type(e).__name__, e.message, delay,
            )
            await asyncio.sleep(delay)

        except Exception as e:
            category = classify_error(e)
            trace.attempts.append({
                "attempt": attempt,
                "error_type": category.value,
                "error_message": str(e)[:200],
            })

            if not _is_retryable_category(category):
                trace.total_attempts = attempt
                trace.final_outcome = "non_retryable"
                trace.total_delay_seconds = total_delay
                raise

            if attempt >= retry_config.max_attempts:
                trace.total_attempts = attempt
                trace.final_outcome = "exhausted"
                trace.total_delay_seconds = total_delay
                raise

            delay = retry_config.get_delay(attempt)
            total_delay += delay
            logger.warning(
                "[Retry] %s attempt %d/%d raised %s: %.100s, "
                "retrying in %.1fs",
                operation_name, attempt, retry_config.max_attempts,
                type(e).__name__, e, delay,
            )
            await asyncio.sleep(delay)

    # Should not be reachable, but guard anyway
    trace.total_attempts = retry_config.max_attempts
    trace.final_outcome = "exhausted"
    trace.total_delay_seconds = total_delay
    raise SecurityTestError(
        f"{operation_name} failed after {retry_config.max_attempts} attempts"
    )


async def retry_with_backoff(
    func: Callable,
    retry_config: RetryConfig | None = None,
    operation_name: str = "operation",
) -> Any:
    """Backward-compatible wrapper that discards the RetryTrace.

    Delegates to :func:`retry_with_trace` and returns only the result.
    """
    result, _ = await retry_with_trace(func, retry_config, operation_name)
    return result


def classify_error(error: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category

    Args:
        error: Exception object

    Returns:
        Error category
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # LLM-specific retryable errors
    llm_retryable_keywords = [
        "rate limit",
        "429",
        "too many requests",
        "quota",
        "capacity",
        "server error",
        "502",
        "503",
        "504",
        "500",
        "internal server",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
    ]
    if any(kw in error_str for kw in llm_retryable_keywords):
        return ErrorCategory.TRANSIENT

    # LLM-specific permanent errors
    llm_permanent_keywords = [
        "invalid api key",
        "authentication",
        "context_length_exceeded",
        "max_tokens",
        "content policy",
        "content_filter",
    ]
    if any(kw in error_str for kw in llm_permanent_keywords):
        return ErrorCategory.PERMANENT

    # Network-related errors
    network_keywords = [
        "connection",
        "network",
        "remote",
        "protocol",
        "httpx",
        "tcp",
        "socket",
    ]
    if any(keyword in error_str or keyword in error_type for keyword in network_keywords):
        return ErrorCategory.NETWORK

    # Timeout errors
    if "timeout" in error_str or "timeout" in error_type:
        return ErrorCategory.TIMEOUT

    # Validation errors
    validation_keywords = [
        "validation",
        "invalid",
        "not found",
        "does not exist",
        "permission",
        "unauthorized",
        "forbidden",
    ]
    if any(keyword in error_str for keyword in validation_keywords):
        return ErrorCategory.VALIDATION

    # Default to transient error
    return ErrorCategory.TRANSIENT


def wrap_error(error: Exception, context: str = "") -> SecurityTestError:
    """
    Wrap a generic exception as SecurityTestError

    Args:
        error: Original exception
        context: Context information

    Returns:
        SecurityTestError instance
    """
    if isinstance(error, SecurityTestError):
        return error

    category = classify_error(error)
    message = f"{context}: {error}" if context else str(error)

    return SecurityTestError(message, category)


__all__ = [
    # Domain exceptions
    "EvaluationError",
    "ConfigurationError",
    "SkillNotFoundError",
    "AgentNotFoundError",
    "TestNotFoundError",
    "PayloadNotFoundError",
    "ValidationError",
    # Error classification system
    "ErrorCategory",
    "SecurityTestError",
    "SandboxError",
    "TestExecutionError",
    "ConsequenceDetectionError",
    "LogCollectionError",
    "TimeoutError",
    # Retry mechanism
    "RetryConfig",
    "RetryTrace",
    "retry_with_backoff",
    "retry_with_trace",
    "classify_error",
    "wrap_error",
]
