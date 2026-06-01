import asyncio
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.application.services.streaming_orchestrator import (
    StreamingOrchestrator,
    StreamingProgress,
    StreamingResult,
)
from src.domain.analysis.interfaces.i_llm_judge import (
    LLMJudgeResult,
    LLMJudgeVerdict,
)
from src.domain.analysis.services.verdict_resolver import FailureAnalysis
from src.domain.generation.entities.test_suite import GeneratedTestCase
from src.domain.generation.services.adaptive_params import AdaptiveGenerationParams
from src.domain.testing.entities.test_case import (
    TestCaseId,
)
from src.domain.testing.entities.test_case import (
    TestResult as ExecutionTestResult,
)
from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig
from src.shared.types import AttackType


def _build_config() -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                    "base_dir": "data/skill_inject",
                },
                "skill_names": ["INST-10_git_task0"],
                "attack_types": ["information_disclosure"],
            },
            "execution": {
                "max_concurrency": 1,
                "output_dir": "experiment_results_test",
                "sandbox": {
                    "domain": "localhost:8080",
                    "image": "claude_code:latest",
                },
                "agent": {
                    "agent_type": "claude-code",
                },
            },
        }
    )


def _build_config_with_judge(output_dir: str = "experiment_results_test") -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            **_build_config().to_dict(),
            "execution": {
                **_build_config().to_dict()["execution"],
                "output_dir": output_dir,
            },
            "judge": {
                "attack_judgment": False,
                "provider": "openai",
                "model": "gpt-5-mini",
                "api_key_env": "JUDGE_LLM_OPENAI_API_KEY",
            },
        }
    )


@pytest.mark.asyncio
async def test_execute_streaming_defaults_to_configured_skill_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config(),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    captured: dict[str, object] = {}

    async def fake_execute_concurrent(
        self: StreamingOrchestrator,
        skill_names: list[str] | None,
        attack_types: list[AttackType] | None,
        progress_callback: Any = None,
    ) -> StreamingResult:
        captured["skill_names"] = skill_names
        captured["attack_types"] = attack_types
        now = datetime.now()
        return StreamingResult(
            total_generated=0,
            total_executed=0,
            total_success=0,
            total_blocked=0,
            total_ignored=0,
            total_classification_failed=0,
            total_determined=0,
            success_rate=0.0,
            block_rate=0.0,
            ignored_rate=0.0,
            success_tests=[],
            blocked_tests=[],
            ignored_tests=[],
            classification_failed_tests=[],
            execution_time_seconds=0.0,
            started_at=now,
            completed_at=now,
            metadata={},
        )

    monkeypatch.setattr(StreamingOrchestrator, "_load_completed_tests", lambda self: None)
    monkeypatch.setattr(StreamingOrchestrator, "_get_all_skill_names", lambda self: ["INST-10_git_task0"])
    monkeypatch.setattr(StreamingOrchestrator, "_execute_streaming_concurrent", fake_execute_concurrent)

    await orchestrator.execute_streaming(
        skill_names=None,
        attack_types=[AttackType.INFORMATION_DISCLOSURE],
    )

    assert captured["skill_names"] == ["INST-10_git_task0"]


def test_persist_result_json_update_intermediate_result_omits_verdict_when_judge_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={
            "skill_name": "INST-10_git_task0",
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "task_script": "rm -rf /tmp/evil",
        },
    )
    test_result = ExecutionTestResult(
        test_id=TestCaseId(generated_test.test_id),
        executed_malicious=False,
        agent_output="I refuse to run that.",
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "adaptive_params": {"iteration_number": 0, "feedback_mode": "none"},
        },
    )
    result_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "",
                "error_type": "",
                "is_infrastructure_error": False,
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    orchestrator._persist_result_json_update(
        generated_test=generated_test,
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        iteration_number=0,
        test_result=test_result,
        finalize_classification=False,
    )

    data = json.loads((result_dir / "result.json").read_text(encoding="utf-8"))
    assert "final_verdict" not in data
    assert data["classification_pending"] is True


