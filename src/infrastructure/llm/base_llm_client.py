"""
LLM Client Abstract Base Class

Defines unified LLM client interface, supporting multiple LLM providers.
Includes built-in retry with exponential backoff for infrastructure errors.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from src.domain.generation.services.llm_injection_service import (
    InjectionPoint,
    LLMInjectionBatchRequest,
    LLMInjectionBatchResult,
    LLMInjectionRequest,
    LLMInjectionResult,
)
from src.domain.generation.value_objects.injection_strategy import InjectionStrategy
from src.shared.constants import LLM_TIMEOUT
from src.shared.exceptions import (
    ErrorCategory,
    RetryConfig,
    RetryTrace,
    _is_retryable_category,
)

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


@dataclass
class LLMClientConfig:
    """LLM Client Configuration

    Attributes:
        api_key: API key
        model: Model name
        max_tokens: Maximum tokens
        temperature: Temperature parameter
        timeout: Request timeout (seconds)
        retry_config: Retry configuration for infrastructure errors
    """

    api_key: str = ""
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = LLM_TIMEOUT
    retry_config: RetryConfig | None = None


class LLMClient(ABC):
    """LLM Client Abstract Base Class

    Defines interfaces that all LLM clients must implement.
    Provides built-in retry with exponential backoff for transient
    infrastructure errors (rate limits, timeouts, network failures).
    """

    def __init__(self, config: LLMClientConfig | None = None):
        """Initialize client

        Args:
            config: Client configuration
        """
        self._config = config or LLMClientConfig()
        self._retry_config = self._config.retry_config or RetryConfig(max_attempts=3)
        self._last_retry_trace: RetryTrace | None = None

    @property
    def last_retry_trace(self) -> RetryTrace | None:
        """Retrieve the RetryTrace from the most recent _call_with_retry()."""
        return self._last_retry_trace

    @abstractmethod
    def _classify_provider_error(self, error: Exception) -> ErrorCategory:
        """Classify a provider-specific exception for retry decisions.

        Each concrete client must implement this to map its SDK's
        exception hierarchy to ``ErrorCategory`` values.
        """
        ...

    async def _call_with_retry(
        self,
        operation: Callable[[], Awaitable[_T]],
        operation_name: str = "llm_api_call",
    ) -> _T:
        """Execute an async operation with retry and exponential backoff.

        Handles two failure modes:
        1. **Exception-based** – the operation raises and
           ``_classify_provider_error()`` decides whether to retry.
        2. **Result-based** – the operation returns an object with
           ``success=False``; the error message is classified to decide.

        The retry trace is stored in ``self._last_retry_trace`` for the
        caller to propagate into iteration metadata.

        Args:
            operation: Async callable that performs the provider API call.
            operation_name: Label for log messages and RetryTrace.

        Returns:
            The result of the operation (may be the raw API response or a
            structured result object).

        Raises:
            Exception: Re-raises the last exception when all retries are
                exhausted or the error is non-retryable.
        """
        config = self._retry_config
        trace_attempts: list[dict[str, Any]] = []
        total_delay = 0.0
        last_exception: Exception | None = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                result = await operation()

                # --- Check result-based failure (e.g. success=False) ---
                if hasattr(result, "success") and not result.success:
                    error_msg = getattr(result, "error_message", "") or "Unknown error"
                    category = classify_error_from_message(error_msg)

                    trace_attempts.append({
                        "attempt": attempt,
                        "error_type": category.value,
                        "error_message": error_msg[:200],
                    })

                    if not _is_retryable_category(category):
                        # Non-retryable failure – return immediately
                        self._last_retry_trace = RetryTrace(
                            operation_name=operation_name,
                            attempts=trace_attempts,
                            total_attempts=attempt,
                            final_outcome="non_retryable",
                            total_delay_seconds=total_delay,
                        )
                        return cast(_T, result)

                    if attempt >= config.max_attempts:
                        self._last_retry_trace = RetryTrace(
                            operation_name=operation_name,
                            attempts=trace_attempts,
                            total_attempts=attempt,
                            final_outcome="exhausted",
                            total_delay_seconds=total_delay,
                        )
                        return cast(_T, result)

                    delay = config.get_delay(attempt)
                    total_delay += delay
                    logger.warning(
                        "[Retry] %s attempt %d/%d result error (%s): %.100s, "
                        "retrying in %.1fs",
                        operation_name, attempt, config.max_attempts,
                        category.value, error_msg, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                # --- Success ---
                self._last_retry_trace = RetryTrace(
                    operation_name=operation_name,
                    attempts=trace_attempts,
                    total_attempts=attempt,
                    final_outcome="success" if attempt == 1 else "retried_success",
                    total_delay_seconds=total_delay,
                )
                return result

            except Exception as e:
                category = self._classify_provider_error(e)
                trace_attempts.append({
                    "attempt": attempt,
                    "error_type": category.value,
                    "error_message": str(e)[:200],
                })
                last_exception = e

                if not _is_retryable_category(category):
                    self._last_retry_trace = RetryTrace(
                        operation_name=operation_name,
                        attempts=trace_attempts,
                        total_attempts=attempt,
                        final_outcome="non_retryable",
                        total_delay_seconds=total_delay,
                    )
                    raise

                if attempt >= config.max_attempts:
                    self._last_retry_trace = RetryTrace(
                        operation_name=operation_name,
                        attempts=trace_attempts,
                        total_attempts=attempt,
                        final_outcome="exhausted",
                        total_delay_seconds=total_delay,
                    )
                    raise

                delay = config.get_delay(attempt)
                total_delay += delay
                logger.warning(
                    "[Retry] %s attempt %d/%d raised %s (%s): %.100s, "
                    "retrying in %.1fs",
                    operation_name, attempt, config.max_attempts,
                    type(e).__name__, category.value, e, delay,
                )
                await __import__("asyncio").sleep(delay)

        # Should not be reachable
        self._last_retry_trace = RetryTrace(
            operation_name=operation_name,
            attempts=trace_attempts,
            total_attempts=config.max_attempts,
            final_outcome="exhausted",
            total_delay_seconds=total_delay,
        )
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation_name} failed after {config.max_attempts} attempts")

    @abstractmethod
    async def inject_intelligent(self, request: LLMInjectionRequest) -> LLMInjectionResult:
        """Execute intelligent injection

        Args:
            request: Injection request

        Returns:
            Injection result
        """
        raise NotImplementedError

    @abstractmethod
    async def inject_intelligent_batch(
        self, batch_request: LLMInjectionBatchRequest
    ) -> LLMInjectionBatchResult:
        """Execute intelligent injection in batch

        Args:
            batch_request: Batch injection request

        Returns:
            Batch injection result
        """
        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name

        Returns:
            Provider name
        """
        raise NotImplementedError

    @abstractmethod
    def _build_prompt(self, request: LLMInjectionRequest, strategy: InjectionStrategy) -> str:
        """Build LLM prompt

        Args:
            request: Injection request
            strategy: Injection strategy

        Returns:
            Prompt string
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Generate code

        Args:
            prompt: Prompt for code generation
            language: Programming language (python/shell)

        Returns:
            Generated code content
        """
        raise NotImplementedError

    @abstractmethod
    async def chat(self, system_prompt: str | None, user_prompt: str) -> str:
        """Generic chat completion with optional system prompt.

        Returns raw text content without any cleaning or parsing.
        Used by the LLM-as-Judge evaluation pipeline.

        Args:
            system_prompt: Optional system prompt (provider-native format).
            user_prompt: User message content.

        Returns:
            Raw text content from the model response.
        """
        raise NotImplementedError

    def supports_batch(self) -> bool:
        """Check if batch processing is supported

        Default implementation returns True

        Returns:
            Whether batch processing is supported
        """
        return True

    def _parse_injection_points(
        self, response_text: str, original_content: str
    ) -> list[InjectionPoint]:
        """Parse injection point information from LLM response

        Args:
            response_text: LLM response text
            original_content: Original content

        Returns:
            List of injection points
        """
        # Default implementation: assume entire content was modified
        return [
            InjectionPoint(
                location="full_content",
                method="modify",
                original_text=original_content[:200],
                injected_text=response_text[:200],
            )
        ]

    def _calculate_confidence(self, response_text: str, strategy: InjectionStrategy) -> float:
        """Calculate injection confidence

        Args:
            response_text: Response text
            strategy: Injection strategy

        Returns:
            Confidence (0.0 - 1.0)
        """
        del response_text, strategy
        return 0.90

    def _extract_explanation(self, response_text: str) -> str:
        """Extract explanation from response

        Args:
            response_text: Response text

        Returns:
            Explanation text
        """
        # Try to extract JSON format explanation
        # Look for JSON format reasoning
        json_pattern = r'\s*"reasoning":\s*"(.*?)",?\s*\n'
        match = re.search(json_pattern, response_text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Look for XML tag format explanation
        xml_pattern = r"<explanation>(.*?)</explanation>"
        match = re.search(xml_pattern, response_text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Default explanation
        return "Payload injected using intelligent strategy"

    def _clean_response(self, response_text: str) -> str:
        """Clean LLM response, remove extra markers

        Args:
            response_text: Original response text

        Returns:
            Cleaned content
        """
        content = response_text

        # Remove JSON wrapper - use JSON parsing instead of regex
        if content.strip().startswith("{"):
            try:
                # Use JSON parsing to handle escape characters
                data = json.loads(content)
                # Prefer using skill_md field (Resource-First response)
                if "skill_md" in data:
                    content = data["skill_md"]
                # Secondly use content field (standard response)
                elif "content" in data:
                    content = data["content"]
            except (json.JSONDecodeError, UnicodeDecodeError):
                # JSON parsing failed, keep original content
                pass

        # Remove XML tags
        content = re.sub(r"<explanation>.*?</explanation>", "", content, flags=re.DOTALL)
        content = re.sub(r"<reasoning>.*?</reasoning>", "", content, flags=re.DOTALL)
        content = re.sub(r"<injection_points>.*?</injection_points>", "", content, flags=re.DOTALL)

        # Remove markdown code block markers
        content = self._strip_markdown_code_blocks(content)

        return content.strip()

    def _strip_markdown_code_blocks(self, content: str) -> str:
        """Remove markdown code block markers, keep content

        Supports removing the following code block markers:
        - ```markdown
        - ```yaml
        - ```text
        - ```json
        - ``` (no language identifier)

        Args:
            content: Content that may contain code block markers

        Returns:
            Content with code block markers removed
        """
        pattern = r"^```(?:\w+)?\s*\n(.*?)\n?```\s*$"
        match = re.search(pattern, content.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return content


def classify_error_from_message(error_message: str) -> ErrorCategory:
    """Classify an error from its message string (no exception object).

    Used by ``_call_with_retry`` when the LLM client returns
    ``success=False`` with an ``error_message`` instead of raising.
    """
    msg = error_message.lower()

    # LLM-specific retryable errors
    retryable_keywords = [
        "rate limit", "429", "too many requests", "quota", "capacity",
        "server error", "502", "503", "504", "500", "internal server",
        "service unavailable", "bad gateway", "gateway timeout",
        "timeout", "connection", "network", "httpx", "tcp", "socket",
    ]
    if any(kw in msg for kw in retryable_keywords):
        if "timeout" in msg:
            return ErrorCategory.TIMEOUT
        if any(kw in msg for kw in ["connection", "network", "httpx", "tcp", "socket"]):
            return ErrorCategory.NETWORK
        return ErrorCategory.TRANSIENT

    # LLM-specific permanent errors
    permanent_keywords = [
        "invalid api key", "authentication", "context_length_exceeded",
        "max_tokens", "content policy", "content_filter",
        "invalid request", "400",
    ]
    if any(kw in msg for kw in permanent_keywords):
        return ErrorCategory.PERMANENT

    # Validation errors
    validation_keywords = [
        "validation", "invalid", "not found", "does not exist",
        "permission", "unauthorized", "forbidden",
    ]
    if any(kw in msg for kw in validation_keywords):
        return ErrorCategory.VALIDATION

    return ErrorCategory.TRANSIENT
