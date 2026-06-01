from pathlib import Path

from src.domain.testing.value_objects.execution_config import DatasetConfig
from src.infrastructure.loaders.skill_data_resolver import SkillDataResolver


def test_skill_data_resolver_lists_and_finds_files(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"

    (skill_base / "alpha").mkdir(parents=True)
    (skill_base / "alpha" / "SKILL.md").write_text("alpha", encoding="utf-8")
    (skill_base / "beta").mkdir(parents=True)
    (skill_base / "beta" / "README.md").write_text("no skill", encoding="utf-8")
    (skill_base / "gamma").mkdir(parents=True)
    (skill_base / "gamma" / "SKILL.md").write_text("gamma", encoding="utf-8")

    (instruction_base / "alpha").mkdir(parents=True)
    (instruction_base / "alpha" / "instruction.md").write_text("do alpha", encoding="utf-8")

    dataset = DatasetConfig(
        name="custom",
        base_dir=skill_base,
        instruction_base_dir=instruction_base,
    )
    resolver = SkillDataResolver(dataset)

    assert resolver.list_skill_names() == ["alpha", "gamma"]
    assert resolver.find_skill_file("alpha") == skill_base / "alpha" / "SKILL.md"
    assert resolver.find_skill_file("beta") is None

    assert resolver.find_instruction_file("alpha") == instruction_base / "alpha" / "instruction.md"
    assert resolver.find_instruction_file("gamma") is None

    filtered = resolver.scan_skill_files(["gamma"])
    assert filtered == [skill_base / "gamma" / "SKILL.md"]