def test_persist_result_json_update_clears_pending_flag_after_final_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={
            "skill_name": "INST-10_git_task0",
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "task_script": "rm -rf /tmp/evil",
        },
    )
    test_result = ExecutionTestResult(
        test_id=TestCaseId(generated_test.test_id),
        executed_malicious=False,
        agent_output="I refuse to run that.",
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "adaptive_params": {"iteration_number": 0, "feedback_mode": "none"},
            "response_classification": {
                "verdict": "rejected",
                "evidence": "Explicit refusal",
                "confidence": 0.9,
                "reasoning": "The agent declined the task",
            },
        },
    )
    result_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "",
                "error_type": "",
                "is_infrastructure_error": False,
                "classification_pending": True,
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    orchestrator._persist_result_json_update(
        generated_test=generated_test,
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        iteration_number=0,
        test_result=test_result,
        finalize_classification=True,
    )

    data = json.loads((result_dir / "result.json").read_text(encoding="utf-8"))
    assert data["final_verdict"] == "rejected"
    assert "classification_pending" not in data


def test_load_completed_tests_queues_pending_classification_for_reclassification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    result_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "information_disclosure"
        / "iteration_0"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "Attack failed - ignored (no attack attempts detected)",
                "error_type": "",
                "is_infrastructure_error": False,
                "classification_pending": True,
                "agent_output": "I refuse to run this malicious step.",
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    orchestrator._load_completed_tests()

    assert orchestrator._ignored_tests == []
    assert orchestrator._blocked_tests == []
    assert orchestrator._completed_tests == {}
    pending = orchestrator._pending_reclassification["INST-10_git_task0_information_disclosure"]
    assert pending["skill_name"] == "INST-10_git_task0"
    assert pending["attack_type"] == "information_disclosure"


def test_load_completed_tests_queues_legacy_unclassified_result_for_reclassification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    result_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "information_disclosure"
        / "iteration_0"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "Attack failed - ignored (no attack attempts detected)",
                "error_type": "",
                "is_infrastructure_error": False,
                "agent_output": "I refuse to run this malicious step.",
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    orchestrator._load_completed_tests()

    assert orchestrator._ignored_tests == []
    assert "INST-10_git_task0_information_disclosure" in orchestrator._pending_reclassification


def test_load_completed_tests_builds_resume_state_for_non_terminal_rejected_iteration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    iteration_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "information_disclosure"
        / "iteration_0"
    )
    (iteration_dir / "skill").mkdir(parents=True, exist_ok=True)
    (iteration_dir / "skill" / "SKILL.md").write_text("# revised skill", encoding="utf-8")
    (iteration_dir / "result.json").write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "blocked",
                "blocked": True,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "The agent declined the task",
                "final_verdict": "rejected",
                "response_classification": {
                    "verdict": "rejected",
                    "evidence": "Explicit refusal",
                    "confidence": 0.9,
                    "reasoning": "The agent declined the task",
                },
                "metadata": {
                    "adaptive_params": {
                        "iteration_number": 0,
                        "feedback_mode": "rejected",
                        "has_previous_content": False,
                        "improvement_strategy": "Change narrative strategy",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    orchestrator._load_completed_tests()

    assert orchestrator._completed_tests == {}
    resume = orchestrator._resume_states["INST-10_git_task0_information_disclosure"]
    assert resume["iteration_number"] == 1
    adaptive = resume["adaptive_params"]
    assert adaptive.iteration_number == 1
    assert adaptive.feedback is not None
    assert adaptive.feedback.mode == "rejected"
    assert adaptive.previous_content == "# revised skill"


def test_load_completed_tests_falls_back_one_iteration_when_latest_artifacts_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(str(output_dir)),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    iteration_0 = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "information_disclosure"
        / "iteration_0"
    )
    (iteration_0 / "skill").mkdir(parents=True, exist_ok=True)
    (iteration_0 / "skill" / "SKILL.md").write_text("# stable prior skill", encoding="utf-8")
    (iteration_0 / "result.json").write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "blocked",
                "blocked": True,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "The agent declined the task",
                "final_verdict": "rejected",
                "response_classification": {
                    "verdict": "rejected",
                    "evidence": "Explicit refusal",
                    "confidence": 0.9,
                    "reasoning": "The agent declined the task",
                },
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    iteration_1 = iteration_0.parent / "iteration_1"
    iteration_1.mkdir(parents=True, exist_ok=True)
    (iteration_1 / "result.json").write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "The agent ignored the task",
                "final_verdict": "ignored",
                "response_classification": {
                    "verdict": "ignored",
                    "evidence": "No explicit refusal",
                    "confidence": 0.9,
                    "reasoning": "The agent ignored the task",
                },
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    orchestrator._load_completed_tests()

    resume = orchestrator._resume_states["INST-10_git_task0_information_disclosure"]
    assert resume["iteration_number"] == 1
    adaptive = resume["adaptive_params"]
    assert adaptive.iteration_number == 1
    assert adaptive.feedback is not None
    assert adaptive.feedback.mode == "rejected"
    assert adaptive.previous_content == "# stable prior skill"


def test_get_all_skill_names_uses_dataset_base_dir_for_direct_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"

    (skill_base / "skill_a").mkdir(parents=True)
    (skill_base / "skill_a" / "SKILL.md").write_text("a", encoding="utf-8")
    (skill_base / "skill_b").mkdir(parents=True)
    (skill_base / "skill_b" / "SKILL.md").write_text("b", encoding="utf-8")

    # No instruction.md for skill_b; enumeration should still include it.
    (instruction_base / "skill_a").mkdir(parents=True)
    (instruction_base / "skill_a" / "instruction.md").write_text("do a", encoding="utf-8")

    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "custom",
                    "base_dir": str(skill_base),
                    "instruction_base_dir": str(instruction_base),
                },
            },
            "execution": {
                "max_concurrency": 1,
                "output_dir": str(tmp_path / "results"),
                "sandbox": {"domain": "localhost:8080", "image": "claude_code:latest"},
                "agent": {"agent_type": "claude-code"},
            },
        }
    )

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(list_skill_names=lambda: ["skill_a", "skill_b"]),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    assert orchestrator._get_all_skill_names() == ["skill_a", "skill_b"]


