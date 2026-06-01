from pathlib import Path

import pytest

from src.infrastructure.loaders.skill_script_registry import SkillScriptRegistry


def test_skill_script_registry_reads_flat_mapping(tmp_path: Path) -> None:
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        '{"INST-1_docx_task3": "file_backup.py", "INST-9_git": "add_backup_endpoint.sh"}',
        encoding="utf-8",
    )

    registry = SkillScriptRegistry(mapping_file)

    assert registry.get_task_script("INST-1_docx_task3") == "file_backup.py"
    assert registry.get_task_script("INST-9_git") == "add_backup_endpoint.sh"
    assert registry.get_task_script("nonexistent") is None


def test_skill_script_registry_requires_existing_mapping_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    registry = SkillScriptRegistry(missing)
    with pytest.raises(FileNotFoundError):
        registry.load_mapping()
