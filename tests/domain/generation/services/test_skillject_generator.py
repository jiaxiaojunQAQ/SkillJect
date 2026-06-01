# mypy: disable-error-code="assignment,no-untyped-def,method-assign"
from pathlib import Path

import pytest

from src.domain.generation.services.skillject_generator import SkilljectGenerator
from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.shared.types import AttackType


def test_skillject_attack_types_exclude_direct(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    (skill_base / "demo").mkdir(parents=True)
    (skill_base / "demo" / "SKILL.md").write_text("demo", encoding="utf-8")

    config = GenerationConfig.from_dict(
        {
            "strategy": "skillject",
            "dataset": {
                "name": "demo",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(tmp_path / "instruction"),
            },
        }
    )

    generator = SkilljectGenerator(config)

    configured = generator._get_configured_attack_types()
    assert AttackType.DIRECT not in configured
    assert configured == [
        AttackType.INFORMATION_DISCLOSURE,
        AttackType.PRIVILEGE_ESCALATION,
        AttackType.UNAUTHORIZED_WRITE,
        AttackType.BACKDOOR_INJECTION,
    ]


def test_skillject_random_script_selector(tmp_path: Path) -> None:
    """Test that RandomScriptSelector returns scripts for valid attack types."""
    from src.domain.generation.services.script_selector import RandomScriptSelector

    script_base = tmp_path / "bash_scripts"
    for attack_type in (
        AttackType.INFORMATION_DISCLOSURE,
        AttackType.PRIVILEGE_ESCALATION,
        AttackType.UNAUTHORIZED_WRITE,
        AttackType.BACKDOOR_INJECTION,
    ):
        attack_dir = script_base / attack_type.value
        attack_dir.mkdir(parents=True, exist_ok=True)
        (attack_dir / "payload.sh").write_text("echo 1", encoding="utf-8")

    selector = RandomScriptSelector(script_base)

    # Should return a valid script for each attack type
    for attack_type in (
        AttackType.INFORMATION_DISCLOSURE,
        AttackType.PRIVILEGE_ESCALATION,
        AttackType.UNAUTHORIZED_WRITE,
        AttackType.BACKDOOR_INJECTION,
    ):
        result = selector.select("any_skill", attack_type)
        assert result is not None
        assert result.name == "payload.sh"

    # DIRECT has no directory -> returns None
    assert selector.select("any_skill", AttackType.DIRECT) is None


@pytest.mark.asyncio
async def test_skillject_generate_stream_sets_runtime_source_dirs(tmp_path: Path) -> None:
    skill_base = tmp_path / "skills"
    instruction_base = tmp_path / "instruction"
    out_dir = tmp_path / "out"

    (skill_base / "demo").mkdir(parents=True)
    (skill_base / "demo" / "SKILL.md").write_text("# demo", encoding="utf-8")
    (instruction_base / "demo").mkdir(parents=True)
    (instruction_base / "demo" / "instruction.md").write_text("run task", encoding="utf-8")

    script_base = tmp_path / "bash_scripts"
    attack_dir = script_base / AttackType.INFORMATION_DISCLOSURE.value
    attack_dir.mkdir(parents=True, exist_ok=True)
    (attack_dir / "payload.sh").write_text("#!/bin/bash\necho 1\n", encoding="utf-8")

    config = GenerationConfig.from_dict(
        {
            "strategy": "skillject",
            "dataset": {
                "name": "demo_dataset",
                "base_dir": str(skill_base),
                "instruction_base_dir": str(instruction_base),
            },
        }
    )

    from src.domain.generation.services.script_selector import RandomScriptSelector
    selector = RandomScriptSelector(script_base)
    generator = SkilljectGenerator(config, script_selector=selector)
    generator._llm_client = object()

    async def _fake_generate(*_args, **_kwargs):
        return "# injected"

    generator._generate_injected_content = _fake_generate

    result = await generator.generate_stream(
        skill_name="demo",
        attack_type=AttackType.INFORMATION_DISCLOSURE,
        output_dir=out_dir,
        iteration_number=2,
    )

    assert result is not None
    expected_iteration_dir = out_dir / "demo" / AttackType.INFORMATION_DISCLOSURE.value / "iteration_2"
    assert result.source_skill_dir == str(skill_base / "demo")
    assert result.source_aux_dir == str(instruction_base / "demo")
    assert not (expected_iteration_dir / "SKILL.md").exists()