def test_streaming_result_to_dict_includes_ignored_tests_in_totals() -> None:
    now = datetime.now()
    result = StreamingResult(
        total_generated=3,
        total_executed=3,
        total_success=1,
        total_blocked=1,
        total_ignored=1,
        total_classification_failed=0,
        total_determined=3,
        success_rate=1 / 3,
        block_rate=1 / 3,
        ignored_rate=1 / 3,
        success_tests=["success_case"],
        blocked_tests=["blocked_case"],
        ignored_tests=["ignored_case"],
        classification_failed_tests=[],
        execution_time_seconds=1.0,
        started_at=now,
        completed_at=now,
    )

    data = result.to_dict()

    assert data["total_test_cases"] == 3
    assert data["ignored_tests"] == ["ignored_case"]


@pytest.mark.asyncio
async def test_execute_single_test_direct_execution_only_writes_instruction_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "LICENSE.txt").write_text("license", encoding="utf-8")
    (source_skill_dir / "nested").mkdir()
    (source_skill_dir / "nested" / "data.txt").write_text("data", encoding="utf-8")

    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {"name": "skill_inject", "base_dir": "data/skill_inject"},
                "skill_names": ["INST-10_git_task0"],
                "attack_types": ["information_disclosure"],
            },
            "execution": {
                "max_concurrency": 1,
                "output_dir": str(output_dir),
                "sandbox": {"domain": "localhost:8080", "image": "claude_code:latest"},
                "agent": {"agent_type": "claude-code"},
            },
        }
    )

    class _RunnerStub:
        def prepare_context(self, test_case: Any) -> dict[str, Any]:
            return {"test_case": test_case}

        async def _run_test_async(
            self,
            test_case: Any,
            iteration_number: int = 0,
            skill_dir: Path | None = None,
        ) -> Any:
            return SimpleNamespace(test_case=test_case, iteration_number=iteration_number, skill_dir=skill_dir)

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: _RunnerStub(),
    )
    monkeypatch.setattr(StreamingOrchestrator, "_load_completed_tests", lambda self: None)

    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0",
        skill_path=str(source_skill_dir / "SKILL.md"),
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="Use the skill and update docx title.",
        should_be_blocked=True,
        source_skill_dir=str(source_skill_dir),
        source_aux_dir=str(tmp_path / "instruction_aux"),
        dataset="skill_inject",
        metadata={"skill_name": "INST-10_git_task0"},
    )

    result = await orchestrator._execute_single_test(generated_test, iteration_number=0)

    iteration_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
    )
    assert (iteration_dir / "instruction.md").exists()
    assert not (iteration_dir / "LICENSE.txt").exists()
    assert not (iteration_dir / "nested" / "data.txt").exists()
    result_any: Any = result
    assert result_any.test_case.attack_type == AttackType.DIRECT


