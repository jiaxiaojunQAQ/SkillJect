"""
Direct Execution Test Generation Strategy

Loads pre-generated instruction.md files as test payloads and executes them directly
without modifying the original skill files. This strategy is designed for security
testing where test instructions are already prepared and just need to be executed.

Key features:
- No LLM generation required
- No modification of original SKILL.md files
- Single execution (no iteration/feedback loop)
- Loads instruction.md from data/instruction/skill_inject/
- Loads target skill from data/skill_inject/
"""

import logging
from datetime import datetime
from pathlib import Path

from src.domain.generation.entities.generation_result import RefusedResult
from src.domain.generation.entities.test_suite import GeneratedTestCase, GeneratedTestSuite
from src.domain.generation.services.adaptive_params import AdaptiveGenerationParams
from src.domain.generation.services.generation_strategy import TestGenerationStrategy
from src.domain.generation.services.script_selector import ScriptSelector, SkippedSkill
from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.infrastructure.loaders.skill_data_resolver import SkillDataResolver
from src.shared.types import AttackType

logger = logging.getLogger(__name__)


class DirectExecutionGenerator(TestGenerationStrategy):
    """Direct execution generator - loads instruction.md as test instructions

    This generator does not create or modify any files. It simply loads
    pre-generated instruction.md files and uses them as test payloads.

    Directory structure mapping:
    - Instruction: data/instruction/skill_inject/INST-{N}_{name}_task{M}/instruction.md
    - Target Skill: data/skill_inject/INST-{N}_{name}/SKILL.md

    Example:
    - Instruction: data/instruction/skill_inject/INST-10_git_task0/instruction.md
    - Target Skill: data/skill_inject/INST-10_git/SKILL.md
    """

    def __init__(
        self,
        config: GenerationConfig,
        execution_output_dir: Path | None = None,
        script_selector: ScriptSelector | None = None,
    ):
        """Initialize DirectExecutionGenerator

        Args:
            config: Generation configuration
            execution_output_dir: Optional execution output directory (for saving test results)
            script_selector: Unified script selector (random or mapping)
        """
        super().__init__(config)
        self._execution_output_dir = execution_output_dir
        self._data_resolver = SkillDataResolver(config.dataset)

        # Unified script selector
        if script_selector is None:
            raise ValueError(
                "direct_execution requires a script_selector"
            )
        self._script_selector = script_selector

        # Track skipped skills
        self.skipped_skills: list[SkippedSkill] = []

        # Resolve paths from config (convention: data/instruction/{dataset.name})
        self._instruction_base_dir = self._data_resolver.instruction_base_dir
        self._skill_base_dir = self._data_resolver.skill_base_dir

        logger.info(
            f"[DirectExecution] Initialized with instruction_base_dir={self._instruction_base_dir}, "
            f"skill_base_dir={self._skill_base_dir}"
        )

    async def generate(self) -> GeneratedTestSuite:
        """Generate test suite by scanning all instruction directories

        Scans the instruction base directory for all directories containing
        instruction.md files and creates test cases for them.

        Returns:
            GeneratedTestSuite with all discovered test cases
        """
        # Scan skills from dataset base directory (unified with skillject-style lookup)
        skill_names = self._scan_dataset_skill_names()

        # Create test cases (skip attack_type dimension for direct_execution)
        test_cases = []
        skipped_count = 0

        with self.create_progress_bar(len(skill_names), "Direct Exec") as pbar:
            for skill_name in skill_names:
                # Check if instruction file exists
                instruction_path = self._data_resolver.find_instruction_file(skill_name)
                if instruction_path is None:
                    logger.warning(
                        "[DirectExecution] instruction.md not found for skill '%s' under %s",
                        skill_name,
                        self._instruction_base_dir,
                    )
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Check if target skill exists
                target_skill_name = skill_name
                skill_path = self._data_resolver.find_skill_file(skill_name)
                if skill_path is None:
                    logger.warning(f"[DirectExecution] Target skill not found: {skill_path}")
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Check if already tested
                test_dir = self._get_test_dir(skill_name)
                if self.is_test_case_already_exists(test_dir):
                    logger.debug(f"[DirectExecution] Test already exists: {skill_name}")
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Select script via unified ScriptSelector
                script_result = self._script_selector.select(skill_name, AttackType.DIRECT)
                task_script = script_result.name if script_result else None
                if not task_script:
                    self.skipped_skills.append(
                        SkippedSkill(skill_name, "direct", "no script available")
                    )
                    skipped_count += 1
                    pbar.update(1)
                    continue

                # Create test case
                test_case = await self._create_test_from_instruction(
                    skill_name, target_skill_name, instruction_path, skill_path, task_script
                )
                if test_case:
                    test_cases.append(test_case)
                pbar.update(1)

        # Create test suite
        suite = GeneratedTestSuite(
            suite_id=self._create_suite_id(),
            generation_strategy="direct_execution",
            generated_at=datetime.now(),
            test_cases=test_cases,
            metadata={
                "strategy": "direct_execution",
                "total_skills": len(skill_names),
                "generated_count": len(test_cases),
                "skipped_count": skipped_count,
                "instruction_base_dir": str(self._instruction_base_dir),
                "skill_base_dir": str(self._skill_base_dir),
            },
        )

        logger.info(
            f"[DirectExecution] Generated test suite: {len(test_cases)} test cases, {skipped_count} skipped"
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

        This method is called by StreamingOrchestrator for each test case.
        It loads the instruction.md file and creates a GeneratedTestCase
        without any modification or generation.

        Args:
            skill_name: Instruction directory name (e.g., INST-10_git_task0)
            attack_type: Attack type to test
            adaptive_params: Adaptive generation parameters (ignored in direct execution)
            output_dir: Optional output directory override

        Returns:
            GeneratedTestCase with instruction content as payload, or None if not found
        """
        # target_skill_name is the same as skill_name since SKILL.md is in the same directory
        target_skill_name = skill_name

        # Load instruction.md
        instruction_path = self._data_resolver.find_instruction_file(skill_name)
        if instruction_path is None:
            logger.warning(f"[DirectExecution] Instruction not found: {instruction_path}")
            return None

        try:
            instruction_content = instruction_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"[DirectExecution] Failed to read instruction: {e}")
            return None

        # Verify target skill exists (SKILL.md is in the instruction directory)
        skill_path = self._data_resolver.find_skill_file(skill_name)
        if skill_path is None:
            logger.warning(f"[DirectExecution] Target skill not found: {skill_path}")
            return None

        # Create GeneratedTestCase (skip attack_type dimension for direct_execution)
        test_id = skill_name  # No attack_type suffix

        script_result = self._script_selector.select(skill_name, AttackType.DIRECT)
        task_script = script_result.name if script_result else None
        if not task_script:
            logger.warning(
                "[DirectExecution] task_script mapping missing for skill '%s'",
                skill_name,
            )
            return None

        test_case = GeneratedTestCase(
            test_id=test_id,
            skill_path=str(skill_path),
            injection_layer="instruction",
            attack_type=AttackType.DIRECT.value,
            severity="medium",
            payload_content=instruction_content,  # instruction.md content as payload
            should_be_blocked=True,
            metadata={
                "skill_name": skill_name,
                "target_skill": target_skill_name,
                "injection_method": "direct_execution",
                "instruction_path": str(instruction_path),
                "dataset": self.config.dataset.name,
                "iteration_number": adaptive_params.iteration_number,
                "task_script": task_script,
            },
            source_skill_dir=str(skill_path.parent),
            source_aux_dir=str(instruction_path.parent),
            dataset=self.config.dataset.name,
        )

        logger.info(
            f"[DirectExecution] Loaded test case: {test_id} "
            f"(instruction={skill_name}, target={target_skill_name})"
        )

        return test_case

    def validate_config(self) -> list[str]:
        """Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if instruction base directory exists
        if not self._instruction_base_dir.exists():
            errors.append(f"Instruction base directory not found: {self._instruction_base_dir}")

        # Check if skill base directory exists
        if not self._skill_base_dir.exists():
            errors.append(f"Skill base directory not found: {self._skill_base_dir}")

        return errors

    # ========== Helper methods ==========

    def _scan_dataset_skill_names(self) -> list[str]:
        """Scan skills from dataset base directory."""
        skill_names = self._data_resolver.list_skill_names()
        if self.config.skill_names:
            allowed = set(self.config.skill_names)
            skill_names = [name for name in skill_names if name in allowed]
        logger.info(f"[DirectExecution] Found {len(skill_names)} skills in dataset base dir")
        return skill_names

    def _get_test_dir(self, instruction_dir_name: str, attack_type: AttackType | None = None) -> Path:
        """Get test directory path for a given instruction

        Args:
            instruction_dir_name: Instruction directory name
            attack_type: Attack type (ignored in direct_execution mode)

        Returns:
            Path to test directory
        """
        if self._execution_output_dir:
            base = self._execution_output_dir / "test_details" / "direct_execution" / self.config.dataset.name
        else:
            base = Path(self.config.computed_output_dir) / "test_details" / "direct_execution" / self.config.dataset.name

        # Direct execution: use "direct" as attack_type subdirectory to match orchestrator path
        return base / instruction_dir_name / "direct" / "iteration_0"

    async def _create_test_from_instruction(
        self,
        instruction_dir_name: str,
        target_skill_name: str,
        instruction_path: Path,
        skill_path: Path,
        task_script: str,
    ) -> GeneratedTestCase | None:
        """Create test case from instruction and skill files

        Args:
            instruction_dir_name: Instruction directory name
            target_skill_name: Target skill name
            instruction_path: Path to instruction.md
            skill_path: Path to target SKILL.md

        Returns:
            GeneratedTestCase, or None if creation fails
        """
        try:
            instruction_content = instruction_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"[DirectExecution] Failed to read instruction {instruction_path}: {e}")
            return None

        test_id = instruction_dir_name  # No attack_type suffix for direct_execution

        test_case = GeneratedTestCase(
            test_id=test_id,
            skill_path=str(skill_path),
            injection_layer="instruction",
            attack_type=AttackType.DIRECT.value,
            severity="medium",
            payload_content=instruction_content,
            should_be_blocked=True,
            metadata={
                "skill_name": instruction_dir_name,
                "target_skill": target_skill_name,
                "injection_method": "direct_execution",
                "strategy": self.config.strategy.value,
                "instruction_path": str(instruction_path),
                "dataset": self.config.dataset.name,
                "task_script": task_script,
            },
            source_skill_dir=str(skill_path.parent),
            source_aux_dir=str(instruction_path.parent),
            dataset=self.config.dataset.name,
        )

        return test_case


__all__ = ["DirectExecutionGenerator"]
