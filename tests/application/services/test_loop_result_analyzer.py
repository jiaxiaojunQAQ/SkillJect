import json
from pathlib import Path

from src.application.scripts.verdict_utils import get_current_verdict
from src.application.services.loop_result_analyzer import LoopResultAnalyzer


def test_get_current_verdict_prefers_final_verdict() -> None:
    data = {
        "final_verdict": "ignored",
        "response_classification": {"verdict": "rejected"},
        "executed_malicious": True,
    }

    assert get_current_verdict(data) == "ignored"


def test_get_current_verdict_returns_unknown_when_classification_pending() -> None:
    data = {
        "classification_pending": True,
        "reasoning": "Attack failed - ignored (no attack attempts detected)",
        "executed_malicious": False,
    }

    assert get_current_verdict(data) == "unknown"


def test_aggregate_test_case_results_uses_final_verdict_and_preserves_blocked_state(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "skill_a" / "information_disclosure"
    iteration_0 = test_dir / "iteration_0"
    iteration_1 = test_dir / "iteration_1"
    iteration_0.mkdir(parents=True)
    iteration_1.mkdir(parents=True)

    (iteration_0 / "result.json").write_text(
        json.dumps(
            {
                "attack_type": "information_disclosure",
                "dataset": "skill_inject",
                "final_verdict": "rejected",
                "executed_malicious": False,
                "blocked": True,
                "execution_time_seconds": 1.2,
            }
        ),
        encoding="utf-8",
    )
    (iteration_1 / "result.json").write_text(
        json.dumps(
            {
                "attack_type": "information_disclosure",
                "dataset": "skill_inject",
                "final_verdict": "attack_success",
                "executed_malicious": True,
                "blocked": False,
                "execution_time_seconds": 2.4,
            }
        ),
        encoding="utf-8",
    )

    analyzer = LoopResultAnalyzer()
    summary = analyzer.aggregate_test_case_results(
        test_id="skill_a_information_disclosure",
        test_dir=test_dir,
    )

    assert summary["final_status"] == "attack_success"
    assert summary["succeeded_iteration"] == 1
    assert summary["attempts_summary"][0]["final_verdict"] == "rejected"
    assert summary["attempts_summary"][0]["blocked"] is True
    assert summary["attempts_summary"][1]["final_verdict"] == "attack_success"
