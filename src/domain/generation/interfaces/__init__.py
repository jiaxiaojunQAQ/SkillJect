"""
Domain Generation Layer Interfaces

Defines abstract interfaces for generation and injection, implementing strategy pattern and dependency injection
"""

from src.domain.generation.interfaces.i_llm_injection_provider import ILLMInjectionProvider
from src.domain.generation.interfaces.i_skill_parser import (
    ISkillParser,
    SkillParseResult,
)
from src.domain.generation.interfaces.i_test_generator import ITestGenerator

__all__ = [
    "ISkillParser",
    "SkillParseResult",
    "ITestGenerator",
    "ILLMInjectionProvider",
]