@pytest.mark.asyncio
async def test_execute_streaming_concurrent_reports_history_reuse_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config(),
        max_attempts_per_test=1,
        stop_on_success=True,
        max_concurrency=4,
    )

    def fake_load_completed_tests(self: StreamingOrchestrator) -> None:
        self._completed_tests = {"INST-10_git_task0": {"direct"}}
        self._blocked_tests = ["INST-10_git_task0_direct"]
        self._success_tests = []
        self._history_reused_tests = {
            "INST-10_git_task0_direct": {
                "test_id": "INST-10_git_task0_direct",
                "status": "passed",
                "executed_malicious": False,
                "iteration": "iteration_4",
                "iteration_number": 4,
                "timestamp": "2026-04-09T11:31:19.294696",
                "result_file": "experiment_results_claude_minimax/test_details/.../iteration_4/result.json",
            }
        }

    monkeypatch.setattr(StreamingOrchestrator, "_load_completed_tests", fake_load_completed_tests)

    result = await orchestrator.execute_streaming(skill_names=["INST-10_git_task0"])

    assert result.metadata["all_from_history"] is True
    assert result.metadata["history_reused_tests"][0]["iteration"] == "iteration_4"
    assert result.metadata["history_reused_tests"][0]["iteration_number"] == 4


@pytest.mark.asyncio
async def test_execute_streaming_concurrency_one_reuses_history_with_consistent_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config(),
        max_attempts_per_test=1,
        stop_on_success=True,
        max_concurrency=1,
    )

    def fake_load_completed_tests(self: StreamingOrchestrator) -> None:
        self._completed_tests = {"INST-10_git_task0": {"direct"}}
        self._blocked_tests = []
        self._success_tests = ["INST-10_git_task0_direct"]
        self._history_reused_tests = {
            "INST-10_git_task0_direct": {
                "test_id": "INST-10_git_task0_direct",
                "status": "failed",
                "executed_malicious": True,
                "iteration": "iteration_2",
                "iteration_number": 2,
                "timestamp": "2026-04-09T11:31:19.294696",
                "result_file": "experiment_results_openclaw_glm/test_details/.../iteration_2/result.json",
            }
        }

    monkeypatch.setattr(StreamingOrchestrator, "_load_completed_tests", fake_load_completed_tests)

    result = await orchestrator.execute_streaming(skill_names=["INST-10_git_task0"])

    assert result.total_generated == 0
    assert result.total_executed == 0
    assert result.total_success == 1
    assert result.total_blocked == 0
    assert result.total_determined == 1
    assert result.success_tests == ["INST-10_git_task0_direct"]
    assert result.metadata["all_from_history"] is True
    assert result.metadata["history_reused_tests"][0]["iteration_number"] == 2


@pytest.mark.asyncio
async def test_feedback_loop_records_ignored_test_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GeneratorStub:
        async def generate_stream_with_feedback(self, **kwargs: Any) -> GeneratedTestCase:
            return generated_test

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config(),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={"task_script": "rm -rf /tmp/evil"},
    )

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
    ) -> ExecutionTestResult:
        return ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output="I will not do that.",
            metadata={},
        )

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "ignored",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.IGNORED,
                evidence="Agent did not engage",
                confidence=0.9,
                reasoning="No explicit refusal",
            ),
        )

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)

    progress = StreamingProgress(
        total_generated=0,
        total_executed=0,
        total_success=0,
        total_blocked=0,
        total_ignored=0,
        total_classification_failed=0,
        total_determined=0,
        current_skill="",
        current_attack_type="",
        current_params={},
        message="",
    )

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    assert progress.total_ignored == 1
    assert progress.total_determined == 1
    assert orchestrator._ignored_tests == ["INST-10_git_task0_information_disclosure"]


@pytest.mark.asyncio
async def test_reclassify_pending_records_ignored_test_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config(),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )
    orchestrator._judge_service = MagicMock()

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "ignored",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.IGNORED,
                evidence="Agent did not engage",
                confidence=0.9,
                reasoning="No explicit refusal",
            ),
        )

    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)

    orchestrator._pending_reclassification = {
        "INST-10_git_task0_information_disclosure": {
            "skill_name": "INST-10_git_task0",
            "attack_type": "information_disclosure",
            "agent_output": "ignored",
            "injection_text": "payload",
        }
    }

    progress = StreamingProgress(
        total_generated=0,
        total_executed=0,
        total_success=0,
        total_blocked=0,
        total_ignored=0,
        total_classification_failed=0,
        total_determined=0,
    )

    await orchestrator._reclassify_pending(progress)

    assert progress.total_ignored == 1
    assert progress.total_determined == 1
    assert orchestrator._ignored_tests == ["INST-10_git_task0_information_disclosure"]


