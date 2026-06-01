"""Generation Result Entity

Defines various possible result types for test case generation, including:
- GeneratedTestCase: Successfully generated test case
- RefusedResult: Result when LLM refuses generation
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RefusedResult:
    """Result when LLM refuses to generate test case

    Returned when LLM refuses to generate test case due to security policy or other reasons.
    Contains detailed refusal information for logging and user feedback.

    Attributes:
        skill_name: Skill name
        attack_type: Attack type
        reason: Refusal reason (extracted from LLM response)
        response_content: LLM's original response (for debugging)
        timestamp: Timestamp when refusal occurred
    """

    skill_name: str
    attack_type: str
    reason: str
    response_content: str  # LLM's original response (for debugging)
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "skill_name": self.skill_name,
            "attack_type": self.attack_type,
            "reason": self.reason,
            "response_content": self.response_content,
            "timestamp": self.timestamp,
        }


__all__ = ["RefusedResult"]
