"""
Unit tests for AgentConfig credential resolution in get_claude_settings().
"""

import logging
from unittest.mock import patch

import pytest

from src.domain.testing.value_objects.execution_config import AgentConfig
from src.shared.exceptions import ConfigurationError


class TestGetClaudeSettingsAuthResolution:
    """get_claude_settings must fail loudly when credentials cannot be resolved."""

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_when_auth_token_unresolved(self) -> None:
        config = AgentConfig(use_api_key=False, auth_token_env="ANTHROPIC_AUTH_TOKEN")

        with pytest.raises(ConfigurationError) as exc_info:
            config.get_claude_settings()

        message = str(exc_info.value)
        assert "ANTHROPIC_AUTH_TOKEN" in message
        assert "auth_token_env" in message
        assert ".env" in message

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_when_api_key_unresolved(self) -> None:
        config = AgentConfig(use_api_key=True, auth_token_env="ZHIPU_API_KEY")

        with pytest.raises(ConfigurationError) as exc_info:
            config.get_claude_settings()

        message = str(exc_info.value)
        assert "ZHIPU_API_KEY" in message
        assert "ANTHROPIC_API_KEY" in message  # fallback also checked

    @patch.dict(
        "os.environ",
        {
            "ANTHROPIC_AUTH_TOKEN": "env-token-12345678",
            "ANTHROPIC_BASE_URL": "https://relay.example.com",
        },
        clear=True,
    )
    def test_resolves_auth_token_and_base_url_from_env(self) -> None:
        config = AgentConfig(use_api_key=False)

        settings = config.get_claude_settings()

        assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "env-token-12345678"
        assert settings["env"]["ANTHROPIC_BASE_URL"] == "https://relay.example.com"
        assert settings["permissions"] == {"defaultMode": "bypassPermissions"}

    @patch.dict("os.environ", {}, clear=True)
    def test_config_fields_take_precedence_without_env(self) -> None:
        config = AgentConfig(
            use_api_key=False,
            auth_token="cfg-token-12345678",
            base_url="https://cfg.example.com",
        )

        settings = config.get_claude_settings()

        assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "cfg-token-12345678"
        assert settings["env"]["ANTHROPIC_BASE_URL"] == "https://cfg.example.com"

    @patch.dict("os.environ", {"ANTHROPIC_AUTH_TOKEN": "env-token-12345678"}, clear=True)
    def test_warns_when_base_url_missing(self, caplog: pytest.LogCaptureFixture) -> None:
        config = AgentConfig(use_api_key=False, base_url_env="ANTHROPIC_BASE_URL")

        with caplog.at_level(logging.WARNING):
            config.get_claude_settings()

        assert "ANTHROPIC_BASE_URL" in caplog.text

    @patch.dict(
        "os.environ",
        {"ANTHROPIC_AUTH_TOKEN": "env-token-12345678", "ANTHROPIC_BASE_URL": "https://r.example.com"},
        clear=True,
    )
    def test_logs_injected_env_with_masked_token(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = AgentConfig(use_api_key=False)

        with caplog.at_level(logging.INFO):
            config.get_claude_settings()

        assert "ANTHROPIC_AUTH_TOKEN" in caplog.text
        assert "env-token-12345678" not in caplog.text  # never log the raw token
        assert "5678" in caplog.text  # masked tail
