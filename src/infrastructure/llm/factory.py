"""
LLM Client Factory

All strategy and judge LLM calls use the OpenAI-compatible interface.
Different providers (MiniMax, Zhipu, etc.) are accessed via base_url.
"""

import os

from src.infrastructure.llm.base_llm_client import LLMClient, LLMClientConfig
from src.infrastructure.llm.openai_client import OpenAIClient
from src.shared.constants import LLM_TIMEOUT
from src.shared.exceptions import RetryConfig


class LLMClientFactory:
    """LLM Client Factory

    Creates OpenAI-compatible LLM client instances.
    All providers are accessed via the OpenAI SDK with configurable base_url.
    """

    DEFAULT_MODEL = "gpt-4"

    @classmethod
    def create_client(
        cls,
        config: LLMClientConfig | None = None,
        **kwargs,
    ) -> LLMClient:
        """Create LLM client (OpenAI-compatible).

        Args:
            config: Client configuration
            **kwargs: Configuration parameters including:
                - model: Model name
                - base_url: API base URL
                - api_key_env: Environment variable name for API key
                - timeout, temperature, max_tokens: Tuning parameters

        Returns:
            OpenAI-compatible LLM client instance
        """
        if config is None:
            config = cls._create_config(**kwargs)

        base_url = kwargs.get("base_url", "")
        return OpenAIClient(config, base_url=base_url)

    @classmethod
    def _create_config(cls, **kwargs) -> LLMClientConfig:
        """Create client configuration.

        API key resolution: api_key kwarg > api_key_env env var > OPENAI_API_KEY.
        """
        api_key = kwargs.get("api_key", "")
        api_key_env = kwargs.get("api_key_env", "")

        if not api_key and api_key_env:
            api_key = os.getenv(api_key_env, "")

        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")

        return LLMClientConfig(
            api_key=api_key,
            model=kwargs.get("model", cls.DEFAULT_MODEL),
            max_tokens=kwargs.get("max_tokens", 8192),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", LLM_TIMEOUT),
            retry_config=kwargs.get("retry_config") or RetryConfig(
                max_attempts=kwargs.get("retry_max_attempts", 3),
                base_delay=kwargs.get("retry_base_delay", 1.0),
                max_delay=kwargs.get("retry_max_delay", 30.0),
            ),
        )


def create_client(**kwargs) -> LLMClient:
    """Convenience function to create LLM client."""
    return LLMClientFactory.create_client(**kwargs)
# mypy: disable-error-code="no-untyped-def,arg-type,call-arg"
