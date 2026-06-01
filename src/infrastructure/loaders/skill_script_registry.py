"""
Skill Script Registry

Loads skill -> task_script mapping from configured JSON file.

Format: { "skill_name": "task_script", ... }
"""

import json
import logging
from pathlib import Path

from src.infrastructure.loaders.paths import resolve_data_path

logger = logging.getLogger(__name__)


class SkillScriptRegistry:
    """Registry for skill -> task_script mapping.

    The mapping file path must be explicitly provided by configuration.
    """

    def __init__(self, mapping_file: str | Path):
        if not mapping_file:
            raise ValueError("task_script mapping file must be configured")
        self._mapping_path = resolve_data_path(mapping_file)
        self._cache: dict[str, str] | None = None

    @property
    def mapping_path(self) -> Path:
        return self._mapping_path

    def load_mapping(self) -> dict[str, str]:
        """Load mapping JSON as flat { skill_name: task_script } dict."""
        if self._cache is not None:
            return self._cache

        if not self._mapping_path.exists():
            raise FileNotFoundError(f"task_script mapping file not found: {self._mapping_path}")

        with open(self._mapping_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(
                f"invalid task_script mapping format in {self._mapping_path}: expected flat object"
            )

        # Validate all values are strings
        mapping: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, str) and isinstance(key, str):
                mapping[key] = value

        logger.info(
            "SkillScriptRegistry: loaded %d mappings from %s",
            len(mapping),
            self._mapping_path,
        )
        self._cache = mapping
        return mapping

    def get_task_script(self, skill_name: str) -> str | None:
        return self.load_mapping().get(skill_name)


__all__ = ["SkillScriptRegistry"]
