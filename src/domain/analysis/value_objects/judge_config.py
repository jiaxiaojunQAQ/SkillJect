"""
Judge Configuration Value Object

Configuration for the LLM-as-judge evaluation system.
All judge LLM calls use the OpenAI-compatible interface via configurable base_url.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JudgeConfig:
    """Configuration for the LLM judge.

    The judge uses a separate LLM from the strategy generation and agent runtime.
    All judge calls use the OpenAI-compatible API; different providers are
    accessed via base_url.

    Attributes:
        attack_judgment: Whether to use LLM for attack-success detection.
            When True, LLM evaluates attack success; when False, rule-based
            dual-layer detection is used. Response classification (REJECTED
            vs IGNORED) always uses LLM regardless of this flag.
        model: Model name for the judge.
        timeout: Request timeout in seconds.
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens in judge response.
        api_key_env: Environment variable name for the API key.
        base_url_env: Environment variable name for the base URL.
        base_url: Explicit base URL (overrides env var).
    """

    attack_judgment: bool = False
    model: str = "gpt-4"
    timeout: int = 180
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key_env: str = ""
    base_url_env: str = ""
    base_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_judgment": self.attack_judgment,
            "model": self.model,
            "timeout": self.timeout,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key_env": self.api_key_env,
            "base_url_env": self.base_url_env,
            "base_url": self.base_url,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "JudgeConfig":
        """Create JudgeConfig from a dictionary.

        Args:
            data: Configuration dictionary, or None/empty for defaults.

        Returns:
            JudgeConfig instance.
        """
        if not data or not isinstance(data, dict):
            return cls()

        return cls(
            attack_judgment=data.get("attack_judgment", data.get("enabled", False)),
            model=data.get("model", "gpt-4"),
            timeout=data.get("timeout", 180),
            temperature=data.get("temperature", 0.3),
            max_tokens=data.get("max_tokens", 4096),
            api_key_env=data.get("api_key_env", ""),
            base_url_env=data.get("base_url_env", ""),
            base_url=data.get("base_url", ""),
        )
