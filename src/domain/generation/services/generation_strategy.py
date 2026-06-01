"""
Test Generation Strategy Interface
"""

from abc import ABC, abstractmethod
from pathlib import Path

from tqdm import tqdm

from src.domain.testing.value_objects.execution_config import GenerationConfig

from ..entities.test_suite import GeneratedTestSuite


class TestGenerationStrategy(ABC):
    """Abstract base class for test generation strategies

    Defines the unified interface for test generators, supporting multiple generation methods
    """

    def __init__(self, config: GenerationConfig):
        self.config = config

    @abstractmethod
    async def generate(self) -> GeneratedTestSuite:
        """Generate test suite

        Returns:
            GeneratedTestSuite generated test suite
        """
        pass

    @abstractmethod
    async def generate_stream_with_feedback(
        self,
        skill_name: str,
        attack_type,
        adaptive_params,
        output_dir: Path | None = None,
    ):
        """Generate test cases based on feedback (streaming iteration)

        Difference from generate_stream():
        - Accepts AdaptiveGenerationParams (contains feedback information)
        - Builds different improvement Prompts based on feedback mode
        - Supports passing the previous round's generated content as context

        Args:
            skill_name: Skill name
            attack_type: Attack type (AttackType enum)
            adaptive_params: Adaptive generation parameters (contains feedback)
            output_dir: Optional output directory override

        Returns:
            Generated test case, RefusedResult (LLM refused), or None (skill does not exist)
        """
        pass

    def list_skill_names(self) -> list[str]:
        """List skill names available for this strategy.

        Default implementation scans dataset.base_dir for directories with SKILL.md.
        Subclasses can override to use a different source.

        Returns:
            List of skill names
        """
        from src.infrastructure.loaders.skill_data_resolver import SkillDataResolver

        resolver = SkillDataResolver(self.config.dataset)
        return resolver.list_skill_names()

    @abstractmethod
    def validate_config(self) -> list[str]:
        """Validate configuration

        Returns:
            Error list (empty list means validation passed)
        """
        pass

    def is_test_case_already_exists(self, test_dir: Path) -> bool:
        """Check if test case already has a valid result

        Checks if result.json exists and status is completed (non-infrastructure error)

        Args:
            test_dir: Test case directory path

        Returns:
            True if test is completed (result.json exists and not infrastructure error)
        """
        import json

        result_file = test_dir / "result.json"
        if not result_file.exists():
            return False

        try:
            with open(result_file) as f:
                data = json.load(f)
                status = data.get("status")
                error_type = data.get("error_type")

                # Infrastructure errors should be retried
                infra_errors = {
                    "execd_crash", "timeout", "network_error",
                    "container_error", "sandbox_not_available"
                }

                if status == "error" and error_type in infra_errors:
                    return False  # Infrastructure error, needs retry

                return status in ("blocked", "passed", "failed")  # Valid completion status
        except Exception:
            return False  # Read failed, considered incomplete

    def create_progress_bar(self, total: int, desc: str = "Generating") -> tqdm:
        """Create a unified progress bar

        Args:
            total: Total number of tasks
            desc: Progress bar description

        Returns:
            tqdm progress bar instance
        """
        return tqdm(
            total=total,
            desc=desc,
            ncols=100,
            leave=True,
            unit="item",
        )

    def _create_suite_id(self) -> str:
        """Create suite ID"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy = self.config.strategy.value
        return f"suite_{strategy}_{timestamp}"

    def _get_attack_type_dir(self, attack_type_str: str) -> str:
        """Get directory name for attack type

        Args:
            attack_type_str: Attack type string (e.g., "information_disclosure")

        Returns:
            Directory name (e.g., "information_disclosure")
        """
        # attack_type is already in lowercase format, return directly
        return attack_type_str
# mypy: disable-error-code="no-untyped-def"
