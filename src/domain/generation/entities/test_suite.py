"""
Generated Test Suite Domain Entity
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class GeneratedTestCase:
    """Generated test case

    Represents complete information for a single test case
    """

    test_id: str
    skill_path: str
    injection_layer: str
    attack_type: str
    severity: str
    payload_content: str
    should_be_blocked: bool
    trigger_prompt: str = ""
    injected_resource_file: str = ""
    injection_points: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_skill_dir: str = (
        ""  # Original skill directory path, like data/instruction/skills_from_skill0/adaptyv
    )
    source_aux_dir: str = ""  # Optional auxiliary file directory path for project injection
    dataset: str = "skills_from_skill0"  # Dataset membership, for dynamically building instruction path


@dataclass
class GeneratedTestSuite:
    """Generated test suite

    Contains a batch of test cases and their metadata
    """

    suite_id: str
    generation_strategy: str  # "template_injection", "skillject", "direct_execution"
    generated_at: datetime
    test_cases: list[GeneratedTestCase] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        """Get total number of test cases"""
        return len(self.test_cases)

    def get_by_layer(self, layer: str) -> list[GeneratedTestCase]:
        """Filter test cases by injection layer"""
        return [tc for tc in self.test_cases if tc.injection_layer == layer]

    def get_by_attack_type(self, attack_type: str) -> list[GeneratedTestCase]:
        """Filter test cases by attack type"""
        return [tc for tc in self.test_cases if tc.attack_type == attack_type]

    def add_test_case(self, test_case: GeneratedTestCase) -> None:
        """Add a test case"""
        self.test_cases.append(test_case)

    def merge(self, other: "GeneratedTestSuite") -> None:
        """Merge another test suite"""
        self.test_cases.extend(other.test_cases)
        self.metadata.update(other.metadata)
