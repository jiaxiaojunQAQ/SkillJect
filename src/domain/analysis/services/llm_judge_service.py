"""
LLM Judge Domain Service

Orchestrates LLM-based evaluation of test results to determine whether
an agent successfully executed a malicious injection. Complements the
existing rule-based ConsequenceDetector and RuleBasedFailureAnalyzer.
"""

import logging
from typing import TYPE_CHECKING

from src.domain.analysis.interfaces.i_llm_judge import (
    ILLMJudge,
    LLMJudgeRequest,
    LLMJudgeResult,
    LLMJudgeVerdict,
)
from src.domain.analysis.value_objects.judge_config import JudgeConfig
from src.domain.analysis.value_objects.judge_criteria import get_criteria
from src.shared.types import AttackType

# AttackType is used by classify_response() to build a lightweight request

if TYPE_CHECKING:
    from src.domain.generation.entities.test_suite import GeneratedTestCase
    from src.domain.testing.entities.test_case import TestResult

logger = logging.getLogger(__name__)

# Markers indicating technical failure (rate limits, infrastructure errors)
TECHNICAL_ERROR_MARKERS = (
    "Rate limit exceeded",
    "usage_limit_reached",
    "429 Too Many Requests",
)


class LLMJudgeService:
    """Domain service that uses an LLM to judge test execution results.

    This service extracts evidence from a TestResult and GeneratedTestCase,
    builds a judge request, and delegates the actual LLM call to an ILLMJudge
    implementation. It also handles technical failure detection before
    sending requests to the LLM.
    """

    def __init__(self, judge: ILLMJudge, config: JudgeConfig) -> None:
        self._judge = judge
        self._config = config

    async def evaluate_injection(
        self,
        test_result: "TestResult",
        generated_test: "GeneratedTestCase",
        custom_judge_prompt: str | None = None,
    ) -> LLMJudgeResult:
        """Evaluate whether an agent executed a malicious injection.

        Args:
            test_result: The execution result containing agent output.
            generated_test: The generated test case containing injection metadata.
            custom_judge_prompt: Optional per-injection custom verification criteria.

        Returns:
            LLMJudgeResult with verdict, evidence, and confidence.
        """
        attack_type = AttackType(generated_test.attack_type)
        injection_text = generated_test.metadata.get("task_script", "")

        # Quick check for technical failures before calling the LLM
        if self._check_technical_failure(test_result):
            logger.info(
                f"[LLM Judge] {generated_test.test_id}: "
                "Technical failure detected, skipping LLM evaluation"
            )
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence="Technical failure detected in agent stderr",
                confidence=1.0,
                reasoning="Agent encountered rate limit or infrastructure error",
                metadata={"skipped_llm_call": True},
            )

        # Build request from test artifacts
        request = self._build_judge_request(
            test_result=test_result,
            attack_type=attack_type,
            injection_text=injection_text,
            custom_judge_prompt=custom_judge_prompt,
        )

        # Delegate to LLM judge
        try:
            result = await self._judge.judge_injection(request)
            logger.info(
                f"[LLM Judge] {generated_test.test_id}: "
                f"Verdict={result.verdict.value}, "
                f"confidence={result.confidence:.2f}"
            )
            return result
        except Exception as e:
            logger.error(
                f"[LLM Judge] {generated_test.test_id}: "
                f"Judge call failed: {e}"
            )
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence=f"Judge call failed: {e}",
                confidence=0.0,
                reasoning="LLM judge call raised an exception",
                metadata={"error": str(e)},
            )

    def _build_judge_request(
        self,
        test_result: "TestResult",
        attack_type: AttackType,
        injection_text: str,
        custom_judge_prompt: str | None = None,
    ) -> LLMJudgeRequest:
        """Build a judge request from test artifacts.

        Extracts agent output, command history, tool calls, and file changes
        from the TestResult and its metadata.
        """
        # Get criteria for this attack type, optionally with custom prompt
        criteria = get_criteria(attack_type, custom_judge_prompt)
        effective_judge_prompt = criteria.format_for_prompt()

        return LLMJudgeRequest(
            attack_type=attack_type,
            injection_text="",
            agent_output=test_result.agent_output or "",
            command_history=[],
            tool_calls=[],
            file_changes={},
            custom_judge_prompt=effective_judge_prompt,
            stderr_output="",
        )

    @staticmethod
    def _check_technical_failure(test_result: "TestResult") -> bool:
        """Check if the test result indicates a technical failure.

        Technical failures (rate limits, crashes) should not be sent to the
        LLM judge since there is nothing meaningful to evaluate.
        """
        if test_result.is_infrastructure_error:
            return True

        stderr = test_result.metadata.get("stderr", "")
        if stderr and any(m in stderr for m in TECHNICAL_ERROR_MARKERS):
            return True

        return False

    async def classify_response(
        self,
        agent_output: str,
        test_id: str = "",
    ) -> LLMJudgeResult:
        """Classify an agent's non-attack response as REJECTED or IGNORED.

        Always called when attack-success determination is negative.
        Does NOT use _check_technical_failure() — that guard is only
        relevant for the attack-success judgment.

        Args:
            agent_output: The agent's response text.
            test_id: Optional test ID for logging.

        Returns:
            LLMJudgeResult with verdict (REJECTED, IGNORED, or TECHNICAL
            with classification_failed=True on retry exhaustion).
        """
        request = LLMJudgeRequest(
            attack_type=AttackType.DIRECT,
            injection_text="",
            agent_output=agent_output,
        )

        try:
            result = await self._judge.classify_response(request)
            logger.info(
                f"[Response Classifier] {test_id}: "
                f"Verdict={result.verdict.value}, "
                f"confidence={result.confidence:.2f}"
            )
            return result
        except Exception as e:
            logger.error(
                f"[Response Classifier] {test_id}: "
                f"Classification call failed: {e}"
            )
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence=f"Classification call failed: {e}",
                confidence=0.0,
                reasoning="LLM classifier call raised an exception",
                metadata={"classification_failed": True, "error": str(e)},
            )
