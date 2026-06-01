"""
Environment Variable Configuration Loader

Loads configuration from environment variables with type conversion and prefix filtering.
"""

import os
from typing import Any


class EnvConfigLoader:
    """Environment Variable Configuration Loader

    Provides environment variable to configuration mapping with type conversion.
    """

    # Default environment variable mappings
    DEFAULT_MAPPINGS = {
        "SANDBOX_DOMAIN": "sandbox.domain",
        "SANDBOX_API_KEY": "sandbox.api_key",
        "SANDBOX_IMAGE": "sandbox.image",
        "SANDBOX_USER": "sandbox.user_config",
        "SANDBOX_REQUEST_TIMEOUT": "sandbox.request_timeout",
        "BYPASS_MODE": "sandbox.bypass_mode",
        "MAX_CONCURRENCY": "test.max_concurrency",
        "COMMAND_TIMEOUT": "test.command_timeout",
        "MAX_TESTS": "test.max_tests",
        "OUTPUT_DIR": "log.output_dir",
        "ANTHROPIC_AUTH_TOKEN": "claude.auth_token",
        "ANTHROPIC_BASE_URL": "claude.base_url",
        "ANTHROPIC_MODEL": "claude.model",
        "SECURITY_TEST_DIR": "paths.test_dir",
        "EXPERIMENT_OUTPUT_DIR": "paths.output_dir",
        "SKILLS_FROM_SKILL0_DIR": "paths.skills_dir",
        "SKILLS_INSTRUCTIONS_DIR": "paths.instructions_dir",
    }

    @staticmethod
    def load(
        prefix: str = "",
        mappings: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Load environment variables as configuration dictionary.

        Args:
            prefix: Environment variable prefix filter (e.g., "SECURITY_")
            mappings: Environment variable to configuration key mapping

        Returns:
            Configuration dictionary
        """
        mappings = mappings or EnvConfigLoader.DEFAULT_MAPPINGS
        config = {}

        for env_var, config_key in mappings.items():
            # Apply prefix filter
            if prefix and not env_var.startswith(prefix):
                continue

            value = os.getenv(env_var)
            if value is not None:
                config[config_key] = EnvConfigLoader._convert_type(value)

        return config

    @staticmethod
    def load_with_prefix(prefix: str) -> dict[str, Any]:
        """Load all environment variables with specified prefix.

        Args:
            prefix: Environment variable prefix (e.g., "SECURITY_")

        Returns:
            Configuration dictionary (keys are lowercase env vars with prefix removed)
        """
        config = {}
        prefix_upper = prefix.upper()

        for env_var, value in os.environ.items():
            if env_var.startswith(prefix_upper):
                # Remove prefix, convert to config key format
                key = env_var[len(prefix_upper) :].lower()
                # Replace __ with .
                key = key.replace("__", ".")
                # Replace _ with . (but not consecutive _)
                if "__" not in env_var:
                    key = key.replace("_", ".")

                config[key] = EnvConfigLoader._convert_type(value)

        return config

    @staticmethod
    def _convert_type(value: str) -> Any:
        """Automatically convert string value type.

        Args:
            value: String value

        Returns:
            Converted value (bool, int, float, or str)
        """
        # Boolean values
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        if value.lower() in ("false", "no", "off", "0"):
            return False

        # Integer
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # Default to string
        return value

    @staticmethod
    def get(env_var: str, default: Any = None) -> Any:
        """Get environment variable with automatic type conversion.

        Args:
            env_var: Environment variable name
            default: Default value

        Returns:
            Environment variable value (converted) or default value
        """
        value = os.getenv(env_var)
        if value is None:
            return default

        return EnvConfigLoader._convert_type(value)

    @staticmethod
    def set(env_var: str, value: Any) -> None:
        """Set environment variable.

        Args:
            env_var: Environment variable name
            value: Value to set
        """
        os.environ[env_var] = str(value)

    @staticmethod
    def require(env_var: str) -> Any:
        """Get required environment variable.

        Args:
            env_var: Environment variable name

        Returns:
            Environment variable value (converted)

        Raises:
            ValueError: Environment variable does not exist
        """
        value = os.getenv(env_var)
        if value is None:
            raise ValueError(f"Required environment variable not set: {env_var}")

        return EnvConfigLoader._convert_type(value)
