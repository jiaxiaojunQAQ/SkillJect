"""
Configuration Loader

Responsible for loading and parsing the evaluation framework's configuration files.
"""

from pathlib import Path
from typing import Any

from src.domain.testing.value_objects.execution_config import (
    AdaptiveIterationConfig,
    GenerationConfig,
    GlobalConfig,
    Phase2ExecutionConfig,
    TwoPhaseExecutionConfig,
)
from src.infrastructure.config.loaders.file_loader import FileConfigLoader
from src.infrastructure.config.loaders.profile_config_loader import ProfileConfigLoader
from src.shared.exceptions import ConfigurationError


class ConfigLoader:
    """Configuration Loader

    Loads evaluation framework configuration from YAML files.
    Supports the profile-based configuration format.
    """

    DEFAULT_CONFIG_PATH = Path("config/main.yaml")

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        profile: str | None = None,
    ) -> TwoPhaseExecutionConfig:
        """Load evaluation configuration.

        Args:
            config_path: Configuration file path (uses default path if None)
            profile: Profile name (for profile-based configs)

        Returns:
            Execution configuration

        Raises:
            ConfigurationError: Configuration file does not exist or has invalid format
        """
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH

        config_path = Path(config_path)

        if cls._is_profile_config(config_path):
            return cls._load_profile_config(config_path, profile)

        raise ConfigurationError(
            f"Unsupported configuration format: {config_path}. "
            "Use config/main.yaml or another execution-plan YAML file."
        )

    @classmethod
    def _is_profile_config(cls, config_path: Path) -> bool:
        """Check if config is using new profile-based format

        Args:
            config_path: Configuration file path

        Returns:
            True if profile-based config
        """
        normalized = config_path.as_posix()

        if normalized.endswith("config/main.yaml") or normalized == "config/main.yaml":
            return True

        try:
            data = FileConfigLoader.load_yaml(config_path)
        except ConfigurationError:
            return False

        if "execution_plan" in data:
            return True

        return False

    @classmethod
    def _load_profile_config(
        cls,
        config_path: Path,
        profile: str | None = None,
    ) -> TwoPhaseExecutionConfig:
        """Load profile-based configuration

        Args:
            config_path: Main config file path
            profile: Profile name override

        Returns:
            Execution configuration
        """
        try:
            config_data = ProfileConfigLoader.load(config_path, profile)
        except Exception as e:
            raise ConfigurationError(f"Failed to load profile configuration: {e}") from e

        # Parse configuration
        try:
            return cls._parse_config(config_data, config_path)
        except ValueError as e:
            raise ConfigurationError(f"Failed to parse configuration: {e}") from e

    @classmethod
    def _parse_config(
        cls,
        data: dict[str, Any],
        config_file_path: str | Path | None = None,
    ) -> TwoPhaseExecutionConfig:
        """Parse configuration data.

        Args:
            data: Configuration data dictionary
            config_file_path: Main configuration file path (for resolving relative paths)

        Returns:
            Execution configuration

        Raises:
            ValueError: Invalid configuration format
        """
        # Parse each configuration section
        generation_data = data.get("generation", {})
        execution_data = data.get("execution", {}).copy()
        global_data = data.get("global", {})
        adaptive_iteration_data = data.get("adaptive_iteration")
        judge_data = data.get("llm_judge")
        dataset_data = data.get("dataset")
        instruction_data = data.get("instruction")

        execution_data = cls._promote_profile_sections(data, execution_data)

        if "config_file" in generation_data:
            raise ConfigurationError(
                "generation.config_file is no longer supported. "
                "Select a public generation method with generation.method."
            )

        # If main config has dataset config, merge into generation_data
        # Prefer main config's dataset (this is usually what users want to override)
        if dataset_data is not None:
            from src.domain.testing.value_objects.execution_config import DatasetConfig

            if isinstance(dataset_data, dict):
                # Merge top-level instruction into dataset dict
                if instruction_data is not None:
                    dataset_data = {**dataset_data, "instruction_base_dir": instruction_data}
                generation_data["dataset"] = DatasetConfig.from_dict(dataset_data)
            elif isinstance(dataset_data, str):
                ds = DatasetConfig.from_dict(dataset_data)
                if instruction_data is not None:
                    ds = DatasetConfig(
                        name=ds.name,
                        base_dir=ds.base_dir,
                        instruction_base_dir=Path(instruction_data),
                    )
                generation_data["dataset"] = ds
            else:
                generation_data["dataset"] = dataset_data
        elif instruction_data is not None:
            # instruction given without dataset -- apply to default dataset
            from src.domain.testing.value_objects.execution_config import DatasetConfig

            generation_data["dataset"] = DatasetConfig(
                instruction_base_dir=Path(instruction_data),
            )

        # Create configuration objects
        # Note: GenerationConfig.from_dict handles dataset conversion
        generation = GenerationConfig.from_dict(generation_data)
        execution = Phase2ExecutionConfig.from_dict(execution_data)
        global_config = GlobalConfig.from_dict(global_data)
        adaptive_iteration = AdaptiveIterationConfig.from_dict(adaptive_iteration_data if adaptive_iteration_data else {})

        # Build final config with optional judge section
        config_kwargs: dict[str, Any] = {
            "generation": generation,
            "execution": execution,
            "global_config": global_config,
            "adaptive_iteration": adaptive_iteration,
        }
        if judge_data:
            from src.domain.analysis.value_objects.judge_config import JudgeConfig
            config_kwargs["judge"] = JudgeConfig.from_dict(judge_data)

        # Combine complete configuration
        return TwoPhaseExecutionConfig(**config_kwargs)

    @classmethod
    def _promote_profile_sections(
        cls,
        data: dict[str, Any],
        execution_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Promote top-level profile sections into legacy execution.* shape."""
        promoted = execution_data.copy()

        execution_keys = {
            "max_concurrency",
            "test_timeout",
            "command_timeout",
            "retry_failed",
            "max_retries",
            "save_detailed_logs",
        }
        for key in execution_keys:
            if key in data and key not in promoted:
                promoted[key] = data[key]

        top_level_agent = data.get("agent")
        if isinstance(top_level_agent, dict):
            merged_agent = promoted.get("agent", {}).copy()
            merged_agent.update(top_level_agent)
            if "type" in merged_agent and "agent_type" not in merged_agent:
                merged_agent["agent_type"] = merged_agent["type"]
            promoted["agent"] = merged_agent

        agent_runtime_keys = {
            "provider",
            "auth_token_env",
            "base_url_env",
            "model_env",
            "auth_token",
            "api_key",
            "base_url",
            "model",
            "disable_traffic",
            "use_api_key",
            "bypass_mode",
        }
        merged_agent = promoted.get("agent", {}).copy()
        for key in agent_runtime_keys:
            if key in data and key not in merged_agent:
                merged_agent[key] = data[key]

        profile_data = data.get("profile")
        if isinstance(profile_data, dict):
            profile_model = profile_data.get("model")
            if profile_model and "model" not in merged_agent:
                merged_agent["model"] = profile_model

        if merged_agent:
            promoted["agent"] = merged_agent

        top_level_sandbox = data.get("sandbox")
        if isinstance(top_level_sandbox, dict):
            merged_sandbox = promoted.get("sandbox", {}).copy()
            merged_sandbox.update(top_level_sandbox)
            promoted["sandbox"] = merged_sandbox

        return promoted

# mypy: disable-error-code="union-attr,no-untyped-def"
