from typing import Any

from run import (
    _resolve_iteration_controls,
    apply_step_overrides,
    build_global_step_overrides,
    merge_step_with_global_overrides,
)
from src.domain.testing.value_objects.execution_config import (
    TwoPhaseExecutionConfig,
)
from src.infrastructure.config.loaders.config_loader import ConfigLoader
from src.infrastructure.config.loaders.file_loader import FileConfigLoader


def test_build_global_step_overrides_prefers_top_level_over_generation() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "method": "template_injection",
            "dataset": {
                "name": "from_generation",
                "base_dir": "data/generation_dataset",
            },
        },
        "method": "direct_execution",
        "dataset": {
            "name": "from_top_level",
            "base_dir": "data/top_level_dataset",
        },
    }

    overrides = build_global_step_overrides(raw_config)

    assert overrides["method"] == "direct_execution"
    assert overrides["dataset"] == {
        "name": "from_top_level",
        "base_dir": "data/top_level_dataset",
    }


def test_merge_step_with_global_overrides_applies_global_defaults() -> None:
    global_overrides: dict[str, Any] = {
        "method": "direct_execution",
        "dataset": {
            "name": "skill_inject",
            "base_dir": "data/skill_inject",
            "instruction_base_dir": "data/instruction/skill_inject",
        },
    }
    step: dict[str, Any] = {"profile": "openclaw-gpt"}

    merged = merge_step_with_global_overrides(step, global_overrides)

    assert merged["profile"] == "openclaw-gpt"
    assert merged["method"] == "direct_execution"
    assert merged["dataset"] == {
        "name": "skill_inject",
        "base_dir": "data/skill_inject",
        "instruction_base_dir": "data/instruction/skill_inject",
    }


def test_merge_step_with_global_overrides_allows_step_to_override_dataset_and_method() -> None:
    global_overrides: dict[str, Any] = {
        "method": "direct_execution",
        "dataset": {
            "name": "skill_inject",
            "base_dir": "data/skill_inject",
            "instruction_base_dir": "data/instruction/skill_inject",
        },
    }
    step: dict[str, Any] = {
        "profile": "claude-gpt",
        "method": "skillject",
        "dataset": {
            "name": "skills_from_openclaw",
        },
    }

    merged = merge_step_with_global_overrides(step, global_overrides)

    assert merged["profile"] == "claude-gpt"
    assert merged["method"] == "skillject"
    assert merged["dataset"] == {
        "name": "skills_from_openclaw",
        "base_dir": "data/skill_inject",
        "instruction_base_dir": "data/instruction/skill_inject",
    }


def test_build_global_step_overrides_extracts_skill_names_from_generation_and_top_level() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "method": "direct_execution",
            "skill_names": ["gen_a", "gen_b"],
        },
        "skill_names": ["top_a"],
    }

    overrides = build_global_step_overrides(raw_config)
    assert overrides["skill_names"] == ["top_a"]


def test_build_global_step_overrides_supports_skills_alias_object() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "method": "direct_execution",
            "skills": {"target_names": ["alias_a"]},
        }
    }

    overrides = build_global_step_overrides(raw_config)
    assert overrides["skill_names"] == ["alias_a"]


def test_build_global_step_overrides_extracts_script_selection() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "method": "direct_execution",
            "script_selection": {"mode": "mapping", "mapping_file": "data/manifest.json"},
            "best_skills_dir": "ignored",
        },
    }

    overrides = build_global_step_overrides(raw_config)

    assert overrides["method"] == "direct_execution"
    assert overrides["script_selection"] == {"mode": "mapping", "mapping_file": "data/manifest.json"}


def test_resolve_iteration_controls_non_adaptive_strategy_defaults_to_single_pass() -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {"strategy": "direct_execution", "dataset": {"name": "skill_inject"}},
            "execution": {"output_dir": "experiment_results"},
            "adaptive_iteration": {"max_attempts": 9, "stop_on_success": False},
        }
    )
    attempts, stop = _resolve_iteration_controls(
        config,
        max_attempts_override=None,
        stop_on_success_override=None,
    )
    assert attempts == 1
    assert stop is True


