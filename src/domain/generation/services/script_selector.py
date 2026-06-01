"""
Unified Script Selector

Two modes for injection script selection:
- random: randomly pick a script from data/bash_scripts/{attack_type}/
- mapping: look up skill_name -> script_path from a JSON mapping file
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.shared.types import AttackType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkippedSkill:
    """Record of a skill skipped due to missing script."""

    skill_name: str
    attack_type: str
    reason: str


class ScriptSelector(Protocol):
    """Protocol for script selection strategies."""

    def select(self, skill_name: str, attack_type: AttackType) -> Path | None:
        """Select a script for the given skill and attack type.

        Returns:
            Path to the script file, or None if the skill should be skipped.
        """
        ...


class RandomScriptSelector:
    """Select a random script from the attack_type subdirectory."""

    def __init__(self, scripts_base_dir: Path) -> None:
        self._scripts_base_dir = scripts_base_dir

    def select(self, skill_name: str, attack_type: AttackType) -> Path | None:
        script_dir = self._scripts_base_dir / attack_type.value
        if not script_dir.exists() or not script_dir.is_dir():
            logger.warning("[ScriptSelector] Directory not found: %s", script_dir)
            return None

        candidates = [
            p for p in script_dir.iterdir()
            if p.is_file() and "__pycache__" not in str(p)
        ]
        if not candidates:
            logger.warning("[ScriptSelector] No scripts in: %s", script_dir)
            return None

        chosen = random.choice(candidates)
        logger.debug(
            "[ScriptSelector] Random: %s for skill=%s attack=%s",
            chosen.name, skill_name, attack_type.value,
        )
        return chosen


class MappingScriptSelector:
    """Select a script by looking up skill_name in a JSON mapping file.

    Mapping format: { "skill_name": "path/to/script.sh", ... }
    """

    def __init__(self, mapping_file: Path) -> None:
        self._mapping_file = mapping_file
        self._cache: dict[str, str] | None = None

    def _load_mapping(self) -> dict[str, str]:
        if self._cache is not None:
            return self._cache

        if not self._mapping_file.exists():
            raise FileNotFoundError(
                f"Script mapping file not found: {self._mapping_file}"
            )

        with open(self._mapping_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(
                f"Invalid mapping format in {self._mapping_file}: expected flat object"
            )

        mapping: dict[str, str] = {
            k: v for k, v in data.items()
            if isinstance(k, str) and isinstance(v, str)
        }
        logger.info(
            "[ScriptSelector] Loaded %d mappings from %s",
            len(mapping), self._mapping_file,
        )
        self._cache = mapping
        return mapping

    def select(self, skill_name: str, attack_type: AttackType) -> Path | None:
        mapping = self._load_mapping()
        script_path_str = mapping.get(skill_name)
        if script_path_str is None:
            return None

        script_path = Path(script_path_str)
        if not script_path.is_absolute():
            # Resolve relative to project root
            from src.infrastructure.loaders.paths import resolve_data_path
            script_path = resolve_data_path(script_path_str)

        return script_path