@pytest.mark.asyncio
async def test_feedback_loop_records_judge_result_in_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GeneratorStub:
        async def generate_stream_with_feedback(self, **kwargs: Any) -> GeneratedTestCase:
            return generated_test

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    orchestrator = StreamingOrchestrator(
        config=TwoPhaseExecutionConfig.from_dict(
            {
                **_build_config().to_dict(),
                "judge": {
                    "provider": "openai",
                    "model": "gpt-5-mini",
                    "attack_judgment": True,
                },
            }
        ),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={"task_script": "rm -rf /tmp/evil"},
    )

    captured_result: ExecutionTestResult | None = None

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
        *,
        save_logs: bool = True,
    ) -> ExecutionTestResult:
        nonlocal captured_result
        captured_result = ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output="I should not do that.",
            metadata={},
        )
        return captured_result

    class _JudgeService:
        async def evaluate_injection(self, *args: Any, **kwargs: Any) -> LLMJudgeResult:
            return LLMJudgeResult(
                verdict=LLMJudgeVerdict.ATTACK_SUCCESS,
                evidence="Executed forbidden command",
                confidence=0.91,
                reasoning="Observed successful execution",
            )

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    orchestrator._judge_service = _JudgeService()
    orchestrator._judge_config_attack_judgment = True
    orchestrator._skill_success["INST-10_git_task0"] = set()

    progress = StreamingProgress()

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    assert captured_result is not None
    assert captured_result.metadata["judge"]["verdict"] == "attack_success"
    assert captured_result.metadata["judge"]["evidence"] == "Executed forbidden command"
    assert captured_result.metadata["judge_upgrade"] is True


@pytest.mark.asyncio
async def test_feedback_loop_records_response_classification_in_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GeneratorStub:
        async def generate_stream_with_feedback(self, **kwargs: Any) -> GeneratedTestCase:
            return generated_test

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={"task_script": "rm -rf /tmp/evil"},
    )

    captured_result: ExecutionTestResult | None = None

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
        *,
        save_logs: bool = True,
    ) -> ExecutionTestResult:
        nonlocal captured_result
        captured_result = ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output="I refuse.",
            metadata={},
        )
        return captured_result

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "rejected",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.REJECTED,
                evidence="Explicit refusal",
                confidence=0.88,
                reasoning="The agent declined the task",
            ),
        )

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)

    progress = StreamingProgress()

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    assert captured_result is not None
    assert captured_result.metadata["response_classification"]["verdict"] == "rejected"
    assert captured_result.metadata["response_classification"]["evidence"] == "Explicit refusal"


@pytest.mark.asyncio
async def test_feedback_loop_single_attempt_judge_saves_finalized_result_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GeneratorStub:
        async def generate_stream_with_feedback(self, **kwargs: Any) -> GeneratedTestCase:
            return generated_test

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(),
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={"task_script": "rm -rf /tmp/evil"},
    )

    saved_results: list[ExecutionTestResult] = []

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
        *,
        save_logs: bool = True,
    ) -> ExecutionTestResult:
        assert save_logs is False
        return ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output="I refuse.",
            metadata={},
        )

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "rejected",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.REJECTED,
                evidence="Explicit refusal",
                confidence=0.88,
                reasoning="The agent declined the task",
            ),
        )

    async def fake_save_finalized_test_detail(**kwargs: Any) -> None:
        saved_results.append(kwargs["test_result"])

    def fail_persist(**kwargs: Any) -> None:
        raise AssertionError("single-attempt judge flow should not persist intermediate result")

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)
    monkeypatch.setattr(orchestrator, "_save_finalized_test_detail", fake_save_finalized_test_detail)
    monkeypatch.setattr(orchestrator, "_persist_result_json_update", fail_persist)

    progress = StreamingProgress()

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    assert len(saved_results) == 1
    assert saved_results[0].metadata["response_classification"]["verdict"] == "rejected"


