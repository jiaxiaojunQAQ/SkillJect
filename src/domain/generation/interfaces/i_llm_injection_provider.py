"""
LLM Injection Provider Interface

Defines the abstract interface for LLM intelligent injection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.domain.generation.value_objects.injection_strategy import InjectionStrategy
from src.shared.types import AttackType, InjectionLayer


@dataclass
class LLMInjectionRequest:
    """LLM injection request

    Attributes:
        skill_name: Skill name
        skill_content: Original skill content
        skill_frontmatter: Parsed frontmatter
        payload: Injection payload
        attack_type: Attack type
        injection_layer: Injection layer
        strategy: Injection strategy
        metadata: Additional metadata
    """

    skill_name: str
    skill_content: str
    skill_frontmatter: dict[str, Any]
    payload: str
    attack_type: AttackType
    injection_layer: InjectionLayer
    strategy: InjectionStrategy
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "skill_name": self.skill_name,
            "skill_content": self.skill_content,
            "skill_frontmatter": self.skill_frontmatter,
            "payload": self.payload,
            "attack_type": self.attack_type.value,
            "injection_layer": self.injection_layer.value,
            "strategy": self.strategy.strategy_type.value,
            "metadata": self.metadata or {},
        }


@dataclass
class LLMInjectionResult:
    """LLM injection result

    Attributes:
        success: Whether successful
        injected_content: Injected content
        used_strategy: Actually used strategy
        error_message: Error message
        metadata: Additional metadata
    """

    success: bool
    injected_content: str
    used_strategy: str
    error_message: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "injected_content": self.injected_content,
            "used_strategy": self.used_strategy,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }


class ILLMInjectionProvider(ABC):
    """LLM injection provider interface

    Defines abstract methods for using LLM for intelligent injection
    """

    @abstractmethod
    async def inject_intelligent(self, request: LLMInjectionRequest) -> LLMInjectionResult:
        """Execute intelligent injection

        Args:
            request: Injection request

        Returns:
            Injection result
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name

        Returns:
            Provider name (e.g., "mock", "openai", "anthropic")
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available

        Returns:
            Whether available
        """
        pass
