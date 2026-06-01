import pytest

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.domain.testing.value_objects.execution_config import (
    AgentConfig,
    GenerationConfig,
    GenerationStrategy,
)
from src.infrastructure.llm.base_llm_client import LLMClientConfig
from src.shared.constants import COMMAND_TIMEOUT, INSTALL_TIMEOUT, LLM_TIMEOUT, REQUEST_TIMEOUT
from src.shared.types import AgentType


def test_shared_timeout_constants_keep_current_public_defaults() -> None:
    assert LLM_TIMEOUT == 120
    assert REQUEST_TIMEOUT == 120
    assert INSTALL_TIMEOUT == 300
    assert COMMAND_TIMEOUT == 300


def test_llm_client_defaults_align_with_shared_timeout_constants() -> None:
    llm_config = LLMClientConfig()

    assert llm_config.timeout == LLM_TIMEOUT
    assert REQUEST_TIMEOUT == 120


def test_base_agent_config_default_timeouts_align_with_shared_constants() -> None:
    config = BaseAgentConfig(
        name="dummy",
        display_name="Dummy Agent",
        npm_package="dummy",
        command="dummy",
        env_prefix="DUMMY",
        env_vars={},
        install_command="install dummy",
    )

    assert config.install_timeout == INSTALL_TIMEOUT
    assert config.command_timeout == COMMAND_TIMEOUT


def test_public_agent_types_are_limited_to_supported_runtimes() -> None:
    assert {agent_type.value for agent_type in AgentType} == {
        "claude-code",
        "openclaw",
    }


def test_public_generation_strategies_match_supported_contract() -> None:
    assert {strategy.value for strategy in GenerationStrategy} == {
        "template_injection",
        "skillject",
        "direct_execution",
        "baseline",
    }


@pytest.mark.parametrize(
    "removed_strategy",
    ["skillject_image", "skillject_cloze", "skillject_transfer"],
)
def test_removed_generation_strategy_names_are_rejected(removed_strategy: str) -> None:
    with pytest.raises(ValueError, match=f"Invalid generation strategy: {removed_strategy}"):
        GenerationConfig.from_dict({"strategy": removed_strategy})


def test_generation_config_no_longer_exposes_variant_fields() -> None:
    config = GenerationConfig.from_dict({"strategy": "skillject"})

    assert {
        "prompt_style",
        "instruction_style",
        "num_blanks",
        "blank_format",
        "framing_style",
        "enable_script_analysis",
        "best_skills_dir",
    }.isdisjoint(config.to_dict())


def test_agent_config_ignores_removed_inject_env_field() -> None:
    config = AgentConfig.from_dict(
        {
            "agent_type": "claude-code",
            "inject_env": True,
            "use_api_key": True,
            "auth_token_env": "ANTHROPIC_API_KEY",
        }
    )

    assert "inject_env" not in config.to_dict()
