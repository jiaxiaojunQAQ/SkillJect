"""
Skill Data Resolver

Unifies skill and instruction path resolution across generation strategies.
"""

from pathlib import Path

from src.domain.testing.value_objects.execution_config import DatasetConfig
from src.infrastructure.loaders.paths import resolve_data_path


class SkillDataResolver:
    """Resolve skills and instructions from dataset configuration."""

    def __init__(self, dataset: DatasetConfig):
        self._dataset = dataset
        self._skill_base_dir = resolve_data_path(dataset.base_dir)
        self._instruction_base_dir = resolve_data_path(dataset.resolved_instruction_base_dir)

    @property
    def skill_base_dir(self) -> Path:
        return self._skill_base_dir

    @property
    def instruction_base_dir(self) -> Path:
        return self._instruction_base_dir

    def list_skill_names(self) -> list[str]:
        """List skill names from dataset.base_dir/<skill>/SKILL.md."""
        if not self._skill_base_dir.exists():
            return []

        return sorted(
            d.name for d in self._skill_base_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        )

    def scan_skill_files(self, allowed_skill_names: list[str] | None = None) -> list[Path]:
        """List SKILL.md files under dataset.base_dir, optionally filtered by skill names."""
        skill_names = self.list_skill_names()
        if allowed_skill_names:
            allowed = set(allowed_skill_names)
            skill_names = [name for name in skill_names if name in allowed]
        return [self._skill_base_dir / name / "SKILL.md" for name in skill_names]

    def find_skill_file(self, skill_name: str) -> Path | None:
        """Return dataset.base_dir/<skill_name>/SKILL.md if it exists."""
        if not self._skill_base_dir.exists():
            return None

        skill_file = self._skill_base_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            return skill_file
        return None

    def find_instruction_file(self, skill_name: str) -> Path | None:
        """Return dataset.instruction_base_dir/<skill_name>/instruction.md if it exists."""
        if not self._instruction_base_dir.exists():
            return None

        instruction_file = self._instruction_base_dir / skill_name / "instruction.md"
        if instruction_file.exists():
            return instruction_file
        return None
