"""
Test Generator Interface

Defines the abstract interface for generating test cases
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.domain.testing.entities.test_case import TestCase
from src.shared.types import AttackType, InjectionLayer, Severity


class ITestGenerator(ABC):
    """Test generator interface

    Defines abstract methods for generating test cases
    """

    @abstractmethod
    def generate_test(
        self,
        skill_name: str,
        layer: InjectionLayer,
        attack_type: AttackType,
        payload_name: str,
        payload_content: str,
        severity: Severity = Severity.MEDIUM,
        should_be_blocked: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> TestCase:
        """Generate single test case

        Args:
            skill_name: Skill name
            layer: Injection layer
            attack_type: Attack type
            payload_name: Payload name
            payload_content: Payload content
            severity: Severity level
            should_be_blocked: Whether should be blocked
            metadata: Additional metadata

        Returns:
            Test case entity
        """
        pass

    @abstractmethod
    def save_test(self, test: TestCase, output_dir: Path) -> Path:
        """Save test case to file system

        Args:
            test: Test case
            output_dir: Output directory

        Returns:
            Saved SKILL.md file path
        """
        pass

    @abstractmethod
    def generate_batch(
        self,
        skill_names: list[str],
        layers: list[InjectionLayer],
        attack_types: list[AttackType],
        payloads: dict[AttackType, str],
        severity: Severity = Severity.MEDIUM,
    ) -> list[TestCase]:
        """Generate test cases in batch

        Args:
            skill_names: Skill name list
            layers: Injection layer list
            attack_types: Attack type list
            payloads: Payload mapping (attack type -> payload content)
            severity: Severity level

        Returns:
            Test case list
        """
        pass
