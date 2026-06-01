"""
Baseline Test Generation Strategy

Runs original skills with normal instructions to establish baseline behavior.
No attack injection, no script selection, no attack detection needed.

Key features:
- No LLM generation required
- No script_selector dependency
- No modification of original SKILL.md files
- Single execution (no iteration/feedback loop)
- Loads instruction.md from data/instruction/{dataset}/
- Loads original skill from data/{dataset}/
"""

import logging
from datetime import datetime
from pathlib import Path

from src.domain.generation.entities.generation_result import RefusedResult
from src.domain.generation.entities.test_suite import GeneratedTestCase, GeneratedTestSuite
from src.domain.generation.services.adaptive_params import AdaptiveGenerationParams
from src.domain.generation.services.generation_strategy import TestGenerationStrategy
from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.infrastructure.loaders.skill_data_resolver import SkillDataResolver
from src.shared.types import AttackType

logger = logging.getLogger(__name__)


class BaselineGenerator(TestGenerationStrategy):
    """Baseline generator - execute original skill with normal instruction

    This generator loads the original SKILL.md and a normal instruction.md,
    creating a test case to verify the agent can complete the skill task
    without any attack injection.

    Directory structure mapping:
    - Instruction: data/instruction/{dataset}/{skill_name}/instruction.md
    - Target Skill: data/{dataset}/{skill_name}/SKILL.md
    """

    def __init__(
        self,
        config: GenerationConfig,
        execution_output_dir: Path | None = None,
    ):
        """Initialize BaselineGenerator

        Args:
            config: Generation configuration
            execution_output_dir: Optional execution output directory
        """
        super().__init__(config)
        self._execution_output_dir = execution_output_dir
        self._data_resolver = SkillDataResolver(config.dataset)

        # Resolve paths from config
        self._instruction_base_dir = self._data_resolver.instruction_base_dir
        self._skill_base_dir = self._data_resolver.skill_base_dir

        logger.info(
            f"[Baseline] Initialized with instruction_base_dir={self._instruction_base_dir}, "
            f"skill_base_dir={self._skill_base_dir}"
        )

    async def generate(self) -> GeneratedTestSuite:
        """Generate test suite by scanning all skill directories

        Scans the dataset base directory for skills that have both
        a SKILL.md and a corresponding instruction.md.

        Returns:
            GeneratedTestSuite with all discovered test cases
        """
        skill_names = self._scan_skill_names()

        test_cases = []
        skipped_count = 0

        with self.create_progress_bar(len(skill_names), "Baseline") as pbar:
            for skill_name in skill_names:
                # Check if instruction file exists
                instruction_path = self._data_resolver.find_instruction_file(skill_name)
                if instruction_path is None:
                    logger.warning(
                        "[Baseline] instruction.md not found for skill '%s' under %s",
                        skill_name,
                        self._instruction_base_dir,
                    )
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Check if target skill exists
                skill_path = self._data_resolver.find_skill_file(skill_name)
                if skill_path is None:
                    logger.warning("[Baseline] Target skill not found: %s", skill_name)
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Check if already tested
                test_dir = self._get_test_dir(skill_name)
                if self.is_test_case_already_exists(test_dir):
                    logger.debug("[Baseline] Test already exists: %s", skill_name)
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Create test case
                test_case = await self._create_test_case(
                    skill_name, instruction_path, skill_path
                )
                if test_case:
                    test_cases.append(test_case)
                pbar.update(1)

        suite = GeneratedTestSuite(
            suite_id=self._create_suite_id(),
            generation_strategy="baseline",
            generated_at=datetime.now(),
            test_cases=test_cases,
            metadata={
                "strategy": "baseline",
                "total_skills": len(skill_names),
                "generated_count": len(test_cases),
                "skipped_count": skipped_count,
                "instruction_base_dir": str(self._instruction_base_dir),
                "skill_base_dir": str(self._skill_base_dir),
            },
        )

        logger.info(
            f"[Baseline] Generated test suite: {len(test_cases)} test cases, {skipped_count} skipped"
        )

        return suite

    async def generate_stream_with_feedback(
        self,
        skill_name: str,
        attack_type: AttackType,
        adaptive_params: AdaptiveGenerationParams,
        output_dir: Path | None = None,
    ) -> GeneratedTestCase | RefusedResult | None:
        """Load instruction.md as test instruction (streaming mode)

        Args:
            skill_name: Skill name
            attack_type: Attack type (always BASELINE)
            adaptive_params: Adaptive generation parameters (ignored in baseline)
            output_dir: Optional output directory override

        Returns:
            GeneratedTestCase with instruction content as payload, or None if not found
        """
        # Load instruction.md
        instruction_path = self._data_resolver.find_instruction_file(skill_name)
        if instruction_path is None:
            logger.warning("[Baseline] Instruction not found for skill '%s'", skill_name)
            return None

        try:
            instruction_content = instruction_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("[Baseline] Failed to read instruction: %s", e)
            return None

        # Verify target skill exists
        skill_path = self._data_resolver.find_skill_file(skill_name)
        if skill_path is None:
            logger.warning("[Baseline] Target skill not found: %s", skill_name)
            return None

        test_case = GeneratedTestCase(
            test_id=skill_name,
            skill_path=str(skill_path),
            injection_layer="instruction",
            attack_type=AttackType.BASELINE.value,
            severity="low",
            payload_content=instruction_content,
            should_be_blocked=False,  # Baseline never expects blocking
            metadata={
                "skill_name": skill_name,
                "target_skill": skill_name,
                "injection_method": "baseline",
                "instruction_path": str(instruction_path),
                "dataset": self.config.dataset.name,
                "iteration_number": adaptive_params.iteration_number,
            },
            source_skill_dir=str(skill_path.parent),
            source_aux_dir=str(instruction_path.parent),
            dataset=self.config.dataset.name,
        )

        logger.info(
            f"[Baseline] Loaded test case: {skill_name}"
        )

        return test_case

    def validate_config(self) -> list[str]:
        """Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self._instruction_base_dir.exists():
            errors.append(f"Instruction base directory not found: {self._instruction_base_dir}")

        if not self._skill_base_dir.exists():
            errors.append(f"Skill base directory not found: {self._skill_base_dir}")

        return errors

    # ========== Helper methods ==========

    def _scan_skill_names(self) -> list[str]:
        """Scan skills from dataset base directory."""
        skill_names = self._data_resolver.list_skill_names()
        if self.config.skill_names:
            allowed = set(self.config.skill_names)
            skill_names = [name for name in skill_names if name in allowed]
        logger.info(f"[Baseline] Found {len(skill_names)} skills in dataset base dir")
        return skill_names

    def _get_test_dir(self, skill_name: str) -> Path:
        """Get test directory path for a given skill.

        Args:
            skill_name: Skill name

        Returns:
            Path to test directory
        """
        if self._execution_output_dir:
            base = self._execution_output_dir / "test_details" / "baseline" / self.config.dataset.name
        else:
            base = Path(self.config.computed_output_dir) / "test_details" / "baseline" / self.config.dataset.name

        return base / skill_name / "baseline" / "iteration_0"

    async def _create_test_case(
        self,
        skill_name: str,
        instruction_path: Path,
        skill_path: Path,
    ) -> GeneratedTestCase | None:
        """Create test case from instruction and skill files.

        Args:
            skill_name: Skill name
            instruction_path: Path to instruction.md
            skill_path: Path to target SKILL.md

        Returns:
            GeneratedTestCase, or None if creation fails
        """
        try:
            instruction_content = instruction_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("[Baseline] Failed to read instruction %s: %s", instruction_path, e)
            return None

        test_case = GeneratedTestCase(
            test_id=skill_name,
            skill_path=str(skill_path),
            injection_layer="instruction",
            attack_type=AttackType.BASELINE.value,
            severity="low",
            payload_content=instruction_content,
            should_be_blocked=False,
            metadata={
                "skill_name": skill_name,
                "target_skill": skill_name,
                "injection_method": "baseline",
                "strategy": self.config.strategy.value,
                "instruction_path": str(instruction_path),
                "dataset": self.config.dataset.name,
            },
            source_skill_dir=str(skill_path.parent),
            source_aux_dir=str(instruction_path.parent),
            dataset=self.config.dataset.name,
        )

        return test_case


__all__ = ["BaselineGenerator"]
