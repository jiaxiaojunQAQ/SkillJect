"""
Profile Configuration Loader

Supports loading configuration from profile-based architecture with extends support.
"""

from pathlib import Path
from typing import Any

from src.infrastructure.config.loaders.file_loader import FileConfigLoader
from src.shared.exceptions import ConfigurationError


class ProfileConfigLoader:
    """Profile-based configuration loader with extends support

    Supports:
    - Loading profiles from config/profiles/
    - Resolving extends chains (recursively loading base configs)
    - Merging configurations with YAML anchor resolution
    """

    CONFIG_DIR = Path("config")

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Load configuration with profile support

        Args:
            config_path: Main execution-plan config path (normally config/main.yaml)
            profile: Profile name selected by the execution plan

        Returns:
            Merged configuration dictionary

        Raises:
            ConfigurationError: Configuration file does not exist or is invalid
        """
        # Load main config
        config_path = Path(config_path) if config_path else cls.CONFIG_DIR / "main.yaml"
        FileConfigLoader.load_yaml(config_path)

        if not profile:
            raise ConfigurationError(
                "Profile name is required. Select a profile from execution_plan in config/main.yaml."
            )
        profile_name = profile

        # Load profile configuration
        profile_path = cls.CONFIG_DIR / "profiles" / f"{profile_name}.yaml"
        if not profile_path.exists():
            raise ConfigurationError(f"Profile not found: {profile_name} (expected: {profile_path})")

        profile_config = FileConfigLoader.load_yaml(profile_path)

        # Resolve extends and merge configurations
        final_config = cls._resolve_extends(profile_config)

        return final_config

    @classmethod
    def _resolve_extends(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve extends chain and merge configurations

        Recursively loads base configs specified in extends field
        and merges them with the current config.

        Args:
            config: Configuration dictionary with extends field

        Returns:
            Merged configuration dictionary
        """
        extends_list = config.get("extends", [])
        if not isinstance(extends_list, list):
            extends_list = [extends_list]

        # Start with an empty base config
        merged_config: dict[str, Any] = {}

        # Load and merge each base config in order
        for extend in extends_list:
            base_config = cls._load_base_config(extend)
            base_merged = cls._resolve_extends(base_config)
            merged_config = cls._deep_merge(merged_config, base_merged)

        # Finally merge with current config (current config takes precedence)
        merged_config = cls._deep_merge(merged_config, config)

        return merged_config

    @classmethod
    def _load_base_config(cls, extend: str) -> dict[str, Any]:
        """Load base configuration

        Args:
            extend: Base config name or path (e.g., "base/common" or "base/execution")

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: Base config not found
        """
        # Check if it's a full path or just a name
        if "/" in extend or extend.endswith(".yaml"):
            # Relative path like "base/common" or absolute path
            # Relative paths are relative to CONFIG_DIR
            if Path(extend).is_absolute():
                base_path = Path(extend)
            else:
                base_path = cls.CONFIG_DIR / extend
                # Add .yaml if no extension
                if not base_path.suffix:
                    base_path = Path(str(base_path) + ".yaml")
        else:
            # Simple name like "common" -> config/base/common.yaml
            base_path = cls.CONFIG_DIR / "base" / f"{extend}.yaml"

        if not base_path.exists():
            raise ConfigurationError(f"Base config not found: {extend} (expected: {base_path})")

        return FileConfigLoader.load_yaml(base_path)

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries

        Override values take precedence over base values.
        Lists are replaced (not merged).

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key.startswith('_'):
                # Skip YAML anchor definitions (keys starting with _)
                continue
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = cls._deep_merge(result[key], value)
            else:
                # Override with new value (including None values)
                result[key] = value

        return result

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List all available profiles

        Returns:
            List of profile names
        """
        profiles_dir = cls.CONFIG_DIR / "profiles"
        if not profiles_dir.exists():
            return []

        profiles = []
        for profile_file in profiles_dir.glob("*.yaml"):
            profiles.append(profile_file.stem)

        return sorted(profiles)

    @classmethod
    def get_profile_info(cls, profile_name: str) -> dict[str, Any]:
        """Get profile information

        Args:
            profile_name: Profile name

        Returns:
            Profile information dictionary
        """
        profile_path = cls.CONFIG_DIR / "profiles" / f"{profile_name}.yaml"
        if not profile_path.exists():
            raise ConfigurationError(f"Profile not found: {profile_name}")

        profile_config = FileConfigLoader.load_yaml(profile_path)

        return {
            "name": profile_name,
            "description": profile_config.get("profile", {}).get("description", ""),
            "agent": profile_config.get("profile", {}).get("agent", ""),
            "model": profile_config.get("profile", {}).get("model", ""),
            "output_dir": profile_config.get("execution", {}).get("output_dir", ""),
        }
