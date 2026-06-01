"""
Execution Configuration Value Objects

Defines execution configuration for two-phase framework
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.domain.analysis.value_objects.judge_config import JudgeConfig

# Configuration validation constants
MIN_CONCURRENCY = 1
MAX_SAFE_CONCURRENCY = 10
MIN_TIMEOUT = 1
MIN_RETRIES = 0


@dataclass(frozen=True)
class DatasetConfig:
    """Dataset configuration (value object)

    Defines configuration for skill datasets, supports switching between different datasets via configuration
    """

    name: str = "skills_from_skill0"
    base_dir: Path = Path("data/skills_from_skill0")
    instruction_base_dir: Path | None = None

    def __post_init__(self) -> None:
        """Validate configuration"""
        if not isinstance(self.base_dir, Path):
            object.__setattr__(self, "base_dir", Path(self.base_dir))
        if self.instruction_base_dir is not None and not isinstance(self.instruction_base_dir, Path):
            object.__setattr__(self, "instruction_base_dir", Path(self.instruction_base_dir))

    @property
    def resolved_instruction_base_dir(self) -> Path:
        """Return instruction_base_dir if set, else derive: data/instruction/{name}"""
        if self.instruction_base_dir is not None:
            return self.instruction_base_dir
        return Path(f"data/instruction/{self.name}")

    @staticmethod
    def _is_path_like(value: str) -> bool:
        """Return True if value looks like a file path rather than a dataset name."""
        return "/" in value or "\\" in value or value.startswith(".")

    @staticmethod
    def _derive_name_from_path(path_str: str) -> str:
        """Derive a dataset name from the last component of a path string."""
        # Normalize backslashes for cross-platform name extraction
        normalized = path_str.replace("\\", "/").rstrip("/")
        return Path(normalized).name or "unnamed_dataset"

    @classmethod
    def from_dict(cls, data: Any) -> "DatasetConfig":
        """Create dataset configuration from dict or string

        Supported formats:
        1. DatasetConfig object: return directly
        2. Shorthand name: dataset: skills_from_skill0
        3. Path string: dataset: data/skill_inject or dataset: /abs/path/to/skills
        4. Dictionary format:
           dataset:
             name: skills_from_skill0
             base_dir: data/skills_from_skill0
             instruction_base_dir: data/instruction/skills_from_skill0

        Args:
            data: Configuration data (DatasetConfig, string, or dict)

        Returns:
            DatasetConfig instance
        """
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            if cls._is_path_like(data):
                derived_name = cls._derive_name_from_path(data)
                return cls(name=derived_name, base_dir=Path(data))
            return cls(name=data, base_dir=Path(f"data/{data}"))
        elif isinstance(data, dict):
            name: str | None = data.get("name")
            base_dir: str | None = data.get("base_dir")
            instruction_base_dir: Any = data.get("instruction_base_dir")

            if base_dir is not None:
                if name is None:
                    name = cls._derive_name_from_path(str(base_dir))
            else:
                if name is None:
                    name = "skills_from_skill0"
                base_dir = f"data/{name}"

            if instruction_base_dir is not None:
                instruction_base_dir = Path(instruction_base_dir)
            return cls(name=name, base_dir=Path(base_dir), instruction_base_dir=instruction_base_dir)
        return cls()


class GenerationStrategy(Enum):
    """Generation strategy type"""

    TEMPLATE_INJECTION = "template_injection"
    SKILLJECT = "skillject"
    DIRECT_EXECUTION = "direct_execution"
    BASELINE = "baseline"


class LogLevel(Enum):
    """Log level"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class GenerationConfig:
    """Phase 1: Test generation configuration (value object)

    Defines all configuration parameters for test generation phase
    """

    # Generation strategy
    strategy: GenerationStrategy

    # Dataset configuration
    dataset: DatasetConfig = field(default_factory=DatasetConfig)

    # Script mapping file for direct_execution method
    script_mapping_file: str | None = None  # Optional custom manifest path

    # Script selection mode (auto, mapping, random)
    script_selection_mode: str = "auto"  # auto = strategy-based, mapping = MappingScriptSelector, random = RandomScriptSelector
    script_selection_mapping_file: str | None = None  # Used when script_selection_mode="mapping"

    # Template-related paths (backward compatible, prefer dataset configuration)
    template_base_dir: Path | None = None  # Use dataset.base_dir when None
    template_output_dir: Path = Path("generated_tests")

    # LLM configuration (OpenAI-compatible, provider selected via base_url)
    llm_model: str = "gpt-4"
    llm_max_concurrency: int = 4
    llm_timeout: int = 120
    llm_base_url: str = ""  # Empty = use provider default
    llm_api_key_env: str = ""  # Empty = use provider default
    llm_base_url_env: str = ""  # Empty = use provider default
    llm_temperature: float = 0.7
    llm_max_tokens: int = 8192

    # Infrastructure retry configuration
    llm_retry_max_attempts: int = 3
    llm_retry_base_delay: float = 1.0
    llm_retry_max_delay: float = 30.0

    # Filter conditions
    attack_types: list[str] = field(default_factory=list)
    injection_layers: list[str] = field(default_factory=list)
    severities: list[str] = field(default_factory=list)
    skill_names: list[str] = field(default_factory=list)

    # Limits
    max_tests: int | None = None
    max_tests_per_skill: int | None = None

    # Metadata options
    save_metadata: bool = True
    metadata_format: str = "json"  # json, yaml

    def __post_init__(self) -> None:
        """Validate configuration"""
        # Use dataset.base_dir when template_base_dir is None
        if self.template_base_dir is None:
            object.__setattr__(self, "template_base_dir", self.dataset.base_dir)
        elif not isinstance(self.template_base_dir, Path):
            object.__setattr__(self, "template_base_dir", Path(self.template_base_dir))

        if not isinstance(self.template_output_dir, Path):
            object.__setattr__(self, "template_output_dir", Path(self.template_output_dir))

        if self.llm_max_concurrency < 1:
            raise ValueError("llm_max_concurrency must be greater than 0")

        if self.max_tests is not None and self.max_tests < 1:
            raise ValueError("max_tests must be greater than 0")

    @property
    def computed_output_dir(self) -> Path:
        """Build complete output directory path

        Return format: generated_tests/{dataset_name}/{method_dir}
        - method_dir: template_injection, skillject, direct_execution

        Returns:
            Complete output directory path
        """
        dataset_name = self.dataset.name
        if self.strategy == GenerationStrategy.TEMPLATE_INJECTION:
            method_dir = "template_injection"
        elif self.strategy == GenerationStrategy.SKILLJECT:
            method_dir = "skillject"
        elif self.strategy == GenerationStrategy.DIRECT_EXECUTION:
            method_dir = "direct_execution"
        elif self.strategy == GenerationStrategy.BASELINE:
            method_dir = "baseline"
        else:
            raise ValueError(f"Unsupported generation strategy for output dir: {self.strategy}")
        return Path("generated_tests") / dataset_name / method_dir

    @staticmethod
    def _normalize_dataset_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle dataset configuration section

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "dataset" in data:
            dataset_input = data["dataset"]
            # Handle different types of input
            if isinstance(dataset_input, DatasetConfig):
                # Already a DatasetConfig object, use directly
                dataset_config = dataset_input
            else:
                # Dictionary or other type, use from_dict to convert
                dataset_config = DatasetConfig.from_dict(dataset_input)
            normalized["dataset"] = dataset_config
            normalized["dataset_name"] = dataset_config.name
            normalized["dataset_base_dir"] = str(dataset_config.base_dir)

    @staticmethod
    def _normalize_template_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle template configuration section

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "template" in data:
            template = data["template"]
            base_dir = template.get("base_dir", "data/skills_from_skill0")

            # Handle {dataset_base_dir} placeholder
            if "{dataset_base_dir}" in base_dir:
                base_dir = base_dir.replace(
                    "{dataset_base_dir}",
                    normalized.get("dataset_base_dir", "data/skills_from_skill0"),
                )

            normalized["template_base_dir"] = base_dir

            # Simplified output_dir (relative path)
            # If configured as absolute path (starts with / or generated_tests), keep unchanged
            output_dir = template.get("output_dir", "template_injection")
            if not output_dir.startswith("/") and not output_dir.startswith("generated_tests"):
                # Relative path, will build complete path in computed_output_dir
                normalized["template_output_dir"] = output_dir
            else:
                # Absolute path, maintain backward compatibility
                normalized["template_output_dir"] = output_dir
        elif "template_base_dir" in data:
            # Direct template_base_dir key (non-nested structure)
            base_dir = data.get("template_base_dir", "data/skills_from_skill0")

            # Handle {dataset_base_dir} placeholder
            if "{dataset_base_dir}" in base_dir:
                base_dir = base_dir.replace(
                    "{dataset_base_dir}",
                    normalized.get("dataset_base_dir", "data/skills_from_skill0"),
                )

            normalized["template_base_dir"] = base_dir

            # Handle template_output_dir
            if "template_output_dir" in data:
                normalized["template_output_dir"] = data["template_output_dir"]

    @staticmethod
    def _normalize_llm_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle llm configuration section

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "llm" in data:
            llm = data["llm"]
            normalized["llm_model"] = llm.get("model", "gpt-4")
            normalized["llm_max_concurrency"] = llm.get("max_concurrency", 4)
            normalized["llm_timeout"] = llm.get("timeout", 120)
            # LLM connection parameters
            for key in ("base_url", "api_key_env", "base_url_env", "temperature", "max_tokens"):
                if key in llm:
                    normalized[f"llm_{key}"] = llm[key]
        else:
            # Top-level llm_* keys are accepted for fully materialized configs.
            for key in (
                "llm_model", "llm_max_concurrency", "llm_timeout",
                "llm_base_url", "llm_api_key_env", "llm_base_url_env",
                "llm_temperature", "llm_max_tokens",
                "llm_retry_max_attempts", "llm_retry_base_delay", "llm_retry_max_delay",
            ):
                if key in data and key not in normalized:
                    normalized[key] = data[key]

    @staticmethod
    def _normalize_payloads_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle payloads/attack_types configuration section

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "payloads" in data:
            payloads = data["payloads"]
            normalized["attack_types"] = payloads.get("attack_types", [])
            normalized["injection_layers"] = payloads.get("injection_layers", [])
            normalized["severities"] = payloads.get("severities", [])
        elif "attack_types" in data:
            attack_types = data["attack_types"]
            if isinstance(attack_types, dict):
                normalized["attack_types"] = attack_types.get("enabled", [])
                normalized["severities"] = attack_types.get("severities", [])
            else:
                normalized["attack_types"] = attack_types

    @staticmethod
    def _normalize_script_selection_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle script_selection configuration section.

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "script_selection" in data:
            sel = data["script_selection"]
            if isinstance(sel, dict):
                normalized["script_selection_mode"] = sel.get("mode", "auto")
                if "mapping_file" in sel:
                    normalized["script_selection_mapping_file"] = sel["mapping_file"]
        # Also accept flat keys
        if "script_selection_mode" in data and "script_selection_mode" not in normalized:
            normalized["script_selection_mode"] = data["script_selection_mode"]
        if "script_selection_mapping_file" in data and "script_selection_mapping_file" not in normalized:
            normalized["script_selection_mapping_file"] = data["script_selection_mapping_file"]

    @staticmethod
    def _normalize_skills_section(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Handle skills configuration section

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        if "skills" in data:
            skills = data["skills"]
            normalized["skill_names"] = skills.get("target_names", [])

            # Compatible with different base_dir field names
            if "template_base_dir" not in normalized:
                base_dir = skills.get("base_dir", "data/skills_from_skill0")

                # Handle {dataset_base_dir} placeholder
                if "{dataset_base_dir}" in base_dir:
                    base_dir = base_dir.replace(
                        "{dataset_base_dir}",
                        normalized.get("dataset_base_dir", "data/skills_from_skill0"),
                    )

                normalized["template_base_dir"] = base_dir

            # Handle output_dir (supports simplified relative paths)
            if "template_output_dir" not in normalized:
                output_dir = skills.get("output_dir", "generated_tests")
                if not output_dir.startswith("/") and not output_dir.startswith("generated_tests"):
                    # Relative path, will build complete path in computed_output_dir
                    normalized["template_output_dir"] = output_dir
                else:
                    # Absolute path, maintain backward compatibility
                    normalized["template_output_dir"] = output_dir

    @staticmethod
    def _apply_top_level_overrides(data: dict[str, Any], normalized: dict[str, Any]) -> None:
        """Apply top-level configuration overrides

        Args:
            data: Original configuration data
            normalized: Normalized configuration dictionary (will be modified directly)
        """
        override_keys = [
            "attack_types",
            "injection_layers",
            "severities",
            "skill_names",
            "max_tests",
            "max_tests_per_skill",
            "save_metadata",
            "metadata_format",
        ]
        for key in override_keys:
            if key in data and key not in normalized:
                normalized[key] = data[key]

    @classmethod
    def _normalize_config(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize configuration data, support flat and nested structures

        Args:
            data: Original configuration data

        Returns:
            Normalized flat configuration dictionary
        """
        # Flat structure (main config file or backward compatible)
        if "method" not in data:
            return data.copy()

        # Nested structure (sub-config file format) - needs flattening
        normalized: dict[str, Any] = {}
        normalized["strategy"] = data.get("method", "template_injection")

        # Process dataset config first (other configs may depend on it)
        cls._normalize_dataset_section(data, normalized)

        # Process each config section
        cls._normalize_template_section(data, normalized)
        cls._normalize_llm_section(data, normalized)
        cls._normalize_payloads_section(data, normalized)
        cls._normalize_script_selection_section(data, normalized)
        cls._normalize_skills_section(data, normalized)

        # Process limits and output sections
        if "limits" in data:
            normalized["max_tests"] = data["limits"].get("max_tests")
        if "output" in data:
            normalized["save_metadata"] = data["output"].get("save_metadata", True)

        # Apply top-level overrides
        cls._apply_top_level_overrides(data, normalized)

        return normalized

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            GenerationConfig instance
        """
        # Normalize configuration data
        normalized = cls._normalize_config(data)

        # Parse strategy
        strategy_str = normalized.get("strategy", "template_injection")
        try:
            strategy = GenerationStrategy(strategy_str)
        except ValueError as exc:
            raise ValueError(f"Invalid generation strategy: {strategy_str}") from exc

        # Get dataset configuration
        dataset = normalized.get("dataset")
        if dataset is None:
            dataset = DatasetConfig()
        elif isinstance(dataset, dict):
            # If dataset is a dictionary, convert to DatasetConfig object
            dataset = DatasetConfig.from_dict(dataset)

        return cls(
            strategy=strategy,
            dataset=dataset,
            script_mapping_file=normalized.get("script_mapping_file"),
            script_selection_mode=normalized.get("script_selection_mode", "auto"),
            script_selection_mapping_file=normalized.get("script_selection_mapping_file"),
            # template_base_dir is None means automatically use dataset.base_dir
            template_base_dir=normalized.get("template_base_dir"),  # None means use dataset.base_dir
            template_output_dir=Path(normalized.get("template_output_dir", "generated_tests")),
            llm_model=normalized.get("llm_model", "gpt-4"),
            llm_max_concurrency=normalized.get("llm_max_concurrency", 4),
            llm_timeout=normalized.get("llm_timeout", 120),
            llm_base_url=normalized.get("llm_base_url", ""),
            llm_api_key_env=normalized.get("llm_api_key_env", ""),
            llm_base_url_env=normalized.get("llm_base_url_env", ""),
            llm_temperature=float(normalized.get("llm_temperature", 0.7)),
            llm_max_tokens=int(normalized.get("llm_max_tokens", 8192)),
            llm_retry_max_attempts=int(normalized.get("llm_retry_max_attempts", 3)),
            llm_retry_base_delay=float(normalized.get("llm_retry_base_delay", 1.0)),
            llm_retry_max_delay=float(normalized.get("llm_retry_max_delay", 30.0)),
            attack_types=normalized.get("attack_types", []),
            injection_layers=normalized.get("injection_layers", []),
            severities=normalized.get("severities", []),
            skill_names=normalized.get("skill_names", []),
            max_tests=normalized.get("max_tests"),
            max_tests_per_skill=normalized.get("max_tests_per_skill"),
            save_metadata=normalized.get("save_metadata", True),
            metadata_format=normalized.get("metadata_format", "json"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "strategy": self.strategy.value,
            "dataset": {
                "name": self.dataset.name,
                "base_dir": str(self.dataset.base_dir),
                **({"instruction_base_dir": str(self.dataset.instruction_base_dir)} if self.dataset.instruction_base_dir is not None else {}),
            },
            "template_base_dir": str(self.template_base_dir),
            "template_output_dir": str(self.template_output_dir),
            "llm_model": self.llm_model,
            "llm_max_concurrency": self.llm_max_concurrency,
            "llm_timeout": self.llm_timeout,
            "llm_base_url": self.llm_base_url,
            "llm_api_key_env": self.llm_api_key_env,
            "llm_base_url_env": self.llm_base_url_env,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_retry_max_attempts": self.llm_retry_max_attempts,
            "llm_retry_base_delay": self.llm_retry_base_delay,
            "llm_retry_max_delay": self.llm_retry_max_delay,
            "attack_types": self.attack_types,
            "injection_layers": self.injection_layers,
            "severities": self.severities,
            "skill_names": self.skill_names,
            "max_tests": self.max_tests,
            "max_tests_per_skill": self.max_tests_per_skill,
            "save_metadata": self.save_metadata,
            "metadata_format": self.metadata_format,
        }
        if self.script_mapping_file is not None:
            result["script_mapping_file"] = self.script_mapping_file
        result["script_selection_mode"] = self.script_selection_mode
        if self.script_selection_mapping_file is not None:
            result["script_selection_mapping_file"] = self.script_selection_mapping_file
        return result


@dataclass(frozen=True)
class SandboxConfig:
    """OpenSandbox connection configuration (value object)

    Defines parameters for connecting to OpenSandbox server
    """

    # Connection parameters
    domain: str
    api_key: str = ""
    request_timeout_seconds: int = 120

    # Container configuration
    image: str = "claude_code:latest"
    user_config: str = "claude_code"

    # Environment variable override priority
    env_domain_var: str = "SANDBOX_DOMAIN"
    env_api_key_var: str = "SANDBOX_API_KEY"
    env_image_var: str = "SANDBOX_IMAGE"

    def get_active_domain(self) -> str:
        """Get actual domain in use (environment variable takes priority)

        Returns:
            Actual domain in use
        """
        import os

        return os.getenv(self.env_domain_var, self.domain)

    def get_active_api_key(self) -> str:
        """Get actual api_key in use (environment variable takes priority)

        Returns:
            Actual api_key in use
        """
        import os

        return os.getenv(self.env_api_key_var, self.api_key)

    def get_active_image(self) -> str:
        """Get actual image in use (environment variable takes priority)

        Returns:
            Actual image in use
        """
        import os

        return os.getenv(self.env_image_var, self.image)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SandboxConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            SandboxConfig instance
        """
        return cls(
            domain=data.get("domain", "localhost:8080"),
            api_key=data.get("api_key", ""),
            request_timeout_seconds=data.get("request_timeout_seconds", 120),
            image=data.get("image", "claude_code:latest"),
            user_config=data.get("user_config", "claude_code"),
            env_domain_var=data.get("env_domain_var", "SANDBOX_DOMAIN"),
            env_api_key_var=data.get("env_api_key_var", "SANDBOX_API_KEY"),
            env_image_var=data.get("env_image_var", "SANDBOX_IMAGE"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "domain": self.domain,
            "api_key": self.api_key,
            "request_timeout_seconds": self.request_timeout_seconds,
            "image": self.image,
            "user_config": self.user_config,
            "env_domain_var": self.env_domain_var,
            "env_api_key_var": self.env_api_key_var,
            "env_image_var": self.env_image_var,
        }


@dataclass(frozen=True)
class AgentConfig:
    """Agent configuration (value object)

    Defines authentication and connection parameters for AI Agent
    """

    # Agent type
    agent_type: str = "claude-code"

    # Authentication environment variables (backward compatible)
    auth_token_env: str = "ANTHROPIC_AUTH_TOKEN"
    base_url_env: str = "ANTHROPIC_BASE_URL"
    model_env: str = "ANTHROPIC_MODEL"

    # New: Direct configuration fields (for dynamically injecting settings.json)
    provider: str = ""
    auth_token: str = ""  # For GLM/GPT/MiniMax (ANTHROPIC_AUTH_TOKEN)
    api_key: str = ""     # For Claude official API (ANTHROPIC_API_KEY)
    base_url: str = ""
    model: str = ""
    disable_traffic: str = "1"

    # New: Specify which authentication field to use
    # True=use api_key (Claude official API), False=use auth_token (other models)
    use_api_key: bool = False

    # Other configuration
    bypass_mode: bool = True  # Skip permission confirmation

    def get_auth_token(self) -> str:
        """Get authentication token

        Returns:
            Authentication token
        """
        import os

        token = os.getenv(self.auth_token_env, "")
        if not token:
            # Compatible with old environment variable name
            token = os.getenv("ANTHROPIC_API_KEY", "")
        return token

    def get_base_url(self) -> str | None:
        """Get API base URL

        Returns:
            API base URL or None
        """
        import os

        return os.getenv(self.base_url_env)

    def get_model(self) -> str | None:
        """Get model name

        Returns:
            Model name or None
        """
        import os

        return os.getenv(self.model_env)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            AgentConfig instance
        """
        # Set default environment variables based on agent_type
        agent_type = data.get("agent_type", "claude-code")

        # Environment variable mapping for each agent type
        agent_env_defaults: dict[str, tuple[str, str, str]] = {
            "claude-code": ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"),
            "openclaw": ("OPENCLAW_GATEWAY_TOKEN", "OPENCLAW_BASE_URL", "OPENCLAW_MODEL"),
        }

        if agent_type not in agent_env_defaults:
            supported = ", ".join(sorted(agent_env_defaults))
            raise ValueError(f"Unsupported agent_type: {agent_type}. Supported: {supported}")

        auth_env, url_env, model_env = agent_env_defaults[agent_type]

        return cls(
            agent_type=agent_type,
            auth_token_env=data.get("auth_token_env", auth_env),
            base_url_env=data.get("base_url_env", url_env),
            model_env=data.get("model_env", model_env),
            # New fields
            provider=data.get("provider", ""),
            auth_token=data.get("auth_token", ""),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            model=data.get("model", ""),
            disable_traffic=data.get("disable_traffic", "1"),
            use_api_key=data.get("use_api_key", False),
            bypass_mode=data.get("bypass_mode", True),
        )

    def _resolve_auth_token(self) -> str | None:
        """Resolve effective auth token (prefer config field, fallback to env var)"""
        if self.auth_token:
            return self.auth_token
        return os.getenv(self.auth_token_env)

    def _resolve_api_key(self) -> str | None:
        """Resolve effective API key (prefer config field, fallback to auth_token_env or ANTHROPIC_API_KEY)"""
        if self.api_key:
            return self.api_key
        # Fallback to auth_token_env (allows use_api_key=True with custom env var)
        token = os.getenv(self.auth_token_env)
        if token:
            return token
        # Last resort: ANTHROPIC_API_KEY
        return os.getenv("ANTHROPIC_API_KEY")

    def _resolve_base_url(self) -> str | None:
        """Resolve effective base URL (prefer config field, fallback to env var)"""
        if self.base_url:
            return self.base_url
        return os.getenv(self.base_url_env)

    def _resolve_model(self) -> str | None:
        """Resolve effective model (prefer config field, fallback to env var)"""
        if self.model:
            return self.model
        return os.getenv(self.model_env)

    def _resolve_provider(self) -> str | None:
        """Resolve effective provider name."""
        if self.provider:
            return self.provider
        return None

    def get_claude_settings(self) -> dict:
        """Generate Claude Code settings.json content

        Selects ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN based on use_api_key

        Returns:
            Dictionary content for settings.json
        """
        env_vars: dict[str, str] = {
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": self.disable_traffic,
        }

        # Select correct field name based on use_api_key
        if self.use_api_key:
            api_key = self._resolve_api_key()
            if api_key:
                env_vars["ANTHROPIC_API_KEY"] = api_key
        else:
            auth_token = self._resolve_auth_token()
            if auth_token:
                env_vars["ANTHROPIC_AUTH_TOKEN"] = auth_token

        # Add optional base_url (prefer config field, fallback to env var)
        base_url = self._resolve_base_url()
        if base_url:
            env_vars["ANTHROPIC_BASE_URL"] = base_url

        # Add optional model
        model = self._resolve_model()
        if model:
            env_vars["ANTHROPIC_MODEL"] = model

        return {
            "env": env_vars,
            "permissions": {"defaultMode": "bypassPermissions"}
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_type": self.agent_type,
            "auth_token_env": self.auth_token_env,
            "base_url_env": self.base_url_env,
            "model_env": self.model_env,
            "provider": self.provider,
            "auth_token": self.auth_token,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "disable_traffic": self.disable_traffic,
            "use_api_key": self.use_api_key,
            "bypass_mode": self.bypass_mode,
        }


@dataclass(frozen=True)
class Phase2ExecutionConfig:
    """Phase 2: Test execution configuration (value object)

    Defines all configuration parameters for test execution phase
    Each test uses an independent sandbox instance for concurrent execution
    """

    # Concurrency configuration
    max_concurrency: int

    # Timeout configuration (seconds)
    test_timeout: int
    command_timeout: int

    # Retry configuration
    retry_failed: bool
    max_retries: int

    # Monitoring configuration
    enable_network_monitoring: bool
    enable_process_monitoring: bool
    enable_container_monitoring: bool

    # Output configuration
    output_dir: Path
    save_detailed_logs: bool

    # Agent configuration (kept for compatibility)
    agent_type: str

    # Sandbox and Agent configuration
    sandbox: SandboxConfig
    agent: AgentConfig

    def __post_init__(self) -> None:
        """Validate configuration"""
        if not isinstance(self.output_dir, Path):
            object.__setattr__(self, "output_dir", Path(self.output_dir))

        if self.max_concurrency < MIN_CONCURRENCY:
            raise ValueError(f"max_concurrency must be greater than or equal to {MIN_CONCURRENCY}")

        if self.test_timeout < MIN_TIMEOUT:
            raise ValueError(f"test_timeout must be greater than or equal to {MIN_TIMEOUT}")

        if self.command_timeout < MIN_TIMEOUT:
            raise ValueError(f"command_timeout must be greater than or equal to {MIN_TIMEOUT}")

        if self.max_retries < MIN_RETRIES:
            raise ValueError(f"max_retries cannot be less than {MIN_RETRIES}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Phase2ExecutionConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            Phase2ExecutionConfig instance
        """
        monitoring = data.get("enable_monitoring", {})
        if monitoring is None:
            monitoring = {}

        # Load Sandbox configuration
        sandbox_data = data.get("sandbox", {})
        sandbox = SandboxConfig.from_dict(sandbox_data)

        # Load Agent configuration
        agent_data = data.get("agent", {})
        # agent_type can be specified either at execution level or in agent section
        # Priority: agent section > execution level > default
        agent_type = agent_data.get("agent_type") or data.get("agent_type", "claude-code")
        agent_data["agent_type"] = agent_type
        agent = AgentConfig.from_dict(agent_data)

        return cls(
            max_concurrency=data.get("max_concurrency", 4),
            test_timeout=data.get("test_timeout", 120),
            command_timeout=data.get("command_timeout", 300),
            retry_failed=data.get("retry_failed", True),
            max_retries=data.get("max_retries", 2),
            enable_network_monitoring=monitoring.get("network", True),
            enable_process_monitoring=monitoring.get("process", False),
            enable_container_monitoring=monitoring.get("container", False),
            output_dir=Path(data.get("output_dir", "experiment_results")),
            save_detailed_logs=data.get("save_detailed_logs", True),
            agent_type=data.get("agent_type", "claude-code"),
            sandbox=sandbox,
            agent=agent,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_concurrency": self.max_concurrency,
            "test_timeout": self.test_timeout,
            "command_timeout": self.command_timeout,
            "retry_failed": self.retry_failed,
            "max_retries": self.max_retries,
            "enable_monitoring": {
                "network": self.enable_network_monitoring,
                "process": self.enable_process_monitoring,
                "container": self.enable_container_monitoring,
            },
            "output_dir": str(self.output_dir),
            "save_detailed_logs": self.save_detailed_logs,
            "agent_type": self.agent_type,
            "sandbox": self.sandbox.to_dict(),
            "agent": self.agent.to_dict(),
        }


@dataclass(frozen=True)
class GlobalConfig:
    """Global configuration (value object)

    Defines global configuration parameters
    """

    verbose: bool
    log_level: LogLevel
    timestamp_format: str

    def __post_init__(self) -> None:
        """Validate configuration"""
        if isinstance(self.log_level, str):
            try:
                object.__setattr__(self, "log_level", LogLevel(self.log_level))
            except ValueError as exc:
                raise ValueError(f"Invalid log level: {self.log_level}") from exc

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlobalConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            GlobalConfig instance
        """
        log_level_str = data.get("log_level", "INFO")
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO

        return cls(
            verbose=data.get("verbose", False),
            log_level=log_level,
            timestamp_format=data.get("timestamp_format", "%Y-%m-%d %H:%M:%S"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "verbose": self.verbose,
            "log_level": self.log_level.value,
            "timestamp_format": self.timestamp_format,
        }


@dataclass(frozen=True)
class AdaptiveIterationConfig:
    """Adaptive iteration configuration (value object)

    Defines feedback-driven streaming test configuration parameters
    """

    max_attempts: int
    stop_on_success: bool

    def __post_init__(self) -> None:
        """Validate configuration"""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be greater than 0")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AdaptiveIterationConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary (None means use default values)

        Returns:
            AdaptiveIterationConfig instance
        """
        if data is None:
            data = {}

        return cls(
            max_attempts=data.get("max_attempts", 3),
            stop_on_success=data.get("stop_on_success", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_attempts": self.max_attempts,
            "stop_on_success": self.stop_on_success,
        }


@dataclass(frozen=True)
class TwoPhaseExecutionConfig:
    """Two-phase execution configuration (aggregate value object)

    Contains complete two-phase framework configuration
    """

    generation: GenerationConfig
    execution: Phase2ExecutionConfig
    global_config: GlobalConfig
    adaptive_iteration: AdaptiveIterationConfig
    judge: JudgeConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "generation": self.generation.to_dict(),
            "execution": self.execution.to_dict(),
            "global": self.global_config.to_dict(),
            "adaptive_iteration": self.adaptive_iteration.to_dict(),
        }
        if self.judge is not None:
            result["judge"] = self.judge.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TwoPhaseExecutionConfig":
        """Create configuration from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            TwoPhaseExecutionConfig instance
        """
        judge_data = data.get("judge")
        judge_cfg = JudgeConfig.from_dict(judge_data) if judge_data else None

        return cls(
            generation=GenerationConfig.from_dict(data.get("generation", {})),
            execution=Phase2ExecutionConfig.from_dict(data.get("execution", {})),
            global_config=GlobalConfig.from_dict(data.get("global", {})),
            adaptive_iteration=AdaptiveIterationConfig.from_dict(data.get("adaptive_iteration")),
            judge=judge_cfg,
        )

    def validate(self) -> list[str]:
        """Validate complete configuration

        Returns:
            Error list (empty list means valid)
        """
        errors = []

        # Validate generation configuration
        try:
            GenerationConfig.from_dict(self.generation.to_dict())
        except ValueError as e:
            errors.append(f"Generation configuration error: {e}")

        # Validate execution configuration
        try:
            Phase2ExecutionConfig.from_dict(self.execution.to_dict())
        except ValueError as e:
            errors.append(f"Execution configuration error: {e}")

        # Validate global configuration
        try:
            GlobalConfig.from_dict(self.global_config.to_dict())
        except ValueError as e:
            errors.append(f"Global configuration error: {e}")

        # Validate adaptive iteration configuration
        try:
            AdaptiveIterationConfig.from_dict(self.adaptive_iteration.to_dict())
        except ValueError as e:
            errors.append(f"Adaptive iteration configuration error: {e}")

        return errors
