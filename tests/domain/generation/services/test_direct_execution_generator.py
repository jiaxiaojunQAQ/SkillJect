from pathlib import Path

# mypy: disable-error-code="union-attr"
import pytest

from src.domain.generation.services.direct_execution_generator import DirectExecutionGenerator
from src.domain.generation.services.script_selector import MappingScriptSelector
from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.shared.types import AttackType


@pytest.mark.asyncio
async def test_direct_execution_scans_dataset_skills_and_skips_missing_instruction(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"

    (skill_base / "with_instruction").mkdir(parents=True)
    (skill_base / "with_instruction" / "SKILL.md").write_text("skill", encoding="utf-8")
    (instruction_base / "with_instruction").mkdir(parents=True)
    (instruction_base / "with_instruction" / "instruction.md").write_text("do it", encoding="utf-8")

    (skill_base / "missing_instruction").mkdir(parents=True)
    (skill_base / "missing_instruction" / "SKILL.md").write_text("skill", encoding="utf-8")

    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        '{"with_instruction": "run_with_instruction.sh", "missing_instruction": "run_missing_instruction.sh"}',
        encoding="utf-8",
    )

    config = GenerationConfig.from_dict(
        {
            "strategy": "direct_execution",
            "dataset": {
                "name": "test_dataset",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(instruction_base),
            },
        }
    )

    selector = MappingScriptSelector(mapping_file)
    generator = DirectExecutionGenerator(config=config, script_selector=selector)
    suite = await generator.generate()

    assert len(suite.test_cases) == 1
    assert suite.test_cases[0].test_id == "with_instruction"
    assert suite.metadata["generated_count"] == 1
    assert suite.metadata["skipped_count"] == 1


def test_direct_execution_requires_script_selector(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"
    (skill_base / "s1").mkdir(parents=True)
    (skill_base / "s1" / "SKILL.md").write_text("skill", encoding="utf-8")
    (instruction_base / "s1").mkdir(parents=True)
    (instruction_base / "s1" / "instruction.md").write_text("do it", encoding="utf-8")

    config = GenerationConfig.from_dict(
        {
            "strategy": "direct_execution",
            "dataset": {
                "name": "test_dataset",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(instruction_base),
            },
        }
    )

    with pytest.raises(ValueError, match="script_selector"):
        DirectExecutionGenerator(config=config)


@pytest.mark.asyncio
async def test_direct_execution_resolves_mapping(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"

    (skill_base / "s1").mkdir(parents=True)
    (skill_base / "s1" / "SKILL.md").write_text("skill", encoding="utf-8")
    (instruction_base / "s1").mkdir(parents=True)
    (instruction_base / "s1" / "instruction.md").write_text("do it", encoding="utf-8")

    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        '{"s1": "run_s1.sh"}',
        encoding="utf-8",
    )

    config = GenerationConfig.from_dict(
        {
            "strategy": "direct_execution",
            "dataset": {
                "name": "test_dataset",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(instruction_base),
            },
        }
    )

    selector = MappingScriptSelector(mapping_file)
    generator = DirectExecutionGenerator(config=config, script_selector=selector)
    tc = await generator.generate_stream_with_feedback(
        skill_name="s1",
        attack_type=AttackType.DIRECT,
        adaptive_params=type("AP", (), {"iteration_number": 0})(),
    )

    assert tc is not None
    assert tc.metadata["task_script"] == "run_s1.sh"