def test_resolve_iteration_controls_skillject_uses_adaptive_defaults() -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {"strategy": "skillject", "dataset": {"name": "skill_inject"}},
            "execution": {"output_dir": "experiment_results"},
            "adaptive_iteration": {"max_attempts": 7, "stop_on_success": False},
        }
    )
    attempts, stop = _resolve_iteration_controls(
        config,
        max_attempts_override=None,
        stop_on_success_override=None,
    )
    assert attempts == 7
    assert stop is False


def test_build_global_step_overrides_extracts_instruction_from_generation() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "method": "direct_execution",
            "instruction": "data/instruction/custom",
        },
    }

    overrides = build_global_step_overrides(raw_config)
    assert overrides["instruction"] == "data/instruction/custom"


def test_build_global_step_overrides_instruction_top_level_overrides_generation() -> None:
    raw_config: dict[str, Any] = {
        "generation": {
            "instruction": "data/instruction/gen_level",
        },
        "instruction": "data/instruction/top_level",
    }

    overrides = build_global_step_overrides(raw_config)
    assert overrides["instruction"] == "data/instruction/top_level"


def test_build_global_step_overrides_instruction_absent_when_not_set() -> None:
    raw_config: dict[str, Any] = {
        "generation": {"method": "direct_execution"},
    }

    overrides = build_global_step_overrides(raw_config)
    assert "instruction" not in overrides


def test_build_global_step_overrides_extracts_llm_judge() -> None:
    raw_config: dict[str, Any] = {
        "llm_judge": {
            "provider": "openai",
            "model": "gpt-5-mini",
            "attack_judgment": False,
        }
    }

    overrides = build_global_step_overrides(raw_config)
    assert overrides["llm_judge"] == {
        "provider": "openai",
        "model": "gpt-5-mini",
        "attack_judgment": False,
    }


def test_merge_step_with_global_overrides_allows_step_to_override_llm_judge() -> None:
    global_overrides: dict[str, Any] = {
        "llm_judge": {
            "provider": "openai",
            "model": "gpt-5-mini",
        },
    }
    step: dict[str, Any] = {
        "profile": "claude-gpt",
        "llm_judge": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
        },
    }

    merged = merge_step_with_global_overrides(step, global_overrides)

    assert merged["llm_judge"] == {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    }


def test_apply_step_overrides_sets_judge_from_llm_judge_dict() -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {"strategy": "direct_execution"},
            "execution": {"agent": {"agent_type": "claude-code"}},
        }
    )
    step: dict[str, Any] = {
        "llm_judge": {
            "provider": "openai",
            "model": "gpt-5-mini",
            "attack_judgment": False,
        }
    }

    updated = apply_step_overrides(config, step)

    assert updated.judge is not None
    assert updated.judge.model == "gpt-5-mini"
    assert updated.judge.attack_judgment is False


def test_apply_step_overrides_allows_disabling_judge_with_null_llm_judge() -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {"strategy": "direct_execution"},
            "execution": {"agent": {"agent_type": "claude-code"}},
            "judge": {
                "provider": "openai",
                "model": "gpt-5-mini",
            },
        }
    )

    updated = apply_step_overrides(config, {"llm_judge": None})
    assert updated.judge is None


def test_execution_plan_flow_applies_main_llm_judge_to_profile_config() -> None:
    raw_config = FileConfigLoader.load_yaml("config/main.yaml")
    execution_plan = raw_config["execution_plan"]
    step = execution_plan[0]

    global_overrides = build_global_step_overrides(raw_config)
    merged_step = merge_step_with_global_overrides(step, global_overrides)

    profile_name = str(step["profile"])
    config = ConfigLoader.load("config/main.yaml", profile=profile_name)
    updated = apply_step_overrides(config, merged_step)

    assert updated.judge is not None
