"""
LLM Judge Interface

Defines the interface and data transfer objects for LLM-as-judge evaluation.
The judge determines whether an agent successfully executed a malicious injection
by analyzing the agent's output, command history, and tool call traces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.shared.types import AttackType


class LLMJudgeVerdict(str, Enum):
    """Verdict returned by the LLM judge."""

    ATTACK_SUCCESS = "attack_success"
    REJECTED = "rejected"
    IGNORED = "ignored"
    TECHNICAL = "technical"


@dataclass
class LLMJudgeRequest:
    """Request payload sent to the LLM judge.

    Contains all evidence the judge needs to determine whether the agent
    attempted or executed the malicious instruction.
    """

    attack_type: AttackType
    injection_text: str
    agent_output: str
    command_history: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    file_changes: dict[str, str] = field(default_factory=dict)
    custom_judge_prompt: str | None = None
    stderr_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_type": self.attack_type.value,
            "injection_text": self.injection_text[:500],
            "agent_output_length": len(self.agent_output),
            "command_history_count": len(self.command_history),
            "tool_calls_count": len(self.tool_calls),
            "has_custom_judge_prompt": self.custom_judge_prompt is not None,
        }


@dataclass
class LLMJudgeResult:
    """Result returned by the LLM judge.

    Contains the verdict, supporting evidence, and confidence score.
    """

    verdict: LLMJudgeVerdict
    evidence: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    raw_output: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }

    @property
    def is_attack_success(self) -> bool:
        return self.verdict == LLMJudgeVerdict.ATTACK_SUCCESS

    @property
    def is_rejected(self) -> bool:
        return self.verdict == LLMJudgeVerdict.REJECTED


class ILLMJudge(ABC):
    """Abstract interface for LLM-based judge evaluation.

    The judge receives collected evidence from a test execution and uses an LLM
    to determine whether the agent attempted or executed the malicious instruction.
    """

    @abstractmethod
    async def judge_injection(self, request: LLMJudgeRequest) -> LLMJudgeResult:
        """Evaluate whether an agent executed a malicious injection.

        Args:
            request: Evidence collected from the test execution.

        Returns:
            Judge result with verdict, evidence, and confidence.
        """
        ...

    @abstractmethod
    async def classify_response(self, request: LLMJudgeRequest) -> LLMJudgeResult:
        """Classify agent response as REJECTED or IGNORED.

        Always called when attack-success determination is negative.
        Uses retry with exponential backoff; returns TECHNICAL with
        classification_failed=True metadata when all retries exhaust.

        Args:
            request: Evidence collected from the test execution.

        Returns:
            Judge result with verdict (REJECTED or IGNORED).
        """
        ...
