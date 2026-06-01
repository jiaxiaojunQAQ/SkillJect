"""
File Configuration Loader

Loads configuration from file system, supporting multiple formats.
"""

import json
from pathlib import Path
from typing import Any

from src.shared.exceptions import ConfigurationError


class FileConfigLoader:
    """File Configuration Loader

    Supports YAML, JSON, TOML format configuration files.
    """

    @staticmethod
    def load_yaml(path: str | Path) -> dict[str, Any]:
        """Load YAML configuration file.

        Args:
            path: YAML file path

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: File does not exist or has invalid format
        """
        path = Path(path)

        if not path.exists():
            raise ConfigurationError(f"Configuration file does not exist: {path}")

        try:
            import yaml

            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if not isinstance(data, dict):
                raise ConfigurationError("Invalid configuration file format: root must be a dictionary")

            return data

        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML parsing failed: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}") from e

    @staticmethod
    def load_json(path: str | Path) -> dict[str, Any]:
        """Load JSON configuration file.

        Args:
            path: JSON file path

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: File does not exist or has invalid format
        """
        path = Path(path)

        if not path.exists():
            raise ConfigurationError(f"Configuration file does not exist: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ConfigurationError("Invalid configuration file format: root must be a dictionary")

            return data

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"JSON parsing failed: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}") from e

    @staticmethod
    def load_toml(path: str | Path) -> dict[str, Any]:
        """Load TOML configuration file.

        Args:
            path: TOML file path

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: File does not exist or has invalid format
        """
        path = Path(path)

        if not path.exists():
            raise ConfigurationError(f"Configuration file does not exist: {path}")

        try:
            import tomllib

            with open(path, "rb") as f:
                data = tomllib.load(f)

            return data

        except Exception as e:
            # Python < 3.11 may not have tomllib
            try:
                import tomli

                with open(path, "rb") as f:
                    data = tomli.load(f)

                return data

            except ImportError:
                raise ConfigurationError("Need to install tomli or Python 3.11+ for TOML support") from e
            except Exception as e2:
                raise ConfigurationError(f"TOML parsing failed: {e2}") from e2

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        """Automatically select loader based on file extension.

        Args:
            path: Configuration file path

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: File does not exist or unsupported format
        """
        path = Path(path)
        suffix = path.suffix.lower()

        loaders = {
            ".yaml": FileConfigLoader.load_yaml,
            ".yml": FileConfigLoader.load_yaml,
            ".json": FileConfigLoader.load_json,
            ".toml": FileConfigLoader.load_toml,
        }

        loader = loaders.get(suffix)
        if not loader:
            raise ConfigurationError(f"Unsupported configuration file format: {suffix}")

        return loader(path)

    @staticmethod
    def save_yaml(data: dict[str, Any], path: str | Path) -> None:
        """Save as YAML file.

        Args:
            data: Configuration data
            path: Output path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import yaml

            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save YAML file: {e}") from e

    @staticmethod
    def save_json(data: dict[str, Any], path: str | Path, indent: int = 2) -> None:
        """Save as JSON file.

        Args:
            data: Configuration data
            path: Output path
            indent: Number of spaces for indentation
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save JSON file: {e}") from e

    @staticmethod
    def find_config_files(
        directory: str | Path,
        names: list[str] | None = None,
    ) -> list[Path]:
        """Find configuration files in directory.

        Args:
            directory: Search directory
            names: Configuration file name list (e.g., ["config.yaml", ".clauderc"])

        Returns:
            List of found configuration file paths
        """
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            return []

        default_names = ["config.yaml", "config.yml", ".clauderc", "settings.json"]
        search_names = names or default_names

        found = []
        for name in search_names:
            path = directory / name
            if path.exists():
                found.append(path)

        return found
# mypy: disable-error-code="import-not-found,no-any-return"
