"""
Streaming Test Orchestrator

Implements streaming test processing mode: generate one test case, test it immediately,
and dynamically adjust the next generation parameters based on results.
Unlike batch mode, streaming mode supports real-time feedback loops and early stopping.

Core improvements:
- Batch mode: Generate N tests -> Execute N tests -> Analyze -> Next round
- Streaming mode: Generate 1 test -> Execute -> Analyze -> Adjust parameters -> Generate next

Feedback-driven adaptive iteration:
- Use analyze_failure to analyze failure patterns
- Use AdaptiveGenerationParams to pass feedback to LLM
- LLM dynamically generates improved versions based on feedback
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.analysis.services.llm_judge_service import LLMJudgeService

from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig
from src.shared.types import AttackType, InjectionLayer, Severity, TestStatus

from ...domain.analysis.services.verdict_resolver import FailureAnalysis, analyze_failure
from ...domain.generation.entities.generation_result import RefusedResult
from ...domain.generation.entities.test_suite import GeneratedTestCase
from ...domain.generation.services.adaptive_params import AdaptiveGenerationParams
from ...domain.generation.services.generation_factory import TestGenerationStrategyFactory
from ...domain.testing.entities.test_case import TestCase, TestCaseId, TestResult
from ...shared.exceptions import RetryConfig

logger = logging.getLogger(__name__)


@dataclass
class StreamingProgress:
    """Streaming processing progress

    Tracks real-time progress of streaming test processing
    """

    total_generated: int = 0
    total_executed: int = 0
    total_success: int = 0  # Number of attack-succeeded tests
    total_blocked: int = 0  # Number of blocked/defended tests
    total_ignored: int = 0  # Number of ignored tests (neither success nor blocked)
    total_classification_failed: int = 0  # Number of tests where response classification failed
    total_determined: int = 0  # Number of tests with clear results (success + blocked + ignored)
    current_skill: str = ""
    current_attack_type: str = ""
    current_params: dict = field(default_factory=dict)
    message: str = ""

    @property
    def success_rate(self) -> float:
        """Calculate attack success rate (based on tests with clear results).

        Returns:
            Success rate (0-1), attack success rate / ASR
        """
        if self.total_determined == 0:
            return 0.0
        return self.total_success / self.total_determined

    @property
    def block_rate(self) -> float:
        """Calculate block/defense rate for determined results."""
        if self.total_determined == 0:
            return 0.0
        return self.total_blocked / self.total_determined

    @property
    def undetermined_count(self) -> int:
        """Number of tests with undetermined results (including classification failures)"""
        return self.total_executed - self.total_determined - self.total_classification_failed

    @property
    def ignored_rate(self) -> float:
        """Calculate ignored rate for determined results."""
        if self.total_determined == 0:
            return 0.0
        return self.total_ignored / self.total_determined

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_generated": self.total_generated,
            "total_executed": self.total_executed,
            "total_success": self.total_success,
            "total_blocked": self.total_blocked,
            "total_ignored": self.total_ignored,
            "total_classification_failed": self.total_classification_failed,
            "total_determined": self.total_determined,
            "undetermined_count": self.undetermined_count,
            "success_rate": self.success_rate,
            "block_rate": self.block_rate,
            "ignored_rate": self.ignored_rate,
            "current_skill": self.current_skill,
            "current_attack_type": self.current_attack_type,
            "current_params": self.current_params,
            "message": self.message,
        }


@dataclass
class StreamingResult:
    """Streaming processing result

    Final result of streaming test execution
    """

    total_generated: int
    total_executed: int
    total_success: int
    total_blocked: int
    total_ignored: int  # Number of ignored tests (neither success nor blocked)
    total_classification_failed: int  # Number of tests where response classification failed
    total_determined: int  # Number of tests with clear results (success + blocked + ignored)
    success_rate: float
    block_rate: float
    ignored_rate: float
    success_tests: list[str]  # Attack-succeeded test IDs
    blocked_tests: list[str]  # Blocked/defended test IDs
    ignored_tests: list[str]  # Ignored test IDs (neither success nor blocked)
    classification_failed_tests: list[str]  # Tests where response classification failed
    execution_time_seconds: float
    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped_skills: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        total_test_cases = (
            len(self.success_tests) + len(self.blocked_tests) + len(self.ignored_tests)
        )

        return {
            "total_generated": self.total_generated,
            "total_executed": self.total_executed,
            "total_success": self.total_success,
            "total_blocked": self.total_blocked,
            "total_ignored": self.total_ignored,
            "total_classification_failed": self.total_classification_failed,
            "determined_count": self.total_determined,
            "undetermined_count": self.total_executed - self.total_determined - self.total_classification_failed,
            "total_test_cases": total_test_cases,
            "success_rate": self.success_rate,
            "block_rate": self.block_rate,
            "ignored_rate": self.ignored_rate,
            "success_tests": self.success_tests,
            "blocked_tests": self.blocked_tests,
            "ignored_tests": self.ignored_tests,
            "classification_failed_tests": self.classification_failed_tests,
            "execution_time_seconds": self.execution_time_seconds,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "metadata": self.metadata,
            "skipped_skills": self.skipped_skills,
        }


class StreamingOrchestrator:
    """Streaming test orchestrator

    Implements core logic for streaming test processing:
    1. Iterate through skills
    2. Attempt multiple iterations for each skill
    3. Generate -> Execute -> Analyze -> Generate next based on feedback (closed loop)
    4. Support early stopping mechanism

    Uses feedback-driven adaptive iteration:
    - RuleBasedFailureAnalyzer analyzes failure patterns
    - AdaptiveGenerationParams passes feedback to LLM
    - LLM dynamically generates improved versions based on feedback
    """

    def __init__(
        self,
        config: TwoPhaseExecutionConfig,
        max_attempts_per_test: int = 3,
        stop_on_success: bool = False,
        max_concurrency: int = 4,
    ):
        """Initialize streaming orchestrator

        Args:
            config: Two-phase execution configuration
            max_attempts_per_test: Maximum attempts per test (default 6)
            stop_on_success: Whether to stop after single success (skip remaining iterations)
            max_concurrency: Maximum concurrency for skill-attack pairs (default 4)
        """
        self._config = config
        self._max_attempts_per_test = max_attempts_per_test
        self._stop_on_success = stop_on_success
        self._max_concurrency = max_concurrency

        # Infrastructure error retry: reuse execution.max_retries for all infra errors.
        # Uses RetryConfig for delay calculation (exponential backoff with jitter).
        self._infra_retry_cfg = RetryConfig(
            max_attempts=config.execution.max_retries + 1,
            base_delay=10.0,
            max_delay=120.0,
        )
        self._infra_retry_counts: dict[str, int] = {}

        # Completed test case set {skill_name: {attack_type}}
        self._completed_tests: dict[str, set[str]] = {}
        self._history_reused_tests: dict[str, dict[str, object]] = {}

        # Create generator, test runner, and failure analyzer
        # Use factory pattern to create generator, supports all generation strategies
        # Pass execution.output_dir so generator saves to test_details directory
        self._generator = TestGenerationStrategyFactory.create(
            config.generation,
            execution_output_dir=Path(config.execution.output_dir),
        )
        # Use factory function to create test runner based on agent_type
        from src.domain.testing.services.sandbox_test_runner import create_sandbox_test_runner
        logger.info(f"[Streaming Orch] Creating test runner, agent_type: {config.execution.agent.agent_type}")
        self._test_runner = create_sandbox_test_runner(config)
        logger.info(f"[Streaming Orch] Test runner created: {type(self._test_runner).__name__}")

        # Initialize LLM judge service (response classification always needs LLM)
        self._judge_service = self._init_judge_service(config)
        self._judge_config_attack_judgment = config.judge.attack_judgment if config.judge else False

        # Log generator type (for debugging)
        logger.info(
            f"[Streaming Orch] Initialized generator: {type(self._generator).__name__} "
            f"(strategy: {config.generation.strategy.value})"
        )

        # Statistics (requires concurrency protection)
        self._success_tests: list[str] = []
        self._blocked_tests: list[str] = []
        self._ignored_tests: list[str] = []
        self._classification_failed_tests: list[str] = []
        self._pending_reclassification: dict[str, dict] = {}
        self._resume_states: dict[str, dict[str, Any]] = {}

        # Early stopping state (requires concurrency protection)
        self._skill_success: dict[str, set[str]] = {}  # {skill_name: {attack_type}}

        # Concurrency control locks
        self._early_stop_lock = asyncio.Lock()  # Protect _skill_success state
        self._progress_lock = asyncio.Lock()  # Protect progress updates (_success_tests, _blocked_tests)
        self._completed_lock = asyncio.Lock()  # Protect _completed_tests state

    @staticmethod
    def _serialize_judge_result(result: Any) -> dict[str, Any] | None:
        """Convert a judge/classification result into a stable JSON-friendly dict."""
        if result is None:
            return None

        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            raw_data = to_dict()
            if not isinstance(raw_data, dict):
                return None
            data = dict(raw_data)
        elif isinstance(result, dict):
            data = dict(result)
        else:
            return None

        metadata = data.get("metadata", {})
        if isinstance(metadata, dict) and "classification_failed" in metadata:
            data["classification_failed"] = bool(metadata["classification_failed"])
        return data

    @staticmethod
    def _record_result_metadata(
        test_result: TestResult,
        *,
        judge_result: Any = None,
        response_classification: Any = None,
    ) -> None:
        """Attach serialized judge outputs to the test result metadata."""
        if judge_result is not None:
            serialized_judge = StreamingOrchestrator._serialize_judge_result(judge_result)
            if serialized_judge is not None:
                test_result.metadata["judge"] = serialized_judge

        if response_classification is not None:
            serialized_classification = StreamingOrchestrator._serialize_judge_result(
                response_classification
            )
            if serialized_classification is not None:
                test_result.metadata["response_classification"] = serialized_classification

    def _persist_result_json_update(
        self,
        *,
        generated_test: GeneratedTestCase,
        skill_name: str,
        attack_type: AttackType,
        iteration_number: int,
        test_result: TestResult,
        finalize_classification: bool = False,
    ) -> None:
        """Sync in-memory result updates back into the already-written result.json."""
        strategy = test_result.metadata.get("strategy", self._config.generation.strategy.value)
        attack_type_dir = test_result.metadata.get(
            "attack_type_dir",
            generated_test.metadata.get("attack_type_dir", attack_type.value),
        )
        result_file = (
            Path(self._config.execution.output_dir)
            / "test_details"
            / strategy
            / generated_test.dataset
            / skill_name
            / attack_type_dir
            / f"iteration_{iteration_number}"
            / "result.json"
        )
        if not result_file.exists():
            logger.debug(f"[Result sync] Result file not found, skip sync: {result_file}")
            return

        data = json.loads(result_file.read_text(encoding="utf-8"))
        data["status"] = test_result.status.value
        data["blocked"] = test_result.blocked
        data["executed_malicious"] = test_result.executed_malicious
        data["detected_consequences"] = test_result.detected_consequences
        data["reasoning"] = test_result.reasoning
        data["error_type"] = test_result.error_type.value
        data["is_infrastructure_error"] = test_result.is_infrastructure_error
        if test_result.error_message:
            data["error_message"] = test_result.error_message

        existing_metadata = data.get("metadata", {})
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}

        metadata = dict(existing_metadata)
        metadata.update(test_result.metadata)

        metadata.pop("generation_adaptive_params", None)
        adaptive_params = metadata.get("adaptive_params")
        judge = metadata.pop("judge", None)
        response_classification = metadata.pop("response_classification", None)
        data["metadata"] = metadata

        if isinstance(judge, dict):
            judge = self._attach_adaptive_params_to_payload(judge, adaptive_params)
            data["judge"] = judge

        if isinstance(response_classification, dict):
            response_classification = self._attach_adaptive_params_to_payload(
                response_classification,
                adaptive_params,
            )
            data["response_classification"] = response_classification
            if "classification_failed" not in data["response_classification"]:
                nested_metadata = data["response_classification"].get("metadata", {})
                if isinstance(nested_metadata, dict) and "classification_failed" in nested_metadata:
                    data["response_classification"]["classification_failed"] = bool(
                        nested_metadata["classification_failed"]
                    )

        data.pop("final_verdict", None)
        if isinstance(judge, dict) and judge.get("verdict") == "attack_success":
            data["final_verdict"] = "attack_success"
        elif (
            isinstance(response_classification, dict)
            and response_classification.get("verdict")
            and not response_classification.get("classification_failed")
        ):
            data["final_verdict"] = str(response_classification["verdict"])
        elif data["executed_malicious"]:
            data["final_verdict"] = "attack_success"
        elif data["status"] == "error" or data["is_infrastructure_error"]:
            data["final_verdict"] = "technical"
        elif finalize_classification and self._config.judge is None:
            data["final_verdict"] = "rejected" if data["blocked"] else "ignored"

        classification_pending = False
        if self._config.judge is not None:
            if data.get("final_verdict") in {"attack_success", "rejected", "ignored", "technical"}:
                classification_pending = False
            else:
                classification_pending = True

        if classification_pending:
            data["classification_pending"] = True
        else:
            data.pop("classification_pending", None)

        logger.info(
            "[Result sync] %s/%s iteration_%s -> final_verdict=%s finalize_classification=%s",
            skill_name,
            attack_type.value,
            iteration_number,
            data.get("final_verdict"),
            finalize_classification,
        )

        result_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _build_iteration_adaptive_metadata(
        generation_adaptive_params: AdaptiveGenerationParams,
        *,
        failure_analysis: FailureAnalysis,
        previous_content: str,
    ) -> dict[str, Any]:
        """Build current-iteration adaptive metadata for a failed/non-success result."""
        metadata = generation_adaptive_params.to_dict()
        metadata["feedback_mode"] = failure_analysis.mode
        metadata["improvement_strategy"] = failure_analysis.improvement_strategy
        return metadata

    @staticmethod
    def _build_success_iteration_adaptive_metadata(
        generation_adaptive_params: AdaptiveGenerationParams,
    ) -> dict[str, Any]:
        """Build current-iteration adaptive metadata for a successful result."""
        metadata = generation_adaptive_params.to_dict()
        metadata["feedback_mode"] = "none"
        metadata["improvement_strategy"] = ""
        return metadata

    @staticmethod
    def _attach_adaptive_params_to_payload(
        payload: dict[str, Any],
        adaptive_params: Any,
    ) -> dict[str, Any]:
        """Attach iteration-local adaptive_params into top-level judge payload metadata."""
        if not isinstance(payload, dict) or not isinstance(adaptive_params, dict):
            return payload

        updated = dict(payload)
        nested_metadata = updated.get("metadata", {})
        if not isinstance(nested_metadata, dict):
            nested_metadata = {}
        else:
            nested_metadata = dict(nested_metadata)
        nested_metadata["adaptive_params"] = adaptive_params
        updated["metadata"] = nested_metadata
        return updated

    @staticmethod
    def _init_judge_service(config: TwoPhaseExecutionConfig) -> "LLMJudgeService | None":
        """Initialize the LLM judge service.

        Always creates the service when llm_judge config is present,
        since response classification (REJECTED vs IGNORED) always needs LLM.
        The attack_judgment flag controls whether LLM is used for attack-success
        detection, but does not affect response classification.
        """
        if config.judge is None:
            logger.warning(
                "[Streaming Orch] No llm_judge config found; "
                "response classification will be unavailable"
            )
            return None

        try:
            from src.domain.analysis.services.llm_judge_service import LLMJudgeService
            from src.infrastructure.llm.judge_client import LLMJudgeClient

            judge_client = LLMJudgeClient(config.judge)
            service = LLMJudgeService(judge_client, config.judge)
            logger.info(
                f"[Streaming Orch] LLM Judge initialized: "
                f"model={config.judge.model}, "
                f"attack_judgment={config.judge.attack_judgment}"
            )
            return service
        except Exception as e:
            logger.warning(
                f"[Streaming Orch] Failed to initialize LLM Judge: {e}"
            )
            return None

    async def execute_streaming(
        self,
        skill_names: list[str] | None = None,
        attack_types: list[AttackType] | None = None,
        progress_callback: Callable[[StreamingProgress], None] | None = None,
    ) -> StreamingResult:
        """Execute streaming test pipeline

        Workflow:
        1. Iterate through each skill (or execute multiple skill-attack pairs concurrently)
        2. Iterate through attack types for each skill
        3. Try various parameters for each combination
        4. Generate -> Execute -> Analyze -> Select next parameters

        Scheduling mode:
        - Different skill-attack pairs execute through one shared concurrent scheduler
        - When max_concurrency == 1, the scheduler degrades to single-worker execution
        - Iterations within a single skill-attack pair remain serial (feedback loop dependency)
        - Reuse execution.max_concurrency configuration from main.yaml

        Args:
            skill_names: List of skills to test, None means all
            attack_types: List of attack types to test, None means all
            progress_callback: Progress callback function

        Returns:
            Streaming processing result
        """
        # Load completed tests
        self._load_completed_tests()

        # Get skill list
        if skill_names is None:
            skill_names = self._get_all_skill_names()

        # Get attack type list
        # For DIRECT_EXECUTION strategy, skip attack_type dimension (one test per skill)
        strategy_value = self._config.generation.strategy.value
        is_direct_execution = strategy_value == "direct_execution"
        is_baseline = strategy_value == "baseline"
        if is_direct_execution:
            attack_types = [AttackType.DIRECT]  # Dummy placeholder for interface compatibility
            logger.info(
                f"[Streaming Orch] DIRECT_EXECUTION mode: processing {len(skill_names)} skills "
                f"(attack_type dimension skipped), concurrency: {self._max_concurrency}"
            )
        elif is_baseline:
            attack_types = [AttackType.BASELINE]  # No attack dimension
            logger.info(
                f"[Streaming Orch] BASELINE mode: processing {len(skill_names)} skills "
                f"(no attack detection), concurrency: {self._max_concurrency}"
            )
        elif attack_types is None:
            attack_types = AttackType.core_types()
            logger.info(
                f"[Streaming Orch] Starting processing {len(skill_names)} skills, "
                f"{len(attack_types)} attack types, "
                f"concurrency: {self._max_concurrency}"
            )
        else:
            logger.info(
                f"[Streaming Orch] Starting processing {len(skill_names)} skills, "
                f"{len(attack_types)} attack types, "
                f"concurrency: {self._max_concurrency}"
            )

        return await self._execute_streaming_concurrent(
            skill_names=skill_names,
            attack_types=attack_types,
            progress_callback=progress_callback,
        )

    async def _execute_streaming_concurrent(
        self,
        skill_names: list[str],
        attack_types: list[AttackType],
        progress_callback: Callable[[StreamingProgress], None] | None = None,
    ) -> StreamingResult:
        """Execute streaming test pipeline with a shared scheduler

        Execute at skill-attack pair level:
        - Each independent skill-attack pair can execute concurrently
        - When max_concurrency == 1, the scheduler runs with a single worker
        - Iterations within a single skill-attack pair remain serial (feedback loop requires it)
        - Use Semaphore to limit concurrency

        Args:
            skill_names: List of skills to test
            attack_types: List of attack types to test
            progress_callback: Progress callback function

        Returns:
            Streaming processing result
        """
        start_time = time.time()
        started_at = datetime.now()

        # Initialize progress
        progress = StreamingProgress()

        # Seed outcome counters from historical results so rates/counts include prior runs
        hist_success = len(self._success_tests)
        hist_blocked = len(self._blocked_tests)
        hist_ignored = len(self._ignored_tests)
        hist_determined = hist_success + hist_blocked + hist_ignored
        progress.total_success = hist_success
        progress.total_blocked = hist_blocked
        progress.total_ignored = hist_ignored
        progress.total_determined = hist_determined
        progress.total_executed = hist_determined  # historical test cases count as executed

        self._report_progress(progress, progress_callback)

        # Re-classify any pending tests (failed classifications from previous run)
        await self._reclassify_pending(progress)

        # Build all skill-attack pairs, filter completed tests
        skill_attack_pairs = [
            (s, at)
            for s in skill_names
            for at in attack_types
            if not self._is_test_completed(s, at.value)
        ]

        logger.info(
            f"[Streaming Orch] Shared scheduler: {len(skill_attack_pairs)} skill-attack pairs to execute "
            f"(concurrency={self._max_concurrency})"
        )

        if not skill_attack_pairs:
            logger.info("[Streaming Orch] All tests completed, no execution needed")
            if self._history_reused_tests:
                history_summary = ", ".join(
                    f"{test_id}@{details.get('iteration', 'unknown')}"
                    for test_id, details in sorted(self._history_reused_tests.items())
                )
                logger.info(
                    f"[Streaming Orch] Reused historical results without new execution: {history_summary}"
                )
            completed_at = datetime.now()

            # Use historical statistics
            total_success = len(self._success_tests)
            total_blocked = len(self._blocked_tests)
            total_ignored = len(self._ignored_tests)
            total_determined = total_success + total_blocked + total_ignored
            success_rate = total_success / total_determined if total_determined > 0 else 0.0
            block_rate = total_blocked / total_determined if total_determined > 0 else 0.0
            ignored_rate = total_ignored / total_determined if total_determined > 0 else 0.0

            return StreamingResult(
                total_generated=0,  # No new tests generated in this run
                total_executed=0,   # No new tests run in this run
                total_success=total_success,
                total_blocked=total_blocked,
                total_ignored=total_ignored,
                total_classification_failed=len(self._classification_failed_tests),
                total_determined=total_determined,
                success_rate=success_rate,
                block_rate=block_rate,
                ignored_rate=ignored_rate,
                success_tests=self._success_tests,
                blocked_tests=self._blocked_tests,
                ignored_tests=self._ignored_tests,
                classification_failed_tests=list(self._classification_failed_tests),
                execution_time_seconds=time.time() - start_time,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "max_attempts_per_test": self._max_attempts_per_test,
                    "stop_on_success": self._stop_on_success,
                    "concurrency": self._max_concurrency,
                    "execution_mode": "concurrent",
                    "all_from_history": True,  # Mark all results from history
                    "history_reused_tests": list(self._history_reused_tests.values()),
                },
            )

        # Create Semaphore and tasks
        semaphore = asyncio.Semaphore(self._max_concurrency)

        # Start all concurrent tasks
        tasks = [
            asyncio.create_task(
                self._execute_skill_attack_pair_concurrent(
                    skill_name=s,
                    attack_type=at,
                    semaphore=semaphore,
                    progress=progress,
                    progress_callback=progress_callback,
                )
            )
            for s, at in skill_attack_pairs
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                skill_name, attack_type = skill_attack_pairs[i]
                logger.error(f"[Streaming Orch] Task exception: {skill_name}/{attack_type.value}: {result}")

        # Completion processing
        completed_at = datetime.now()
        execution_time = time.time() - start_time

        # Collect skipped skills from generator
        generator_skipped: list[dict[str, str]] = []
        if hasattr(self._generator, "skipped_skills"):
            generator_skipped = [
                {"skill_name": s.skill_name, "attack_type": s.attack_type, "reason": s.reason}
                for s in self._generator.skipped_skills
            ]

        streaming_result = StreamingResult(
            total_generated=progress.total_generated,
            total_executed=progress.total_executed,
            total_success=progress.total_success,
            total_blocked=progress.total_blocked,
            total_ignored=progress.total_ignored,
            total_classification_failed=progress.total_classification_failed,
            total_determined=progress.total_determined,
            success_rate=progress.success_rate,
            block_rate=progress.block_rate,
            ignored_rate=progress.ignored_rate,
            success_tests=self._success_tests,
            blocked_tests=self._blocked_tests,
            ignored_tests=self._ignored_tests,
            classification_failed_tests=list(self._classification_failed_tests),
            execution_time_seconds=execution_time,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "max_attempts_per_test": self._max_attempts_per_test,
                "stop_on_success": self._stop_on_success,
                "concurrency": self._max_concurrency,
                "execution_mode": "concurrent",
            },
            skipped_skills=generator_skipped,
        )

        if generator_skipped:
            logger.info(
                "[Streaming Orch] Skipped %d skill(s) due to missing script mapping",
                len(generator_skipped),
            )
            for s in generator_skipped:
                logger.info(
                    "  %s (%s) — %s", s["skill_name"], s["attack_type"], s["reason"]
                )

        logger.info(
            f"[Streaming Orch] Concurrent processing complete, success rate: {streaming_result.success_rate:.1%}, "
            f"time: {execution_time:.1f}s"
        )

        return streaming_result

    async def _execute_skill_attack_pair_concurrent(
        self,
        skill_name: str,
        attack_type: AttackType,
        semaphore: asyncio.Semaphore,
        progress: StreamingProgress,
        progress_callback: Callable[[StreamingProgress], None] | None = None,
    ) -> None:
        """Execute a single skill-attack pair concurrently

        Use semaphore to limit concurrency, check early stop conditions before starting.

        Args:
            skill_name: Skill name
            attack_type: Attack type
            semaphore: Concurrency control semaphore
            progress: Progress object
            progress_callback: Progress callback
        """
        async with semaphore:
            # Initialize skill success state
            if skill_name not in self._skill_success:
                self._skill_success[skill_name] = set()

            # Check early stop condition (must check and decide within lock)
            should_skip = False
            async with self._early_stop_lock:
                if self._should_stop_early(skill_name, attack_type):
                    logger.info(
                        f"[Streaming Orch] Concurrent mode skip (early stop): {skill_name}/{attack_type.value}"
                    )
                    should_skip = True

            if should_skip:
                return

            # Execute feedback loop (pass lock for state updates)
            await self._execute_test_with_feedback_loop(
                skill_name=skill_name,
                attack_type=attack_type,
                progress=progress,
                progress_callback=progress_callback,
                early_stop_lock=self._early_stop_lock,
            )

    async def _execute_test_with_feedback_loop(
        self,
        skill_name: str,
        attack_type: AttackType,
        progress: StreamingProgress,
        progress_callback: Callable[[StreamingProgress], None] | None = None,
        early_stop_lock: asyncio.Lock | None = None,
    ) -> None:
        """Execute a single test using feedback loop

        Adaptive iteration generation process based on test results:
        1. Initial generation (default configuration)
        2. Execute test -> ConsequenceDetector detects consequences
        3. RuleBasedFailureAnalyzer analyzes failure patterns
        4. Determine: ESCAPED/BLOCKED/IGNORED/ATTEMPTED_FAILED
        5. ESCAPED -> Stop (attack successful)
        6. Others -> Build feedback Prompt -> LLM generates improved version
        7. Loop until success or max_attempts_per_test reached

        Key improvement: Count by test case, each skill × attack_type combination counts only once.
        Any iteration with executed_malicious=True means the test case is compromised.

        Args:
            skill_name: Skill name
            attack_type: Attack type
            progress: Progress object
            progress_callback: Progress callback
        """
        test_case_key = self._build_test_case_key(skill_name=skill_name, attack_type=attack_type.value)
        resume_state = self._resume_states.pop(test_case_key, None)
        if resume_state is not None:
            adaptive_params = resume_state["adaptive_params"]
            iteration_number = int(resume_state["iteration_number"])
            logger.info(
                "[Feedback Loop] Resuming %s/%s from iteration_%s",
                skill_name,
                attack_type.value,
                iteration_number,
            )
        else:
            adaptive_params = AdaptiveGenerationParams.create_initial()
            iteration_number = 0

        # For reading previous round's generated SKILL.md content
        previous_content = None
        # Consecutive failure counter: allow generation failures up to max_consecutive_failures times.
        consecutive_failures = 0
        max_consecutive_failures = 2
        had_non_infra_iteration = False
        is_baseline = attack_type == AttackType.BASELINE

        while iteration_number < self._max_attempts_per_test:
            # Update progress
            progress.current_skill = skill_name
            progress.current_attack_type = attack_type.value
            progress.current_params = adaptive_params.to_dict()
            progress.message = (
                f"Generating test (iteration {iteration_number + 1}/{self._max_attempts_per_test})"
            )
            self._report_progress(progress, progress_callback)

            # Generate test case (use feedback-driven generation method)
            # Pass base path without test_details, let generator build full path
            base_output_dir = Path(self._config.execution.output_dir)

            generated_test = await self._generator.generate_stream_with_feedback(
                skill_name=skill_name,
                attack_type=attack_type,
                adaptive_params=adaptive_params,
                output_dir=base_output_dir,
            )

            if isinstance(generated_test, RefusedResult):
                # Build refusal message for screen output
                refusal_msg = (
                    f"\n{'=' * 60}\n"
                    f"[{generated_test.skill_name}/{generated_test.attack_type}] LLM Refused Generation\n"
                    f"{'=' * 60}\n"
                    f"  Reason: {generated_test.reason}\n"
                    f"{'=' * 60}\n"
                )
                print(refusal_msg)  # Output directly to screen
                logger.info(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"LLM refused generation, skipping this skill/attack_type combination"
                )
                # Refuse generation breaks out of feedback loop, continue to next attack_type
                break

            if generated_test is None:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(
                        f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                        f"LLM call failed {consecutive_failures} times consecutively, skipping this skill/attack_type combination"
                    )
                    break
                logger.info(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"LLM call failed ({consecutive_failures}/{max_consecutive_failures}), retrying..."
                )
                iteration_number += 1
                continue

            # Verify payload_content is non-empty (last line of defense)
            if not generated_test.payload_content or not generated_test.payload_content.strip():
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(
                        f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                        f"Generated content empty {consecutive_failures} times consecutively, skipping this skill/attack_type combination"
                    )
                    break
                logger.warning(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"Generated test case payload_content empty ({consecutive_failures}/{max_consecutive_failures}), retrying..."
                )
                iteration_number += 1
                continue

            # Generation successful, reset consecutive failure counter
            consecutive_failures = 0

            progress.total_generated += 1
            self._report_progress(progress, progress_callback)

            # Execute test
            progress.message = (
                f"Executing test (iteration {iteration_number + 1}/{self._max_attempts_per_test})"
            )
            self._report_progress(progress, progress_callback)

            if self._judge_service is not None:
                test_result = await self._execute_single_test(
                    generated_test,
                    iteration_number=iteration_number,
                    save_logs=False,
                )
            else:
                test_result = await self._execute_single_test(
                    generated_test,
                    iteration_number=iteration_number,
                )

            progress.total_executed += 1
            self._report_progress(progress, progress_callback)

            # Handle all infrastructure errors (timeout, network, agent API 429, etc.):
            # retry without incrementing iteration_number, with exponential backoff.
            if test_result.is_infrastructure_error:
                retry_count = self._infra_retry_counts.get(test_case_key, 0) + 1
                self._infra_retry_counts[test_case_key] = retry_count

                if retry_count < self._infra_retry_cfg.max_attempts:
                    delay = self._infra_retry_cfg.get_delay(retry_count)
                    logger.warning(
                        f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                        f"Infrastructure error ({test_result.error_type.value}), "
                        f"retry {retry_count}/{self._infra_retry_cfg.max_attempts - 1} "
                        f"without incrementing iteration, waiting {delay:.0f}s"
                    )
                    await asyncio.sleep(delay)
                    continue  # Do NOT increment iteration_number
                else:
                    logger.warning(
                        f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                        f"Infrastructure error persisted after {self._infra_retry_cfg.max_attempts - 1} retries, "
                        f"skipping test case entirely"
                    )
                    if self._config.judge is not None:
                        await self._save_finalized_test_detail(
                            generated_test=generated_test,
                            test_result=test_result,
                            iteration_number=iteration_number,
                        )
                    break  # Falls into "all infrastructure errors" path

            executed_malicious = test_result.executed_malicious
            had_non_infra_iteration = True

            # Baseline mode: skip all attack detection and classification
            # Just record the result and move on
            if is_baseline:
                test_result.metadata["adaptive_params"] = (
                    self._build_success_iteration_adaptive_metadata(adaptive_params)
                )
                await self._save_finalized_test_detail(
                    generated_test=generated_test,
                    test_result=test_result,
                    iteration_number=iteration_number,
                )
                async with self._progress_lock:
                    progress.total_determined += 1
                logger.info(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"Baseline execution completed at iteration_{iteration_number}"
                )
                break

            # LLM-as-Judge for attack-success evaluation (only when attack_judgment is enabled)
            if self._judge_service and not executed_malicious and self._judge_config_attack_judgment:
                try:
                    judge_result = await self._judge_service.evaluate_injection(
                        test_result, generated_test
                    )
                    self._record_result_metadata(test_result, judge_result=judge_result)
                    # Judge can upgrade verdict: rule-based missed but LLM detected attack
                    if judge_result.is_attack_success:
                        executed_malicious = True
                        test_result.mark_executed(reasoning=judge_result.reasoning or judge_result.evidence)
                        test_result.metadata["judge_upgrade"] = True
                        test_result.metadata["judge_evidence"] = judge_result.evidence
                        logger.info(
                            f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                            f"LLM Judge upgraded verdict to ATTACK_SUCCESS"
                        )
                    else:
                        logger.debug(
                            f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                            f"LLM Judge verdict: {judge_result.verdict.value}"
                        )
                except Exception as e:
                    logger.warning(
                        f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                        f"LLM Judge evaluation failed: {e}"
                    )
            classification = "attack_success" if executed_malicious else "classification_failed"
            if not executed_malicious:
                if self._judge_service:
                    logger.info(
                        "[Feedback Loop] %s/%s: Starting response classification for iteration_%s",
                        skill_name,
                        attack_type.value,
                        iteration_number,
                    )
                    classification, judge_result = await self._classify_response(
                        agent_output=test_result.agent_output or "",
                        skill_name=skill_name,
                        attack_type=attack_type.value,
                    )
                    logger.info(
                        "[Feedback Loop] %s/%s: Response classification completed -> %s",
                        skill_name,
                        attack_type.value,
                        classification,
                    )
                    self._record_result_metadata(
                        test_result,
                        response_classification=judge_result,
                    )
                    if classification == "rejected":
                        test_result.mark_blocked(judge_result.reasoning or judge_result.evidence)
                    elif classification == "ignored":
                        test_result.blocked = False
                        test_result.executed_malicious = False
                        test_result.detected_threat = False
                        test_result.status = TestStatus.PASSED
                        test_result.reasoning = judge_result.reasoning or judge_result.evidence or test_result.reasoning
                else:
                    classification = "ignored"

            # Use failure analyzer on finalized per-iteration result
            failure_analysis = analyze_failure(test_result)

            if executed_malicious:
                test_result.metadata["adaptive_params"] = (
                    self._build_success_iteration_adaptive_metadata(adaptive_params)
                )
            else:
                current_adaptive_params_for_result = StreamingOrchestrator._build_iteration_adaptive_metadata(
                    adaptive_params,
                    failure_analysis=failure_analysis,
                    previous_content=generated_test.payload_content,
                )
                test_result.metadata["adaptive_params"] = current_adaptive_params_for_result

            if self._judge_service is not None:
                await self._save_finalized_test_detail(
                    generated_test=generated_test,
                    test_result=test_result,
                    iteration_number=iteration_number,
                )
            else:
                self._persist_result_json_update(
                    generated_test=generated_test,
                    skill_name=skill_name,
                    attack_type=attack_type,
                    iteration_number=iteration_number,
                    test_result=test_result,
                    finalize_classification=True,
                )

            # Count attack success immediately and stop further iterations for this test case.
            if executed_malicious:
                async with self._progress_lock:
                    progress.total_success += 1
                    progress.total_determined += 1
                    self._success_tests.append(test_case_key)
                if early_stop_lock:
                    async with early_stop_lock:
                        self._skill_success[skill_name].add(attack_type.value)
                else:
                    self._skill_success[skill_name].add(attack_type.value)
                logger.info(f"[Feedback Loop] {skill_name}/{attack_type.value}: Attack succeeded, stopping iteration")
                break

            if classification == "classification_failed":
                async with self._progress_lock:
                    progress.total_classification_failed += 1
                    self._classification_failed_tests.append(test_case_key)
                logger.warning(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"Response classification failed for iteration_{iteration_number}"
                )
            elif (iteration_number + 1) >= self._max_attempts_per_test:
                async with self._progress_lock:
                    progress.total_determined += 1
                    if classification == "rejected":
                        progress.total_blocked += 1
                        self._blocked_tests.append(test_case_key)
                    else:
                        progress.total_ignored += 1
                        self._ignored_tests.append(test_case_key)
                logger.info(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"Case completed at iteration_{iteration_number} with verdict {classification}"
                )
                break

            # Prepare next iteration: read previous round's generated SKILL.md content
            previous_content = generated_test.payload_content  # noqa: F841

            # Create next round's adaptive parameters
            adaptive_params = adaptive_params.create_next(
                feedback=failure_analysis,
                previous_content=generated_test.payload_content,
            )

            # Increment iteration number
            iteration_number += 1

            # Log if max attempts reached
            if iteration_number >= self._max_attempts_per_test:
                logger.info(
                    f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                    f"Reached maximum attempts {self._max_attempts_per_test}"
                )

        if not had_non_infra_iteration:
            logger.info(
                f"[Feedback Loop] {skill_name}/{attack_type.value}: "
                "All iterations were infrastructure errors, skipping from statistics"
            )

    async def _classify_response(
        self,
        agent_output: str,
        skill_name: str,
        attack_type: str,
    ) -> tuple[str, Any]:
        """Classify non-attack response as REJECTED or IGNORED via LLM.

        Args:
            agent_output: The agent's response text.
            skill_name: Skill name for logging.
            attack_type: Attack type string for logging.

        Returns:
            Tuple of (classification, judge_result).
            classification is one of: "rejected", "ignored", "classification_failed"
        """
        from src.domain.analysis.interfaces.i_llm_judge import LLMJudgeVerdict

        if not self._judge_service:
            logger.warning(
                f"[Response Classifier] {skill_name}/{attack_type}: "
                "No judge service available, classifying as classification_failed"
            )
            return "classification_failed", None

        try:
            result = await self._judge_service.classify_response(
                agent_output=agent_output,
                test_id=f"{skill_name}/{attack_type}",
            )
        except Exception as e:
            logger.error(
                f"[Response Classifier] {skill_name}/{attack_type}: "
                f"Unexpected error: {e}"
            )
            return "classification_failed", None

        if result.verdict == LLMJudgeVerdict.REJECTED:
            return "rejected", result
        elif result.verdict == LLMJudgeVerdict.IGNORED:
            return "ignored", result
        elif result.metadata.get("classification_failed"):
            return "classification_failed", result
        else:
            # Unexpected verdict from response classifier (e.g. TECHNICAL without classification_failed)
            logger.warning(
                f"[Response Classifier] {skill_name}/{attack_type}: "
                f"Unexpected verdict {result.verdict.value}, treating as classification_failed"
            )
            return "classification_failed", result

    def _load_existing_failure(self, test_id: str) -> dict | None:
        """Load existing failure result for a test case

        Scans the test_details directory to find if this test has a previous
        failure with needs_retry=True (infrastructure error that should be retried).

        Args:
            test_id: Test case ID

        Returns:
            Existing failure result dict if found, None otherwise
        """
        import json

        test_details_dir = Path(self._config.execution.output_dir) / "test_details"
        if not test_details_dir.exists():
            return None

        # Search for result.json files matching this test_id
        # Directory structure: test_details/{strategy}/{dataset}/{skill_name}/{attack_type}/iteration_{N}/
        for result_file in test_details_dir.rglob("result.json"):
            try:
                with open(result_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)

                # Check if this is the same test
                if data.get("test_id") != test_id:
                    continue

                # Check if it's a failure that needs retry
                retry_trace = data.get("metadata", {}).get("retry_trace", {})
                if (
                    data.get("is_infrastructure_error")
                    and isinstance(retry_trace, dict)
                    and retry_trace.get("final_outcome") == "exhausted"
                ):
                    logger.info(
                        f"[Retry] Found existing failure for {test_id} at {result_file}, "
                        f"outcome={retry_trace.get('final_outcome')}"
                    )
                    return data

            except Exception as e:
                logger.warning(f"[Retry] Failed to read existing result {result_file}: {e}")
                continue

        return None

    async def _execute_single_test(
        self,
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
        *,
        save_logs: bool = True,
    ) -> TestResult:
        """Execute a single test

        Args:
            generated_test: Generated test case
            iteration_number: Iteration number, for building iteration_{N} directory
            save_logs: Whether the test runner should persist logs immediately

        Returns:
            Test result
        """
        test_case, skill_dir = self._build_runtime_test_case(
            generated_test=generated_test,
            iteration_number=iteration_number,
        )

        # Execute test
        # Note: skill_dir kept for compatibility, but no longer used to save injected_skill directory
        # (generator has saved SKILL.md and resources to test_case_dir)
        # Cross-run retry: only scan for previous exhausted failures when retry is enabled.
        # This keeps `retry_failed` as the single control for all retry behavior.
        existing_failure = (
            self._load_existing_failure(generated_test.test_id)
            if self._config.execution.retry_failed
            else None
        )
        if existing_failure is not None:
            # Found an existing failure - retry without saving logs to avoid duplicate failed logs
            logger.info(
                f"[Retry] Retrying existing failure for {generated_test.test_id}, "
                f"previous outcome={existing_failure.get('metadata', {}).get('retry_trace', {}).get('final_outcome')}"
            )
            retry_result = await self._test_runner._run_test_async(
                test_case,
                iteration_number=iteration_number,
                skill_dir=skill_dir,
                save_logs=False,  # Don't save failed logs again
            )

            # If retry succeeded, update the existing result.json
            if not retry_result.is_infrastructure_error:
                logger.info(f"[Retry] Retry succeeded for {generated_test.test_id}, updating result.json")
                # Update existing result with new successful result
                import json

                existing_result_path = test_case.test_case_dir / "result.json"
                if existing_result_path.exists():
                    existing_data = json.loads(existing_result_path.read_text(encoding="utf-8"))
                    # Merge retry trace into existing result
                    existing_data["status"] = retry_result.status.value
                    existing_data["executed_malicious"] = retry_result.executed_malicious
                    existing_data["detected_consequences"] = retry_result.detected_consequences
                    existing_data["reasoning"] = retry_result.reasoning
                    existing_data["is_infrastructure_error"] = False
                    existing_data["error_type"] = ""
                    existing_data["error_message"] = ""
                    existing_metadata = existing_data.get("metadata", {})
                    if isinstance(existing_metadata, dict):
                        existing_metadata.pop("generation_adaptive_params", None)
                        existing_metadata.pop("retry_info", None)
                    retry_trace = retry_result.metadata.get("retry_trace", {})
                    if isinstance(retry_trace, dict):
                        retry_trace = dict(retry_trace)
                        retry_trace["replaced_failure"] = True
                        existing_data["metadata"]["retry_trace"] = retry_trace
                    existing_result_path.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")
                    logger.info(f"[Retry] Updated existing result at {existing_result_path}")

            return retry_result

        if save_logs:
            result = await self._test_runner._run_test_async(
                test_case,
                iteration_number=iteration_number,
                skill_dir=skill_dir,
            )
        else:
            result = await self._test_runner._run_test_async(
                test_case,
                iteration_number=iteration_number,
                skill_dir=skill_dir,
                save_logs=False,
            )

        return result

    def _build_runtime_test_case(
        self,
        *,
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
    ) -> tuple[TestCase, Path | None]:
        """Build the runtime TestCase and local skill_dir for a generated test."""
        # Extract skill_name: prefer from metadata, otherwise parse from test_id
        # test_id format: {skill_name}_{attack_type}
        skill_name = generated_test.metadata.get("skill_name")
        if not skill_name:
            # Parse from test_id: remove attack type suffix
            test_id_parts = generated_test.test_id.rsplit("_", 1)
            skill_name = test_id_parts[0] if len(test_id_parts) > 1 else generated_test.test_id

        # Build test_case_dir consistent with generator save path (supports iteration_N)
        # Generator save path: test_details/{strategy}/{dataset}/{skill_name}/{attack_type}/iteration_{N}/
        # For direct_execution mode, attack_type is "direct" (used in path but not a real AttackType)
        # For baseline mode, attack_type is "baseline"
        strategy = self._config.generation.strategy.value
        dataset = generated_test.dataset
        is_direct_execution = strategy == "direct_execution"
        is_baseline = strategy == "baseline"
        attack_type_dir = "direct" if is_direct_execution else ("baseline" if is_baseline else generated_test.attack_type)
        test_case_dir = (
            Path(self._config.execution.output_dir)
            / "test_details"
            / strategy
            / dataset
            / skill_name
            / attack_type_dir
            / f"iteration_{iteration_number}"
        )

        # Ensure directory exists (before creating TestCase)
        test_case_dir.mkdir(parents=True, exist_ok=True)

        # For direct_execution/baseline, keep instruction.md as a local snapshot in test_case_dir.
        # Skill files are no longer pre-copied here; container skill snapshot is sourced from source_skill_dir.
        if is_direct_execution or is_baseline:
            instruction_content = generated_test.payload_content
            instruction_dest = test_case_dir / "instruction.md"
            instruction_dest.write_text(instruction_content, encoding="utf-8")
            logger.debug(f"[{strategy}] Saved instruction.md snapshot to {test_case_dir}")

        # Convert to TestCase
        # For direct_execution, keep semantic attack type as DIRECT.
        # For baseline, use BASELINE sentinel.
        if is_direct_execution:
            test_attack_type = AttackType.DIRECT
        elif is_baseline:
            test_attack_type = AttackType.BASELINE
        else:
            test_attack_type = AttackType(generated_test.attack_type)

        test_metadata = dict(generated_test.metadata)
        test_metadata["attack_type_dir"] = attack_type_dir

        test_case = TestCase(
            id=TestCaseId(generated_test.test_id),
            skill_name=skill_name,
            layer=InjectionLayer(generated_test.injection_layer),
            attack_type=test_attack_type,
            payload_name=strategy,
            severity=Severity(generated_test.severity),
            skill_path=Path(generated_test.skill_path),
            test_case_dir=test_case_dir,
            source_skill_dir=(
                Path(generated_test.source_skill_dir) if generated_test.source_skill_dir else None
            ),
            source_aux_dir=(
                Path(generated_test.source_aux_dir) if generated_test.source_aux_dir else None
            ),
            dataset=generated_test.dataset,
            should_be_blocked=generated_test.should_be_blocked,
            injected_resource_file=generated_test.injected_resource_file,
            injection_points=generated_test.injection_points,
            metadata=test_metadata,
            payload_content=generated_test.payload_content,
        )

        # Execute test
        # Note: skill_dir kept for compatibility, but no longer used to save injected_skill directory
        # (generator has saved SKILL.md and resources to test_case_dir)
        skill_dir = (
            test_case.test_case_dir
            if test_case.test_case_dir and test_case.test_case_dir.exists()
            else None
        )
        return test_case, skill_dir

    async def _save_finalized_test_detail(
        self,
        *,
        generated_test: GeneratedTestCase,
        test_result: TestResult,
        iteration_number: int,
    ) -> None:
        """Persist a finalized single-attempt result after judge classification."""
        save_detail = getattr(self._test_runner, "save_test_detail", None)
        if not callable(save_detail):
            return

        test_case, skill_dir = self._build_runtime_test_case(
            generated_test=generated_test,
            iteration_number=iteration_number,
        )
        await save_detail(
            test_case=test_case,
            result=test_result,
            iteration_number=iteration_number,
            skill_dir=skill_dir,
        )

    def _should_stop_early(self, skill_name: str, attack_type: AttackType) -> bool:
        """Check if should stop early

        Args:
            skill_name: Skill name
            attack_type: Attack type

        Returns:
            Whether to stop early
        """
        # Skill-level early stop: this skill has already succeeded on this attack type
        if skill_name in self._skill_success:
            if attack_type.value in self._skill_success[skill_name]:
                return True

        return False

    def _should_stop_globally(self) -> bool:
        """Check if should stop globally

        Returns:
            Whether to stop globally
        """
        return False

    @staticmethod
    def _build_test_case_key(skill_name: str, attack_type: str) -> str:
        """Build normalized test-case key for aggregation."""
        return f"{skill_name}_{attack_type}"

    def _load_iteration_previous_content(self, result_file: Path) -> str | None:
        """Load one iteration's effective SKILL.md content for resume."""
        candidate_paths = [
            result_file.parent / "skill" / "SKILL.md",
            result_file.parent / "SKILL.md",
        ]
        for path in candidate_paths:
            if path.exists() and path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except OSError:
                    continue
        return None

    def _find_resume_anchor(
        self,
        *,
        result_file: Path,
        data: dict[str, Any],
        iteration_number: int,
    ) -> tuple[Path, dict[str, Any], int, str] | None:
        """Find the latest finalized iteration with enough artifacts to resume from."""
        current_result_file = result_file
        current_data = data
        current_iteration = iteration_number

        while current_iteration >= 0:
            previous_content = self._load_iteration_previous_content(current_result_file)
            if previous_content is not None:
                return current_result_file, current_data, current_iteration, previous_content

            fallback_iteration = current_iteration - 1
            if fallback_iteration < 0:
                return None

            fallback_dir = current_result_file.parent.parent / f"iteration_{fallback_iteration}"
            fallback_result_file = fallback_dir / "result.json"
            if not fallback_result_file.exists():
                return None

            try:
                fallback_data = json.loads(fallback_result_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None

            logger.info(
                "[Incremental Test] Resume artifact missing for iteration_%s, fallback to iteration_%s",
                current_iteration,
                fallback_iteration,
            )
            current_result_file = fallback_result_file
            current_data = fallback_data
            current_iteration = fallback_iteration

    def _build_resume_state_from_result(
        self,
        *,
        test_id: str,
        result_file: Path,
        data: dict[str, Any],
        iteration_number: int,
    ) -> dict[str, Any] | None:
        """Reconstruct next-iteration adaptive state from a finalized iteration result."""
        anchor = self._find_resume_anchor(
            result_file=result_file,
            data=data,
            iteration_number=iteration_number,
        )
        if anchor is None:
            return None

        anchor_result_file, anchor_data, anchor_iteration, previous_content = anchor

        final_verdict = str(anchor_data.get("final_verdict") or "")
        if final_verdict not in {"rejected", "ignored"}:
            return None
        if (anchor_iteration + 1) >= self._max_attempts_per_test:
            return None

        response_classification = anchor_data.get("response_classification", {})
        metadata = anchor_data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        test_result = TestResult(
            test_id=TestCaseId(test_id),
            status=TestStatus(anchor_data.get("status", TestStatus.PASSED.value)),
            agent_output=str(anchor_data.get("agent_output", "")),
            blocked=bool(anchor_data.get("blocked", False)),
            executed_malicious=bool(anchor_data.get("executed_malicious", False)),
            detected_consequences=list(anchor_data.get("detected_consequences", [])),
            reasoning=str(anchor_data.get("reasoning", "")),
            metadata={
                **metadata,
                "response_classification": response_classification,
            },
        )
        failure_analysis = analyze_failure(test_result)
        adaptive_params = AdaptiveGenerationParams(
            feedback=failure_analysis,
            previous_content=previous_content,
            iteration_number=anchor_iteration + 1,
        )
        return {
            "iteration_number": anchor_iteration + 1,
            "adaptive_params": adaptive_params,
            "result_file": str(anchor_result_file),
            "final_verdict": final_verdict,
        }

    def _load_completed_tests(self) -> None:
        """Load completed test cases from existing results and count results

        Only load truly completed tests (non-infrastructure errors).

        Directory structure: test_details/{strategy}/{dataset}/{skill_name}/{attack_type}/iteration_*/result.json
        """
        import json

        # Use test_details directory instead of computed_output_dir
        test_details_dir = Path(self._config.execution.output_dir) / "test_details"
        if not test_details_dir.exists():
            logger.info(f"[Incremental Test] test_details directory does not exist: {test_details_dir}")
            return

        self._history_reused_tests = {}
        self._resume_states = {}

        # Iterate through strategy subdirectories (like skillject)
        current_strategy = self._config.generation.strategy.value
        # Define infrastructure error types
        infra_errors = {
            "execd_crash", "timeout", "network_error",
            "container_error", "sandbox_not_available",
            "agent_api_error",
        }

        for strategy_dir in test_details_dir.iterdir():
            if not strategy_dir.is_dir():
                continue

            # FIX: Only process current strategy results, avoid test results from different strategies interfering
            if strategy_dir.name != current_strategy:
                logger.debug(
                    f"[Incremental Test] Skipping other strategy results: {strategy_dir.name} "
                    f"(current strategy: {current_strategy})"
                )
                continue

            # Iterate through dataset subdirectories (like skills_from_skill0)
            current_dataset = self._config.generation.dataset.name
            for dataset_dir in strategy_dir.iterdir():
                if not dataset_dir.is_dir():
                    continue
                if dataset_dir.name != current_dataset:
                    logger.debug(
                        f"[Incremental Test] Skipping other dataset results: {dataset_dir.name} "
                        f"(current dataset: {current_dataset})"
                    )
                    continue

                # Iterate through skill_name subdirectories
                for skill_dir in dataset_dir.iterdir():
                    if not skill_dir.is_dir():
                        continue
                    skill_name = skill_dir.name

                    # Iterate through attack_type subdirectories
                    for attack_dir in skill_dir.iterdir():
                        if not attack_dir.is_dir():
                            continue
                        attack_type = attack_dir.name

                        # Find latest result.json file
                        result_file = self._find_latest_result_json(attack_dir)
                        if result_file is None:
                            continue

                        # Read results and count
                        try:
                            with open(result_file) as f:
                                data = json.load(f)
                                status = data.get("status")
                                error_type = data.get("error_type")
                                test_id = self._build_test_case_key(skill_name=skill_name, attack_type=attack_type)
                                executed_malicious = data.get("executed_malicious", False)
                                blocked = data.get("blocked", False)
                                iteration_name = result_file.parent.name
                                iteration_number = None
                                if iteration_name.startswith("iteration_"):
                                    try:
                                        iteration_number = int(iteration_name.split("_")[1])
                                    except ValueError:
                                        iteration_number = None

                                # Skip infrastructure errors (need retry)
                                if data.get("is_infrastructure_error") or (
                                    status == "error" and error_type in infra_errors
                                ):
                                    logger.info(
                                        f"[Incremental Test] Skipping infrastructure error (will retry): {test_id}, "
                                        f"error_type={error_type}"
                                    )
                                    continue

                                # Handle classification failures: queue for re-classification (no container re-run)
                                response_classification = data.get("response_classification", {})
                                if response_classification.get("classification_failed"):
                                    logger.info(
                                        f"[Incremental Test] Found classification failure (will re-classify): {test_id}"
                                    )
                                    self._pending_reclassification[test_id] = {
                                        "test_id": test_id,
                                        "skill_name": skill_name,
                                        "attack_type": attack_type,
                                        "agent_output": data.get("agent_output", ""),
                                        "result_file": str(result_file),
                                        "data": data,
                                    }
                                    continue

                                has_final_verdict = bool(data.get("final_verdict"))
                                has_response_classification = bool(
                                    isinstance(response_classification, dict)
                                    and response_classification.get("verdict")
                                )
                                classification_pending = bool(data.get("classification_pending"))
                                legacy_unclassified = (
                                    self._judge_service is not None
                                    and not has_final_verdict
                                    and not has_response_classification
                                    and not executed_malicious
                                    and not blocked
                                )
                                if classification_pending or legacy_unclassified:
                                    logger.info(
                                        f"[Incremental Test] Found pending classification "
                                        f"(will re-classify): {test_id}"
                                    )
                                    self._pending_reclassification[test_id] = {
                                        "test_id": test_id,
                                        "skill_name": skill_name,
                                        "attack_type": attack_type,
                                        "agent_output": data.get("agent_output", ""),
                                        "result_file": str(result_file),
                                        "data": data,
                                    }
                                    continue

                                resume_state = None
                                if iteration_number is not None:
                                    resume_state = self._build_resume_state_from_result(
                                        test_id=test_id,
                                        result_file=result_file,
                                        data=data,
                                        iteration_number=iteration_number,
                                    )
                                if resume_state is not None:
                                    self._resume_states[test_id] = resume_state
                                    logger.info(
                                        f"[Incremental Test] Found resumable case: {test_id}, "
                                        f"next_iteration=iteration_{resume_state['iteration_number']}"
                                    )
                                    continue

                                # Record as completed (for skipping)
                                if skill_name not in self._completed_tests:
                                    self._completed_tests[skill_name] = set()
                                self._completed_tests[skill_name].add(attack_type)

                                # Count historical results (three-way classification)
                                if executed_malicious:
                                    self._success_tests.append(test_id)
                                elif blocked:
                                    self._blocked_tests.append(test_id)
                                else:
                                    self._ignored_tests.append(test_id)

                                self._history_reused_tests[test_id] = {
                                    "test_id": test_id,
                                    "status": status,
                                    "executed_malicious": executed_malicious,
                                    "blocked": blocked,
                                    "iteration": iteration_name,
                                    "iteration_number": iteration_number,
                                    "timestamp": data.get("timestamp"),
                                    "result_file": str(result_file),
                                }

                                logger.info(
                                    f"[Incremental Test] Loaded historical result: {test_id}, "
                                    f"status={status}, executed_malicious={executed_malicious}, blocked={blocked}, "
                                    f"reused_from={iteration_name}"
                                )
                        except Exception as e:
                            logger.warning(f"[Incremental Test] Failed to read result: {result_file}, {e}")

        # Add statistics log
        total_skipped = sum(len(attacks) for attacks in self._completed_tests.values())
        logger.info(
            f"[Incremental Test] Loaded {len(self._completed_tests)} skills' {total_skipped} completed tests, "
            f"historical results: {len(self._success_tests)} success, {len(self._blocked_tests)} rejected, {len(self._ignored_tests)} ignored, "
            f"pending reclassification: {len(self._pending_reclassification)}"
        )

    async def _reclassify_pending(self, progress: StreamingProgress) -> None:
        """Re-classify pending tests without re-running containers.

        For tests where response classification previously failed, this method
        loads existing agent_output and retries the LLM classification only.
        """
        if not self._pending_reclassification:
            return

        if not self._judge_service:
            logger.warning(
                "[Reclassify] No judge service available, "
                f"skipping {len(self._pending_reclassification)} pending reclassifications"
            )
            for test_id in self._pending_reclassification:
                self._classification_failed_tests.append(test_id)
                progress.total_classification_failed += 1
            self._pending_reclassification.clear()
            return

        logger.info(
            f"[Reclassify] Starting re-classification for {len(self._pending_reclassification)} tests"
        )

        for test_id, pending in list(self._pending_reclassification.items()):
            skill_name = pending["skill_name"]
            attack_type = pending["attack_type"]

            classification, judge_result = await self._classify_response(
                agent_output=pending["agent_output"],
                skill_name=skill_name,
                attack_type=attack_type,
            )

            if classification in ("rejected", "ignored"):
                iteration_number = None
                # Persist verdict back to result.json
                result_file_str = pending.get("result_file")
                result_file = Path(result_file_str) if result_file_str else None
                if result_file is not None and result_file.exists():
                    file_data = json.loads(result_file.read_text(encoding="utf-8"))
                    file_data["final_verdict"] = classification
                    file_data.pop("classification_pending", None)
                    serialized = self._serialize_judge_result(judge_result)
                    if serialized is not None:
                        file_data["response_classification"] = serialized
                    result_file.write_text(
                        json.dumps(file_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )

                    iteration_name = result_file.parent.name
                    if iteration_name.startswith("iteration_"):
                        try:
                            iteration_number = int(iteration_name.split("_")[1])
                        except ValueError:
                            iteration_number = None

                    resume_state = None
                    if iteration_number is not None:
                        resume_state = self._build_resume_state_from_result(
                            test_id=test_id,
                            result_file=result_file,
                            data=file_data,
                            iteration_number=iteration_number,
                        )
                    if resume_state is not None:
                        self._resume_states[test_id] = resume_state
                if result_file is None or not result_file.exists() or resume_state is None:
                    async with self._progress_lock:
                        if classification == "rejected":
                            progress.total_blocked += 1
                            self._blocked_tests.append(test_id)
                        else:
                            progress.total_ignored += 1
                            self._ignored_tests.append(test_id)
                        progress.total_determined += 1
                    if skill_name not in self._completed_tests:
                        self._completed_tests[skill_name] = set()
                    self._completed_tests[skill_name].add(attack_type)

                logger.info(
                    f"[Reclassify] {test_id}: Reclassified as {classification}"
                )
            else:
                # Still failed — only log, don't write verdict
                async with self._progress_lock:
                    progress.total_classification_failed += 1
                    self._classification_failed_tests.append(test_id)
                logger.warning(
                    f"[Reclassify] {test_id}: Classification failed again"
                )

        self._pending_reclassification.clear()

    def _find_latest_result_json(self, attack_dir: Path) -> Path | None:
        """Find the latest result.json file in the specified attack directory

        Args:
            attack_dir: Attack type directory (like information_disclosure)

        Returns:
            Path to result.json in the latest iteration directory, or None if not exists
        """
        # Find iteration_* directories with largest number
        iteration_dirs = [
            d for d in attack_dir.iterdir()
            if d.is_dir() and d.name.startswith("iteration_")
        ]
        if not iteration_dirs:
            return None

        # Sort by iteration number, take largest
        iteration_dirs.sort(key=lambda d: int(d.name.split("_")[1]))
        latest_dir = iteration_dirs[-1]
        result_file = latest_dir / "result.json"

        return result_file if result_file.exists() else None

    def _is_test_completed(self, skill_name: str, attack_type: str) -> bool:
        """Check if test is completed

        Args:
            skill_name: Skill name
            attack_type: Attack type

        Returns:
            Whether completed
        """
        if skill_name in self._completed_tests:
            return attack_type in self._completed_tests[skill_name]
        return False

    def _get_all_skill_names(self) -> list[str]:
        """Get all skill names.

        Delegates to the generator's list_skill_names() so each strategy
        controls its own skill source.

        Returns:
            List of skill names
        """
        return self._generator.list_skill_names()

    def _report_progress(
        self,
        progress: StreamingProgress,
        callback: Callable[[StreamingProgress], None] | None = None,
    ) -> None:
        """Report progress

        Args:
            progress: Progress object
            callback: Callback function
        """
        if callback:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"[Progress Report] Callback failed: {e}")

    async def cleanup(self) -> None:
        """Clean up resources"""
        await self._test_runner.cleanup()


__all__ = [
    "StreamingProgress",
    "StreamingResult",
    "StreamingOrchestrator",
]
