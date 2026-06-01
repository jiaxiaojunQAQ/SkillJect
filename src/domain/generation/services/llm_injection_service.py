"""
LLM Injection Service Domain Interface

Defines service interfaces and data transfer objects for LLM intelligent injection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.domain.generation.value_objects.injection_strategy import InjectionStrategy
from src.shared.types import AttackType, InjectionLayer


@dataclass
class LLMInjectionRequest:
    """LLM injection request

    Contains all input parameters needed to execute intelligent injection

    Attributes:
        skill_name: Skill name
        skill_content: Original content of skill file
        skill_frontmatter: Skill frontmatter data
        payload: Attack payload to inject
        attack_type: Attack type
        injection_layer: Injection layer
        strategy: Injection strategy
        context: Additional context information
        use_raw_prompt: Whether to use payload directly as prompt (skip standard prompt construction)
    """

    skill_name: str
    skill_content: str
    skill_frontmatter: dict[str, Any]
    payload: str
    attack_type: AttackType
    injection_layer: InjectionLayer
    strategy: InjectionStrategy
    context: dict[str, Any] = field(default_factory=dict)
    use_raw_prompt: bool = False

    def get_skill_description(self) -> str:
        """Get skill description

        Returns:
            Skill description text
        """
        return self.skill_frontmatter.get("description", "")

    def get_skill_category(self) -> str:
        """Get skill category

        Returns:
            Skill category
        """
        return self.skill_frontmatter.get("category", "general")

    def has_resources(self) -> bool:
        """Check if there are resource files

        Returns:
            Whether there are resources
        """
        return bool(self.skill_frontmatter.get("resources"))


@dataclass
class InjectionPoint:
    """Injection point information

    Describes where and how the payload is injected

    Attributes:
        location: Location description (e.g., "description", "instruction", "resource")
        method: Injection method (e.g., "prepend", "append", "replace")
        original_text: Original text fragment
        injected_text: Injected text
    """

    location: str
    method: str
    original_text: str
    injected_text: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "location": self.location,
            "method": self.method,
            "original_text": self.original_text[:100] + "..."
            if len(self.original_text) > 100
            else self.original_text,
            "injected_text": self.injected_text[:100] + "..."
            if len(self.injected_text) > 100
            else self.injected_text,
        }


@dataclass
class LLMInjectionResult:
    """LLM injection result

    Contains all output information after injection execution

    Attributes:
        injected_content: Complete content after injection
        injection_points: List of injection points
        explanation: Injection strategy explanation
        confidence: Confidence level (0.0 - 1.0)
        metadata: Additional metadata
        success: Whether successful
        error_message: Error message (if any)
    """

    injected_content: str
    injection_points: list[InjectionPoint]
    explanation: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""

    def __post_init__(self) -> None:
        """Validate result data"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got: {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "injected_content": self.injected_content,
            "injection_points": [ip.to_dict() for ip in self.injection_points],
            "explanation": self.explanation,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class LLMInjectionBatchRequest:
    """Batch LLM injection request

    Contains multiple single injection requests for batch processing

    Attributes:
        requests: List of single injection requests
        max_concurrency: Maximum concurrency
    """

    requests: list[LLMInjectionRequest]
    max_concurrency: int = 4

    def __len__(self) -> int:
        """Get number of requests"""
        return len(self.requests)

    def is_empty(self) -> bool:
        """Check if empty"""
        return len(self.requests) == 0


@dataclass
class LLMInjectionBatchResult:
    """Batch LLM injection result

    Contains summary of batch processing results

    Attributes:
        results: List of single injection results
        total_count: Total count
        success_count: Success count
        failure_count: Failure count
        errors: List of errors
    """

    results: list[LLMInjectionResult]
    total_count: int
    success_count: int
    failure_count: int
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_results(cls, results: list[LLMInjectionResult]) -> "LLMInjectionBatchResult":
        """Create batch result from list of results

        Args:
            results: List of single results

        Returns:
            Batch result object
        """
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        errors = [r.error_message for r in results if not r.success and r.error_message]

        return cls(
            results=results,
            total_count=len(results),
            success_count=success_count,
            failure_count=failure_count,
            errors=errors,
        )


class LLMInjectionService(ABC):
    """Abstract interface for LLM injection service

    Defines unified interface for LLM intelligent injection services
    """

    @abstractmethod
    async def inject_intelligent(self, request: LLMInjectionRequest) -> LLMInjectionResult:
        """Execute intelligent injection

        Use LLM to intelligently inject attack payload into skill content

        Args:
            request: Injection request

        Returns:
            Injection result

        Raises:
            Exception: Errors during injection
        """
        raise NotImplementedError

    @abstractmethod
    async def inject_intelligent_batch(
        self, request: LLMInjectionBatchRequest
    ) -> LLMInjectionBatchResult:
        """Execute batch intelligent injection

        Args:
            request: Batch injection request

        Returns:
            Batch injection result
        """
        raise NotImplementedError

    @abstractmethod
    def supports_batch(self) -> bool:
        """Check if batch processing is supported

        Returns:
            Whether batch processing is supported
        """
        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get LLM provider name

        Returns:
            Provider name (e.g., "anthropic", "openai", "mock")
        """
        raise NotImplementedError
# mypy: disable-error-code="no-any-return"
