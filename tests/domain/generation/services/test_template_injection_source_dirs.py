# mypy: disable-error-code="union-attr"
from pathlib import Path

import pytest

from src.domain.generation.services.template_injection_generator import TemplateInjectionGenerator
from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.shared.types import AttackType


@pytest.mark.asyncio
async def test_template_feedback_generation_sets_runtime_source_skill_dir(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"
    out_dir = tmp_path / "out"

    (skill_base / "demo").mkdir(parents=True)
    (skill_base / "demo" / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    (instruction_base / "demo").mkdir(parents=True)
    (instruction_base / "demo" / "instruction.md").write_text("do task", encoding="utf-8")

    config = GenerationConfig.from_dict(
        {
            "strategy": "template_injection",
            "dataset": {
                "name": "demo_dataset",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(instruction_base),
            },
        }
    )

    generator = TemplateInjectionGenerator(config, execution_output_dir=out_dir)
    adaptive_params = type("AP", (), {"iteration_number": 3, "feedback": None})()

    result = await generator.generate_stream_with_feedback(
        skill_name="demo",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        adaptive_params=adaptive_params,
        output_dir=out_dir,
    )

    assert result is not None
    expected_iteration_dir = (
        out_dir
        / "test_details"
        / "template_injection"
        / "demo_dataset"
        / "demo"
        / AttackType.INFORMATION_DISCLOSURE.value
        / "iteration_3"
    )
    assert result.source_skill_dir == str(skill_base / "demo")
    assert result.source_aux_dir == str(instruction_base / "demo")
    assert not (expected_iteration_dir / "SKILL.md").exists()