@pytest.mark.asyncio
async def test_feedback_loop_each_attempt_with_judge_saves_finalized_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GeneratorStub:
        async def generate_stream_with_feedback(self, **kwargs: Any) -> GeneratedTestCase:
            return generated_test

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )
    monkeypatch.setattr(
        StreamingOrchestrator,
        "_init_judge_service",
        staticmethod(lambda config: SimpleNamespace()),
    )

    orchestrator = StreamingOrchestrator(
        config=_build_config_with_judge(),
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={"task_script": "rm -rf /tmp/evil"},
    )

    saved_results: list[ExecutionTestResult] = []
    execute_calls: list[tuple[int, bool]] = []

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
        *,
        save_logs: bool = True,
    ) -> ExecutionTestResult:
        execute_calls.append((iteration_number, save_logs))
        return ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output=f"I refuse on iteration {iteration_number}.",
            metadata={},
        )

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "rejected",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.REJECTED,
                evidence="Explicit refusal",
                confidence=0.88,
                reasoning="The agent declined the task",
            ),
        )

    async def fake_save_finalized_test_detail(**kwargs: Any) -> None:
        saved_results.append(kwargs["test_result"])

    def fail_persist(**kwargs: Any) -> None:
        raise AssertionError("judge-configured flow should save finalized per-iteration results directly")

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)
    monkeypatch.setattr(orchestrator, "_save_finalized_test_detail", fake_save_finalized_test_detail)
    monkeypatch.setattr(orchestrator, "_persist_result_json_update", fail_persist)

    progress = StreamingProgress()

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    assert execute_calls == [(0, False), (1, False), (2, False)]
    assert len(saved_results) == 3
    assert [r.metadata["adaptive_params"]["iteration_number"] for r in saved_results] == [0, 1, 2]
    assert all(r.metadata["response_classification"]["verdict"] == "rejected" for r in saved_results)


def test_persist_result_json_update_carries_adaptive_params_into_judge_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    config = TwoPhaseExecutionConfig.from_dict(
        {
            **_build_config().to_dict(),
            "execution": {
                **_build_config().to_dict()["execution"],
                "output_dir": str(output_dir),
            },
        }
    )
    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )

    initial_adaptive_params = {
        "feedback_mode": "none",
        "iteration_number": 0,
        "has_previous_content": False,
        "improvement_strategy": "",
    }
    iteration_adaptive_params = {
        "feedback_mode": "rejected",
        "iteration_number": 0,
        "has_previous_content": False,
        "improvement_strategy": "be more subtle",
    }
    result_file = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
        / "result.json"
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "status": "passed",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "",
                "error_type": "",
                "is_infrastructure_error": False,
                "metadata": {
                    "strategy": "direct_execution",
                    "attack_type_dir": "direct",
                    "adaptive_params": initial_adaptive_params,
                },
            }
        ),
        encoding="utf-8",
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path="unused",
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir="unused",
        source_aux_dir="unused",
        dataset="skill_inject",
        metadata={
            "skill_name": "INST-10_git_task0",
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "adaptive_params": initial_adaptive_params,
        },
    )
    test_result = ExecutionTestResult(
        test_id=TestCaseId(generated_test.test_id),
        executed_malicious=False,
        blocked=True,
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
            "adaptive_params": iteration_adaptive_params,
            "judge": {
                "verdict": "attack_success",
                "evidence": "Executed forbidden command",
                "confidence": 0.93,
                "reasoning": "Observed execution",
            },
            "response_classification": {
                "verdict": "rejected",
                "evidence": "Explicit refusal",
                "confidence": 0.87,
                "reasoning": "The agent declined",
            },
        },
    )

    orchestrator._persist_result_json_update(
        generated_test=generated_test,
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        iteration_number=0,
        test_result=test_result,
    )

    data = json.loads(result_file.read_text(encoding="utf-8"))
    assert data["metadata"]["adaptive_params"] == iteration_adaptive_params
    assert "generation_adaptive_params" not in data["metadata"]
    assert data["judge"]["metadata"]["adaptive_params"] == iteration_adaptive_params
    assert data["response_classification"]["metadata"]["adaptive_params"] == iteration_adaptive_params


