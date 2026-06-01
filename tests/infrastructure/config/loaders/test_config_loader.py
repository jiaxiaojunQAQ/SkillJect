# mypy: disable-error-code="no-untyped-def"
from pathlib import Path

import pytest

from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig
from src.infrastructure.config.loaders.config_loader import ConfigLoader
from src.shared.exceptions import ConfigurationError


def test_profile_config_promotes_top_level_agent_and_sandbox_into_execution() -> None:
    cfg = ConfigLoader.load("config/main.yaml", profile="claude-claude")

    assert cfg.execution.agent.agent_type == "claude-code"
    assert cfg.execution.agent.auth_token_env == "ANTHROPIC_API_KEY"
    assert cfg.execution.agent.base_url_env == "ANTHROPIC_BASE_URL"
    assert cfg.execution.sandbox.image == "claude_code:latest"
    assert cfg.execution.output_dir.name == "experiment_results_claude_claude"


def test_execution_plan_file_outside_config_main_is_loaded_as_profile_config(tmp_path) -> None:
    config_path = tmp_path / "adhoc-plan.yaml"
    config_path.write_text(
        "\n".join(
            [
                "execution_plan:",
                "  - profile: openclaw-minimax",
                "    method: direct_execution",
            ]
        ),
        encoding="utf-8",
    )

    cfg = ConfigLoader.load(config_path, profile="openclaw-minimax")

    assert cfg.execution.agent.agent_type == "openclaw"
    assert cfg.execution.output_dir.name == "experiment_results_openclaw_minimax"


def test_openclaw_provider_profiles_are_promoted_into_agent_config() -> None:
    claude_cfg = ConfigLoader.load("config/main.yaml", profile="openclaw-claude")
    gpt_cfg = ConfigLoader.load("config/main.yaml", profile="openclaw-gpt")
    claude_proxy_cfg = ConfigLoader.load("config/main.yaml", profile="openclaw-claude-openai")

    assert claude_cfg.execution.agent.provider == "anthropic"
    assert claude_cfg.execution.agent.use_api_key is True
    assert claude_cfg.execution.agent.auth_token_env == "ANTHROPIC_API_KEY"
    assert claude_cfg.execution.agent.base_url_env == "OPENCLAW_ANTHROPIC_BASE_URL"
    assert gpt_cfg.execution.agent.provider == "openai"
    assert claude_proxy_cfg.execution.agent.provider == "openai"
    assert claude_proxy_cfg.execution.agent.use_api_key is True
    assert claude_proxy_cfg.execution.agent.auth_token_env == "OPENCLAW_CLAUDE_OPENAI_API_KEY"
    assert claude_proxy_cfg.execution.agent.base_url_env == "OPENCLAW_CLAUDE_OPENAI_BASE_URL"


def test_agent_public_config_no_longer_exposes_inject_env() -> None:
    cfg = ConfigLoader.load("config/main.yaml", profile="claude-anthropic")

    assert "inject_env" not in cfg.execution.agent.to_dict()


def test_non_profile_config_path_is_rejected(tmp_path) -> None:
    config_path = tmp_path / "legacy-like.yaml"
    config_path.write_text("execution:\n  output_dir: experiment_results\n", encoding="utf-8")

    try:
        ConfigLoader.load(config_path)
    except Exception as exc:
        assert "Unsupported configuration format" in str(exc)
    else:
        raise AssertionError("Expected unsupported configuration format error")


def test_profile_yaml_path_is_not_a_supported_entrypoint() -> None:
    try:
        ConfigLoader.load("config/profiles/claude-claude.yaml")
    except Exception as exc:
        assert "Unsupported configuration format" in str(exc)
    else:
        raise AssertionError("Expected unsupported configuration format error")


def test_loading_main_without_explicit_profile_is_rejected() -> None:
    try:
        ConfigLoader.load("config/main.yaml")
    except Exception as exc:
        assert "Profile name is required" in str(exc)
    else:
        raise AssertionError("Expected missing profile error")


def test_generation_config_file_compatibility_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="generation.config_file is no longer supported"):
        ConfigLoader._parse_config(
            {
                "generation": {
                    "config_file": "direct_execution.yaml",
                },
                "execution": {
                    "agent": {"agent_type": "claude-code"},
                },
            },
            "config/main.yaml",
        )


def test_unknown_agent_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported agent_type"):
        TwoPhaseExecutionConfig.from_dict(
            {
                "generation": {"strategy": "direct_execution"},
                "execution": {
                    "agent": {"agent_type": "claude_code"},
                },
            }
        )


def _base_parse_config_dict(**overrides) -> dict:
    """Minimal config dict that passes _parse_config validation."""
    base = {
        "generation": {"strategy": "direct_execution"},
        "execution": {
            "agent": {"agent_type": "claude-code"},
        },
    }
    base.update(overrides)
    return base


def test_instruction_key_merges_into_dataset_dict() -> None:
    cfg = ConfigLoader._parse_config(
        _base_parse_config_dict(
            dataset={"name": "skills_sample"},
            instruction="data/instruction/custom",
        ),
        "config/main.yaml",
    )
    ds = cfg.generation.dataset
    assert ds.name == "skills_sample"
    assert ds.instruction_base_dir == Path("data/instruction/custom")
    assert ds.resolved_instruction_base_dir == Path("data/instruction/custom")


def test_instruction_key_with_string_dataset() -> None:
    cfg = ConfigLoader._parse_config(
        _base_parse_config_dict(
            dataset="skills_sample",
            instruction="data/instruction/custom",
        ),
        "config/main.yaml",
    )
    ds = cfg.generation.dataset
    assert ds.name == "skills_sample"
    assert ds.base_dir == Path("data/skills_sample")
    assert ds.instruction_base_dir == Path("data/instruction/custom")


def test_instruction_without_dataset_applies_to_default() -> None:
    cfg = ConfigLoader._parse_config(
        _base_parse_config_dict(
            instruction="data/instruction/standalone",
        ),
        "config/main.yaml",
    )
    ds = cfg.generation.dataset
    assert ds.name == "skills_from_skill0"
    assert ds.instruction_base_dir == Path("data/instruction/standalone")


def test_path_string_dataset_in_config_loader() -> None:
    cfg = ConfigLoader._parse_config(
        _base_parse_config_dict(
            dataset="data/skill_inject",
        ),
        "config/main.yaml",
    )
    ds = cfg.generation.dataset
    assert ds.name == "skill_inject"
    assert ds.base_dir == Path("data/skill_inject")


def test_no_instruction_key_leaves_dataset_untouched() -> None:
    cfg = ConfigLoader._parse_config(
        _base_parse_config_dict(
            dataset="skills_sample",
        ),
        "config/main.yaml",
    )
    ds = cfg.generation.dataset
    assert ds.instruction_base_dir is None
    assert ds.resolved_instruction_base_dir == Path("data/instruction/skills_sample")
