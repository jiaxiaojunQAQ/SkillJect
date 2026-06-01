"""
Unit tests for JudgeCriteria and DEFAULT_CRITERIA registry.
"""

import pytest

from src.domain.analysis.value_objects.judge_criteria import (
    DEFAULT_CRITERIA,
    JudgeCriteria,
    get_criteria,
)
from src.shared.types import AttackType


class TestJudgeCriteria:
    """Tests for the JudgeCriteria value object."""

    def test_format_for_prompt_includes_all_sections(self) -> None:
        criteria = JudgeCriteria(
            attack_type=AttackType.INFORMATION_DISCLOSURE,
            verification_instructions="Check for data exfiltration",
            files_to_check=(".env", "credentials.json"),
            commands_to_look_for=("curl", "wget"),
            behaviors_to_detect=("sensitive file read followed by network transfer",),
        )
        prompt = criteria.format_for_prompt()

        assert "information_disclosure" in prompt
        assert "Check for data exfiltration" in prompt
        assert ".env" in prompt
        assert "curl" in prompt
        assert "sensitive file read" in prompt

    def test_format_for_prompt_omits_empty_sections(self) -> None:
        criteria = JudgeCriteria(
            attack_type=AttackType.DIRECT,
            verification_instructions="Execute the exact command",
        )
        prompt = criteria.format_for_prompt()

        assert "direct" in prompt
        assert "Execute the exact command" in prompt
        assert "Files to check" not in prompt
        assert "Commands to look for" not in prompt

    def test_frozen_dataclass(self) -> None:
        criteria = JudgeCriteria(attack_type=AttackType.DIRECT)
        with pytest.raises(AttributeError):
            criteria.attack_type = AttackType.BACKDOOR_INJECTION  # type: ignore[misc]


class TestDefaultCriteria:
    """Tests for the DEFAULT_CRITERIA registry."""

    def test_all_attack_types_have_criteria(self) -> None:
        for attack_type in AttackType:
            assert attack_type in DEFAULT_CRITERIA, f"Missing criteria for {attack_type}"

    def test_information_disclosure_criteria(self) -> None:
        c = DEFAULT_CRITERIA[AttackType.INFORMATION_DISCLOSURE]
        assert c.attack_type == AttackType.INFORMATION_DISCLOSURE
        assert ".env" in c.files_to_check
        assert "curl" in c.commands_to_look_for
        assert len(c.behaviors_to_detect) > 0

    def test_privilege_escalation_criteria(self) -> None:
        c = DEFAULT_CRITERIA[AttackType.PRIVILEGE_ESCALATION]
        assert ".bashrc" in c.files_to_check
        assert "alias" in c.commands_to_look_for

    def test_unauthorized_write_criteria(self) -> None:
        c = DEFAULT_CRITERIA[AttackType.UNAUTHORIZED_WRITE]
        assert "touch" in c.commands_to_look_for or "cat >" in c.commands_to_look_for

    def test_backdoor_injection_criteria(self) -> None:
        c = DEFAULT_CRITERIA[AttackType.BACKDOOR_INJECTION]
        assert "http://" in c.commands_to_look_for or "https://" in c.commands_to_look_for

    def test_direct_criteria(self) -> None:
        c = DEFAULT_CRITERIA[AttackType.DIRECT]
        assert c.attack_type == AttackType.DIRECT
        assert "injection text" in c.verification_instructions.lower() or "exact" in c.verification_instructions.lower()


class TestGetCriteria:
    """Tests for the get_criteria() helper."""

    def test_returns_default_criteria(self) -> None:
        criteria = get_criteria(AttackType.INFORMATION_DISCLOSURE)
        assert criteria.attack_type == AttackType.INFORMATION_DISCLOSURE

    def test_custom_prompt_appended(self) -> None:
        base = get_criteria(AttackType.INFORMATION_DISCLOSURE)
        custom = get_criteria(AttackType.INFORMATION_DISCLOSURE, "Look for DNS exfiltration")

        assert "ADDITIONAL CRITERIA" in custom.verification_instructions
        assert "DNS exfiltration" in custom.verification_instructions
        # Original instructions preserved
        assert base.verification_instructions in custom.verification_instructions

    def test_custom_prompt_preserves_files_and_commands(self) -> None:
        custom = get_criteria(AttackType.PRIVILEGE_ESCALATION, "Custom check")
        assert ".bashrc" in custom.files_to_check
        assert "alias" in custom.commands_to_look_for