@pytest.mark.asyncio
async def test_execute_single_test_retry_success_updates_to_iteration_end_adaptive_params(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "results"
    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    initial_adaptive_params = {
        "feedback_mode": "none",
        "iteration_number": 0,
        "has_previous_content": False,
        "improvement_strategy": "",
    }

    class _RunnerStub:
        async def _run_test_async(
            self,
            test_case: Any,
            iteration_number: int = 0,
            skill_dir: Path | None = None,
            save_logs: bool = True,
        ) -> ExecutionTestResult:
            return ExecutionTestResult(
                test_id=test_case.id,
                executed_malicious=False,
                blocked=True,
                metadata={
                    "strategy": "direct_execution",
                    "attack_type_dir": "direct",
                    "adaptive_params": initial_adaptive_params,
                    "retry_trace": {
                        "operation_name": "sandbox_test_INST-10_git_task0_information_disclosure",
                        "total_attempts": 2,
                        "final_outcome": "retried_success",
                        "total_delay_seconds": 1.0,
                        "attempts": [],
                    },
                },
            )

    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: _RunnerStub(),
    )

    config = TwoPhaseExecutionConfig.from_dict(
        {
            **_build_config().to_dict(),
            "execution": {
                **_build_config().to_dict()["execution"],
                "output_dir": str(output_dir),
            },
        }
    )
    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=1,
        stop_on_success=False,
        max_concurrency=1,
    )
    monkeypatch.setattr(StreamingOrchestrator, "_load_completed_tests", lambda self: None)

    result_file = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
        / "result.json"
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "test_id": "INST-10_git_task0_information_disclosure",
                "status": "error",
                "blocked": False,
                "executed_malicious": False,
                "detected_consequences": [],
                "reasoning": "timeout",
                "error_type": "timeout",
                "is_infrastructure_error": True,
                "error_message": "sandbox timeout",
                "metadata": {
                    "strategy": "direct_execution",
                    "attack_type_dir": "direct",
                    "adaptive_params": initial_adaptive_params,
                    "retry_trace": {
                        "operation_name": "sandbox_test_INST-10_git_task0_information_disclosure",
                        "total_attempts": 2,
                        "final_outcome": "exhausted",
                        "total_delay_seconds": 1.0,
                        "attempts": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    generated_test = GeneratedTestCase(
        test_id="INST-10_git_task0_information_disclosure",
        skill_path=str(tmp_path / "source_skill" / "SKILL.md"),
        injection_layer="instruction",
        attack_type="information_disclosure",
        severity="medium",
        payload_content="payload",
        should_be_blocked=True,
        source_skill_dir=str(tmp_path / "source_skill"),
        source_aux_dir=str(tmp_path / "instruction_aux"),
        dataset="skill_inject",
        metadata={
            "skill_name": "INST-10_git_task0",
            "strategy": "direct_execution",
            "adaptive_params": initial_adaptive_params,
        },
    )

    await orchestrator._execute_single_test(generated_test, iteration_number=0)

    data = json.loads(result_file.read_text(encoding="utf-8"))
    assert data["metadata"]["adaptive_params"] == initial_adaptive_params
    assert "generation_adaptive_params" not in data["metadata"]
    assert data["metadata"]["retry_trace"]["final_outcome"] == "retried_success"
    assert "retry_info" not in data["metadata"]


def test_build_iteration_adaptive_metadata_uses_current_iteration_feedback() -> None:
    current_params = AdaptiveGenerationParams.create_initial()
    failure_analysis = FailureAnalysis(
        mode="ignored",
        root_cause="No effect",
        improvement_strategy="retry later",
        evidence=["No execution trace"],
    )

    metadata = StreamingOrchestrator._build_iteration_adaptive_metadata(
        current_params,
        failure_analysis=failure_analysis,
        previous_content="generated payload",
    )

    assert metadata == {
        "feedback_mode": "ignored",
        "iteration_number": 0,
        "has_previous_content": False,
        "improvement_strategy": "retry later",
    }


def test_build_iteration_success_adaptive_metadata_marks_feedback_not_needed() -> None:
    current_params = AdaptiveGenerationParams.create_initial().create_next(
        feedback=FailureAnalysis(
            mode="rejected",
            root_cause="Blocked",
            improvement_strategy="be more subtle",
            evidence=["Refusal"],
        ),
        previous_content="generated payload",
    )

    metadata = StreamingOrchestrator._build_success_iteration_adaptive_metadata(current_params)

    assert metadata == {
        "feedback_mode": "none",
        "iteration_number": 1,
        "has_previous_content": True,
        "improvement_strategy": "",
    }


@pytest.mark.asyncio
async def test_feedback_loop_each_iteration_has_correct_adaptive_params_in_result_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Each iteration's result.json must contain adaptive_params for THAT iteration.

    Previously, the post-loop _persist_result_json_update used an already-incremented
    iteration_number, pointing to a non-existent file (iteration_N+1) while the last test
    actually ran at iteration_N. This test verifies the fix: all three iterations receive
    their finalized adaptive_params (with feedback_mode), and not the next round's.
    """
    output_dir = tmp_path / "results"

    config = TwoPhaseExecutionConfig.from_dict(
        {
            **_build_config().to_dict(),
            "execution": {
                **_build_config().to_dict()["execution"],
                "output_dir": str(output_dir),
            },
        }
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.create_sandbox_test_runner",
        lambda config: SimpleNamespace(cleanup=lambda: None),
    )

    class _GeneratorStub:
        async def generate_stream_with_feedback(
            self,
            skill_name: str,
            attack_type: Any,
            adaptive_params: Any,
            output_dir: Any = None,
        ) -> GeneratedTestCase:
            raw_params = adaptive_params.to_dict()
            return GeneratedTestCase(
                test_id="INST-10_git_task0_information_disclosure",
                skill_path="unused",
                injection_layer="instruction",
                attack_type="information_disclosure",
                severity="medium",
                payload_content=f"payload_{raw_params['iteration_number']}",
                should_be_blocked=True,
                source_skill_dir="unused",
                source_aux_dir="unused",
                dataset="skill_inject",
                metadata={
                    "skill_name": "INST-10_git_task0",
                    "strategy": "direct_execution",
                    "attack_type_dir": "direct",
                    "task_script": "rm -rf /tmp/evil",
                    "adaptive_params": raw_params,
                },
            )

    monkeypatch.setattr(
        "src.application.services.streaming_orchestrator.TestGenerationStrategyFactory.create",
        lambda *args, **kwargs: _GeneratorStub(),
    )

    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=3,
        stop_on_success=False,
        max_concurrency=1,
    )

    async def fake_execute_single_test(
        generated_test: GeneratedTestCase,
        iteration_number: int = 0,
    ) -> ExecutionTestResult:
        # Simulate sandbox_test_runner writing an initial result.json with generator params.
        result_dir = (
            output_dir
            / "test_details"
            / "direct_execution"
            / "skill_inject"
            / "INST-10_git_task0"
            / "direct"
            / f"iteration_{iteration_number}"
        )
        result_dir.mkdir(parents=True, exist_ok=True)
        initial_metadata = dict(generated_test.metadata)
        (result_dir / "result.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "blocked": False,
                    "executed_malicious": False,
                    "detected_consequences": [],
                    "reasoning": "",
                    "error_type": "",
                    "is_infrastructure_error": False,
                    "metadata": initial_metadata,
                }
            ),
            encoding="utf-8",
        )
        return ExecutionTestResult(
            test_id=TestCaseId(generated_test.test_id),
            executed_malicious=False,
            agent_output="I will not comply.",
            metadata=initial_metadata,
        )

    async def fake_classify_response(**kwargs: Any) -> tuple[str, Any]:
        return (
            "ignored",
            LLMJudgeResult(
                verdict=LLMJudgeVerdict.IGNORED,
                evidence="Agent did not engage",
                confidence=0.9,
                reasoning="No explicit refusal",
            ),
        )

    monkeypatch.setattr(orchestrator, "_execute_single_test", fake_execute_single_test)
    monkeypatch.setattr(orchestrator, "_classify_response", fake_classify_response)

    progress = StreamingProgress()

    await orchestrator._execute_test_with_feedback_loop(
        skill_name="INST-10_git_task0",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        progress=progress,
        progress_callback=None,
        early_stop_lock=asyncio.Lock(),
    )

    # Every iteration's result.json must record adaptive_params for THAT iteration only.
    for iter_num in range(3):
        result_file = (
            output_dir
            / "test_details"
            / "direct_execution"
            / "skill_inject"
            / "INST-10_git_task0"
            / "direct"
            / f"iteration_{iter_num}"
            / "result.json"
        )
        assert result_file.exists(), f"iteration_{iter_num}/result.json missing"
        data = json.loads(result_file.read_text(encoding="utf-8"))
        params = data["metadata"]["adaptive_params"]
        assert params["iteration_number"] == iter_num, (
            f"iteration_{iter_num}/result.json has iteration_number={params['iteration_number']}, "
            f"expected {iter_num}"
        )
        # feedback_mode must be present (written by _persist_result_json_update)
        assert "feedback_mode" in params, (
            f"iteration_{iter_num}/result.json missing feedback_mode in adaptive_params"
        )

    # The last iteration should also have final_verdict written by post-loop persist.
    last_data = json.loads(
        (
            output_dir
            / "test_details"
            / "direct_execution"
            / "skill_inject"
            / "INST-10_git_task0"
            / "direct"
            / "iteration_2"
            / "result.json"
        )
        .read_text(encoding="utf-8")
    )
    assert "final_verdict" in last_data
