"""
LLM Judge Client

Concrete implementation of ILLMJudge using the OpenAI-compatible LLM interface.
Uses strict JSON-only verdict parsing with no text fallback.
"""

import json
import logging
import os
from collections.abc import Iterable

from src.domain.analysis.interfaces.i_llm_judge import (
    ILLMJudge,
    LLMJudgeRequest,
    LLMJudgeResult,
    LLMJudgeVerdict,
)
from src.domain.analysis.value_objects.judge_config import JudgeConfig
from src.infrastructure.llm.base_llm_client import LLMClient, LLMClientConfig
from src.infrastructure.llm.judge_prompts import (
    JUDGE_SYSTEM_PROMPT,
    RESPONSE_CLASSIFIER_SYSTEM_PROMPT,
    build_injection_judge_prompt,
    build_response_classification_prompt,
)
from src.shared.exceptions import RetryConfig, retry_with_trace
from src.shared.secrets import mask_secret

logger = logging.getLogger(__name__)


class LLMJudgeClient(ILLMJudge):
    """LLM judge client using OpenAI-compatible API.

    Creates an OpenAIClient directly and uses chat() for judge-specific
    LLM interactions. Only prompt construction and verdict parsing are
    judge-specific.
    """

    # Judge has its own retry config with slightly longer base delay
    _JUDGE_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0)
    _LOG_TEXT_LIMIT = 16000

    def __init__(self, config: JudgeConfig) -> None:
        self._config = config
        self._llm_client = self._create_llm_client(config)

    @staticmethod
    def _create_llm_client(config: JudgeConfig) -> LLMClient:
        """Create an OpenAI-compatible LLM client for judge calls.

        Resolution order (api_key and base_url are symmetric):
        - api_key:  env[config.api_key_env] -> env[OPENAI_API_KEY] -> error
        - base_url: config.base_url -> env[config.base_url_env]
                    -> env[OPENAI_BASE_URL] -> OpenAI default
        """
        from src.infrastructure.llm.openai_client import OpenAIClient
        from src.shared.exceptions import ConfigurationError

        base_url = config.base_url
        if not base_url and config.base_url_env:
            base_url = os.getenv(config.base_url_env, "")
        if not base_url:
            base_url = os.getenv("OPENAI_BASE_URL", "")

        api_key = ""
        api_key_source = ""
        if config.api_key_env:
            api_key = os.getenv(config.api_key_env, "")
            api_key_source = config.api_key_env
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")
            api_key_source = "OPENAI_API_KEY"
        if not api_key:
            checked = (
                f"'{config.api_key_env}' (llm_judge.api_key_env) and fallback 'OPENAI_API_KEY'"
                if config.api_key_env
                else "'OPENAI_API_KEY'"
            )
            raise ConfigurationError(
                f"Judge LLM API key not found: env var {checked} "
                "is unset. Set it in the project .env file."
            )

        logger.info(
            "Judge LLM client: model=%s base_url=%s api_key=%s (from %s)",
            config.model,
            base_url or "<OpenAI default>",
            mask_secret(api_key),
            api_key_source,
        )

        llm_config = LLMClientConfig(
            api_key=api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            timeout=config.timeout,
        )
        return OpenAIClient(llm_config, base_url=base_url)

    async def judge_injection(self, request: LLMJudgeRequest) -> LLMJudgeResult:
        """Evaluate injection by sending evidence to the LLM judge.

        Retries transient infrastructure errors with exponential backoff.
        Judge output must be valid JSON; invalid output is treated as TECHNICAL.
        """
        prompt = build_injection_judge_prompt(request)
        operation_name = "judge_injection"

        async def _do_judge() -> str:
            return await self._llm_client.chat(JUDGE_SYSTEM_PROMPT, prompt)

        try:
            raw_output, trace = await retry_with_trace(
                _do_judge,
                retry_config=self._JUDGE_RETRY_CONFIG,
                operation_name=operation_name,
            )
            result = self._parse_verdict(
                raw_output,
                allowed_verdicts=(
                    LLMJudgeVerdict.ATTACK_SUCCESS,
                    LLMJudgeVerdict.IGNORED,
                    LLMJudgeVerdict.TECHNICAL,
                ),
            )
            if trace.total_attempts > 1:
                result.metadata["retry_trace"] = trace.to_dict()
            self._log_judge_result(operation_name, raw_output, result)
            return result
        except Exception as e:
            logger.error("[JudgeClient] LLM call failed after retries: %s", e)
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence=f"LLM call failed after retries: {e}",
                confidence=0.0,
                reasoning="Exception during judge evaluation (all retries exhausted)",
                raw_output="",
                metadata={"error": str(e)},
            )

    async def classify_response(self, request: LLMJudgeRequest) -> LLMJudgeResult:
        """Classify agent response as REJECTED or IGNORED.

        Always called when attack-success determination is negative.
        Uses retry with exponential backoff. Output must be valid JSON;
        invalid output is treated as classification_failed.
        """
        prompt = build_response_classification_prompt(
            agent_output=request.agent_output,
        )
        operation_name = "classify_response"

        async def _do_classify() -> str:
            return await self._llm_client.chat(RESPONSE_CLASSIFIER_SYSTEM_PROMPT, prompt)

        try:
            raw_output, trace = await retry_with_trace(
                _do_classify,
                retry_config=self._JUDGE_RETRY_CONFIG,
                operation_name=operation_name,
            )
            result = self._parse_verdict(
                raw_output,
                allowed_verdicts=(
                    LLMJudgeVerdict.REJECTED,
                    LLMJudgeVerdict.IGNORED,
                    LLMJudgeVerdict.TECHNICAL,
                ),
                classification_mode=True,
            )

            if trace.total_attempts > 1:
                result.metadata["retry_trace"] = trace.to_dict()
            self._log_judge_result(operation_name, raw_output, result)
            return result
        except Exception as e:
            logger.error("[JudgeClient] Response classification failed after retries: %s", e)
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence=f"Classification failed after retries: {e}",
                confidence=0.0,
                reasoning="Exception during response classification (all retries exhausted)",
                raw_output="",
                metadata={"classification_failed": True, "error": str(e)},
            )

    @classmethod
    def _parse_verdict(
        cls,
        raw_output: str,
        *,
        allowed_verdicts: Iterable[LLMJudgeVerdict] = (
            LLMJudgeVerdict.ATTACK_SUCCESS,
            LLMJudgeVerdict.REJECTED,
            LLMJudgeVerdict.IGNORED,
            LLMJudgeVerdict.TECHNICAL,
        ),
        classification_mode: bool = False,
    ) -> LLMJudgeResult:
        """Parse strict JSON output from the judge LLM.

        There is no text fallback: invalid or unknown payloads are treated
        as TECHNICAL. Response classification failures are marked explicitly.
        """
        metadata: dict[str, object] = {}
        if classification_mode:
            metadata["classification_failed"] = True

        if not raw_output or not raw_output.strip():
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.TECHNICAL,
                evidence="Empty response from judge LLM",
                confidence=0.0,
                reasoning="Judge returned an empty response",
                raw_output=raw_output,
                metadata=metadata,
            )

        json_verdict, evidence, reasoning = _extract_json_verdict(raw_output)
        allowed = set(allowed_verdicts)
        if json_verdict is not None:
            if json_verdict not in allowed:
                return LLMJudgeResult(
                    verdict=LLMJudgeVerdict.TECHNICAL,
                    evidence=f"Judge returned unsupported verdict: {json_verdict.value}",
                    confidence=0.0,
                    reasoning="Judge JSON contained a verdict outside the allowed set",
                    raw_output=raw_output,
                    metadata=metadata,
                )

            success_metadata = dict(metadata)
            if classification_mode:
                success_metadata["classification_failed"] = False
            return LLMJudgeResult(
                verdict=json_verdict,
                evidence=evidence,
                confidence=0.9 if evidence else 0.5,
                reasoning=reasoning,
                raw_output=raw_output,
                metadata=success_metadata,
            )

        return LLMJudgeResult(
            verdict=LLMJudgeVerdict.TECHNICAL,
            evidence="Judge response was not valid JSON",
            confidence=0.0,
            reasoning="Judge output must be a single valid JSON object",
            raw_output=raw_output,
            metadata=metadata,
        )

    @classmethod
    def _truncate_for_log(cls, text: str) -> str:
        if len(text) <= cls._LOG_TEXT_LIMIT:
            return text
        return f"{text[:cls._LOG_TEXT_LIMIT]}\n... [truncated]"

    def _log_judge_result(
        self,
        operation_name: str,
        raw_output: str,
        result: LLMJudgeResult,
    ) -> None:
        logger.info(
            "[JudgeClient] %s result | raw_output=%s parsed_verdict=%s parsed_evidence=%s parsed_reasoning=%s",
            operation_name,
            self._truncate_for_log(raw_output),
            result.verdict.value,
            self._truncate_for_log(result.evidence),
            self._truncate_for_log(result.reasoning),
        )


def _extract_json_verdict(
    output: str,
) -> tuple[LLMJudgeVerdict | None, str, str]:
    """Try to extract verdict from JSON response.

    Returns (verdict, evidence, reasoning) or (None, "", "") on failure.
    """
    try:
        data = json.loads(output.strip())
        verdict_str = data.get("verdict", "").lower().strip()

        verdict_map = {
            "attack_success": LLMJudgeVerdict.ATTACK_SUCCESS,
            "rejected": LLMJudgeVerdict.REJECTED,
            "ignored": LLMJudgeVerdict.IGNORED,
            "technical": LLMJudgeVerdict.TECHNICAL,
        }
        verdict = verdict_map.get(verdict_str)
        if verdict is not None:
            evidence = data.get("evidence", "")
            reasoning = data.get("reasoning", "")
            return verdict, evidence, reasoning
    except (json.JSONDecodeError, KeyError, AttributeError):
        pass

    return None, "", ""
