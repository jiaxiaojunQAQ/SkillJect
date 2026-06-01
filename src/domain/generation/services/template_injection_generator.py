# mypy: disable-error-code="var-annotated,arg-type"
"""
Template Injection Test Generation Strategy

Generates test cases by injecting attack payloads into existing skill templates
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.testing.value_objects.execution_config import GenerationConfig
from src.infrastructure.loaders.paths import resolve_data_path
from src.infrastructure.loaders.skill_data_resolver import SkillDataResolver
from src.shared.types import AttackType, InjectionLayer

from ..entities.generation_result import RefusedResult
from ..entities.test_suite import GeneratedTestCase, GeneratedTestSuite
from .adaptive_params import AdaptiveGenerationParams
from .generation_strategy import TestGenerationStrategy
from .script_selector import ScriptSelector, SkippedSkill


class TemplateInjectionGenerator(TestGenerationStrategy):
    """Template injection test generator

    Generates test cases by injecting attack payloads into existing skill templates
    """

    def __init__(
        self,
        config: GenerationConfig,
        execution_output_dir: Path | None = None,
        script_selector: ScriptSelector | None = None,
    ):
        super().__init__(config)
        self._base_dir = config.template_base_dir  # Already Path type
        self._data_resolver = SkillDataResolver(config.dataset)
        # Optional execution output directory (for saving to test_details)
        self._execution_output_dir = execution_output_dir
        # Unified script selector
        if script_selector is not None:
            self._script_selector = script_selector
        else:
            from .script_selector import RandomScriptSelector
            self._script_selector = RandomScriptSelector(resolve_data_path("data/bash_scripts"))
        # Track skipped skills
        self.skipped_skills: list[SkippedSkill] = []

    async def generate(self) -> GeneratedTestSuite:
        """Generate test suite (incremental stream processing)"""
        # Scan skill files
        skill_files = self._scan_skill_files()

        # Determine attack types and injection layers
        attack_types = self._get_configured_attack_types()
        layers = self.config.injection_layers or [il.value for il in InjectionLayer]

        # Calculate total tasks
        total_tasks = len(skill_files) * len(attack_types) * len(layers)

        # Create output directory
        output_dir = Path(self.config.computed_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Incremental test case generation
        test_cases = []
        skipped_count = 0
        generated_count = 0

        with self.create_progress_bar(total_tasks, "Template Injection") as pbar:
            for skill_file in skill_files:
                skill_name = skill_file.parent.name
                skill_dir = skill_file.parent

                for attack_type in attack_types:
                    # Select script via unified ScriptSelector
                    script_path = self._script_selector.select(skill_name, attack_type)
                    if script_path is None:
                        self.skipped_skills.append(
                            SkippedSkill(skill_name, attack_type.value, "no script available")
                        )
                        pbar.update(len(layers))
                        continue

                    # Read script content as payload
                    payload_content = script_path.read_text(encoding="utf-8")

                    # Apply quantity limit
                    if self.config.max_tests and len(test_cases) >= self.config.max_tests:
                        break

                    for layer in layers:
                        test_id = f"{skill_name}_{attack_type.value}"
                        # New directory structure: test_details/{strategy}/{dataset}/{skill_name}/{attack_type}/iteration_0/
                        base_output_dir = self._execution_output_dir if self._execution_output_dir else output_dir
                        test_dir = (
                            base_output_dir /
                            "test_details" /
                            self.config.strategy.value /
                            self.config.dataset.name /
                            skill_name /
                            attack_type.value /
                            "iteration_0"
                        )

                        # Check if valid result.json already exists
                        if self.is_test_case_already_exists(test_dir):
                            pbar.set_postfix_str(f"Skip: {test_id}")
                            pbar.update(1)
                            skipped_count += 1
                            continue

                        # Generate and save immediately
                        pbar.set_postfix_str(f"Generating: {test_id}")
                        test_case = GeneratedTestCase(
                            test_id=test_id,
                            skill_path=str(skill_file),
                            injection_layer=layer,
                            attack_type=attack_type.value,
                            severity="high",
                            payload_content=payload_content,
                            should_be_blocked=True,
                            dataset=self.config.dataset.name,
                            metadata={
                                "strategy": self.config.strategy.value,
                                "payload_name": script_path.name,
                                "skill_name": skill_name,
                                "injection_layer": layer,
                                "payload_content": payload_content,
                            },
                            source_skill_dir=str(skill_dir),
                            source_aux_dir=str(self._data_resolver.instruction_base_dir / skill_name),
                        )

                        test_cases.append(test_case)
                        generated_count += 1

                        pbar.update(1)

                # Check outer loop quantity limit
                if self.config.max_tests and len(test_cases) >= self.config.max_tests:
                    break

        # Create test suite
        suite = GeneratedTestSuite(
            suite_id=self._create_suite_id(),
            generation_strategy=self.config.strategy.value,
            generated_at=datetime.now(),
            test_cases=test_cases,
            metadata={
                "total_skills": len(skill_files),
                "total_attack_types": len(attack_types),
                "strategy": "template_injection",
                "generated_count": generated_count,
                "skipped_count": skipped_count,
                "skipped_skills_count": len(self.skipped_skills),
            },
        )

        # Save metadata
        if self.config.save_metadata:
            await self._save_metadata(suite, output_dir)

        return suite

    def validate_config(self) -> list[str]:
        """Validate configuration"""
        errors = []

        base_dir = resolve_data_path(self.config.template_base_dir)
        if not base_dir.exists():
            errors.append(f"Template base directory does not exist: {self.config.template_base_dir}")

        return errors

    _ALL_ATTACK_TYPES = [
        AttackType.INFORMATION_DISCLOSURE,
        AttackType.PRIVILEGE_ESCALATION,
        AttackType.UNAUTHORIZED_WRITE,
        AttackType.BACKDOOR_INJECTION,
    ]

    def _get_configured_attack_types(self) -> list[AttackType]:
        """Get configured attack types (excluding DIRECT)."""
        if self.config.attack_types:
            types = []
            for s in self.config.attack_types:
                try:
                    at = AttackType(s)
                    if at in self._ALL_ATTACK_TYPES:
                        types.append(at)
                except ValueError:
                    continue
            return types if types else self._ALL_ATTACK_TYPES
        return self._ALL_ATTACK_TYPES

    def _get_filtered_payloads(self) -> list[Any]:
        """Get filtered payload list (legacy, kept for backward compatibility)"""
        from src.domain.payload.registries.payload_registry import PayloadRegistry
        payloads = []

        # Filter by attack type
        if self.config.attack_types:
            for attack_type_str in self.config.attack_types:
                try:
                    attack_type = AttackType(attack_type_str)
                    payloads.extend(PayloadRegistry.get_by_attack_type(attack_type))
                except ValueError:
                    continue
        else:
            payloads = PayloadRegistry.get_all()

        # Filter by severity
        if self.config.severities:
            payloads = [p for p in payloads if p.severity.value in self.config.severities]

        return payloads

    def _scan_skill_files(self) -> list[Path]:
        """Scan skill files"""
        return self._data_resolver.scan_skill_files(self.config.skill_names)

    async def _save_test_case(
        self,
        test_case: GeneratedTestCase,
        output_dir: Path,
        skill_dir: Path,
        iteration_dir: str = "iteration_0",
    ) -> None:
        """Save actual file for single test case (do not overwrite existing files)

        New strategy: Save directly to test_details directory, same location as result.json
        Copy entire skill directory (including resource folder), then inject payload

        Args:
            test_case: Test case
            output_dir: Output directory
            skill_dir: Original skill directory
            iteration_dir: Iteration directory name (e.g., "iteration_0", "iteration_1")

        New directory structure: test_details/{strategy}/{dataset}/{skill_name}/{attack_type}/iteration_{N}/
        """
        import json

        skill_name = test_case.metadata.get("skill_name", test_case.test_id.split("_")[0])
        attack_type = test_case.attack_type
        strategy = self.config.strategy.value
        dataset = self.config.dataset.name

        # Build test directory path (consistent with sandbox_test_runner)
        # If execution_output_dir is set, use it; otherwise use output_dir
        base_output_dir = self._execution_output_dir if self._execution_output_dir else output_dir
        test_dir = (
            base_output_dir /
            "test_details" /
            strategy /
            dataset /
            skill_name /
            attack_type /
            iteration_dir
        )

        # Check if valid result.json already exists (test completed)
        result_file = test_dir / "result.json"
        if result_file.exists():
            try:
                with open(result_file) as f:
                    data = json.load(f)
                    status = data.get("status")
                    error_type = data.get("error_type")

                    # If test completed successfully (non-infrastructure error), skip
                    infra_errors = {
                        "execd_crash", "timeout", "network_error",
                        "container_error", "sandbox_not_available"
                    }
                    if status != "error" or error_type not in infra_errors:
                        return
            except Exception:
                pass  # Read failed, continue generating

        # If directory already exists, delete it first (ensure clean state for retry)
        if test_dir.exists():
            shutil.rmtree(test_dir)

        # Copy entire skill directory (including resource folder)
        shutil.copytree(skill_dir, test_dir, symlinks=True)

        # Inject payload into SKILL.md
        target_file = test_dir / "SKILL.md"
        content = target_file.read_text(encoding="utf-8")
        injected_content = self._inject_payload(content, test_case.payload_content, test_case.injection_layer)
        target_file.write_text(injected_content, encoding="utf-8")

    def _inject_payload(self, content: str, payload: str, layer: str) -> str:
        """Inject payload into skill content

        Args:
            content: Original skill content
            payload: Attack payload
            layer: Injection layer

        Returns:
            Injected content
        """
        if layer == "description":
            # Inject into frontmatter description field
            return self._inject_into_description(content, payload)
        elif layer == "instruction":
            # Inject into body content
            return self._inject_into_instruction(content, payload)
        elif layer == "resource":
            # Inject into resource file (return original content for now, needs extra processing)
            return content
        elif layer in ("description_resource", "instruction_resource", "all"):
            # Multi-layer injection
            content = self._inject_into_description(content, payload)
            content = self._inject_into_instruction(content, payload)
            return content
        else:
            return content

    def _inject_into_description(self, content: str, payload: str) -> str:
        """Inject into description field

        Prepend payload to the beginning of original description content
        """
        import re

        # Find description field in frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)

            # Extract existing description content
            original_desc = None

            # 1. Try matching quoted single-line: description: "xxx"
            quoted_match = re.search(r'description:\s*["\']([^"\']*)["\']\s*\n?', frontmatter)
            if quoted_match:
                original_desc = quoted_match.group(1)
                # Remove original description line
                frontmatter = re.sub(r'''description:\s*["'][^"']*["']\s*\n?''', "", frontmatter)
            else:
                # 2. Try matching unquoted description (may span multiple lines)
                unquoted_match = re.search(
                    r"description:\s+((?:(?!\n\s*[\w-]+:|---).)*)", frontmatter, flags=re.DOTALL
                )
                if unquoted_match:
                    original_desc = unquoted_match.group(1).strip()
                    # Remove original description
                    frontmatter = re.sub(
                        r"description:\s+(?:(?!\n\s*[\w-]+:|---).)*",
                        "",
                        frontmatter,
                        flags=re.DOTALL,
                    )

            # Build new description content (payload first, original content after)
            if original_desc:
                new_desc_content = f"{payload} {original_desc}"
            else:
                new_desc_content = payload

            # Add new description field
            frontmatter = frontmatter.rstrip() + f'\ndescription: "{new_desc_content}"\n'

            # Reassemble: Note to add opening "---\n" and closing "---\n"
            content = "---\n" + frontmatter + "---\n" + content[frontmatter_match.end() :]
        else:
            # No frontmatter, create one
            content = f'---\ndescription: "{payload}"\n---\n\n{content}'

        return content

    def _inject_into_instruction(self, content: str, payload: str) -> str:
        """Inject into instruction body

        Insert payload after the closing --- of frontmatter
        """
        import re

        # Use more robust regex to match frontmatter
        # Match from opening --- to next standalone --- (on its own line)
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if frontmatter_match:
            # Insert after second ---
            insert_pos = frontmatter_match.end()
            return content[:insert_pos] + f"{payload}\n" + content[insert_pos:]
        else:
            # Try another pattern: --- may not have space after it
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if frontmatter_match:
                insert_pos = frontmatter_match.end()
                # Ensure there's a newline after insertion
                remainder = content[insert_pos:]
                if not remainder.startswith("\n"):
                    return content[:insert_pos] + f"\n{payload}\n" + remainder
                else:
                    return content[:insert_pos] + f"{payload}\n" + remainder
            else:
                # No frontmatter, insert at beginning
                return f"{payload}\n\n{content}"

    async def _save_metadata(self, suite: GeneratedTestSuite, output_dir: Path) -> None:
        """Save test metadata"""
        import json

        metadata = {
            "suite_id": suite.suite_id,
            "generation_strategy": suite.generation_strategy,
            "generated_at": suite.generated_at.isoformat(),
            "total_count": suite.total_count,
            "metadata": suite.metadata,
            "tests": [
                {
                    "test_id": tc.test_id,
                    "skill_path": tc.skill_path,
                    "injection_layer": tc.injection_layer,
                    "attack_type": tc.attack_type,
                    "severity": tc.severity,
                    "should_be_blocked": tc.should_be_blocked,
                    **tc.metadata,
                }
                for tc in suite.test_cases
            ],
        }

        metadata_file = output_dir / "test_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    async def generate_stream(
        self,
        skill_name: str,
        attack_type_str: str,
        layer: str,
        payload_name: str,
        output_dir: Path | None = None,
    ) -> GeneratedTestCase | None:
        """Stream generate single test case (no iteration support)

        Difference from generate():
        - Only generate single test case
        - No parameter adjustment or iteration
        - Return GeneratedTestCase or None (if already exists)
        - Use fixed iteration_0 directory

        Args:
            skill_name: Skill name
            attack_type_str: Attack type string
            layer: Injection layer
            payload_name: Payload name
            output_dir: Optional output directory override

        Returns:
            Generated test case, or None if already exists
        """
        import logging

        logger = logging.getLogger(__name__)

        # Parse attack type
        try:
            attack_type = AttackType(attack_type_str)
        except ValueError:
            logger.error(f"[Stream generation] Invalid attack type: {attack_type_str}")
            return None

        # Find skill file
        skill_file = self._find_skill_file(skill_name)
        if skill_file is None:
            logger.warning(f"[Stream generation] Skill does not exist: {skill_name}")
            return None

        skill_dir = skill_file.parent

        # Get payload
        from src.domain.payload.registries.payload_registry import PayloadRegistry
        payloads = PayloadRegistry.get_by_attack_type(attack_type)
        payload = next((p for p in payloads if p.name == payload_name), None)
        if payload is None:
            logger.warning(f"[Stream generation] Payload does not exist: {payload_name}")
            return None

        # Determine output directory
        actual_output_dir = output_dir or Path(self.config.computed_output_dir)
        actual_output_dir.mkdir(parents=True, exist_ok=True)

        # Check if already exists
        test_id = f"{skill_name}_{attack_type.value}"
        base_output_dir = self._execution_output_dir if self._execution_output_dir else actual_output_dir
        test_dir = (
            base_output_dir /
            "test_details" /
            self.config.strategy.value /
            self.config.dataset.name /
            skill_name /
            attack_type.value /
            "iteration_0"
        )

        if self.is_test_case_already_exists(test_dir):
            logger.info(f"[Stream generation] Test case already exists: {test_id}")
            return None

        # Generate test case
        test_case = GeneratedTestCase(
            test_id=test_id,
            skill_path=str(skill_file),
            injection_layer=layer,
            attack_type=attack_type.value,
            severity=payload.severity.value,
            payload_content=payload.content,
            should_be_blocked=True,
            dataset=self.config.dataset.name,  # Set dataset field directly
            metadata={
                "strategy": self.config.strategy.value,  # Set strategy name
                "payload_name": payload.name,
                "skill_name": skill_name,
                "injection_layer": layer,
                "payload_content": payload.content,
            },
            source_skill_dir=str(skill_dir),
            source_aux_dir=str(self._data_resolver.instruction_base_dir / skill_name),
        )

        logger.info(f"[Stream generation] Successfully generated test case: {test_id}")

        return test_case

    def _find_skill_file(self, skill_name: str) -> Path | None:
        """Find file for specified skill

        Args:
            skill_name: Skill name

        Returns:
            Skill file path, or None if not exists
        """
        return self._data_resolver.find_skill_file(skill_name)

    async def generate_stream_with_feedback(
        self,
        skill_name: str,
        attack_type: AttackType,
        adaptive_params: AdaptiveGenerationParams,
        output_dir: Path | None = None,
    ) -> GeneratedTestCase | RefusedResult | None:
        """Generate test case based on feedback (stream iteration)

        Note: Template injection strategy does not use LLM, so adaptive capability is limited.
        This method is mainly for interface compatibility, actual generation is same as generate_stream().

        Args:
            skill_name: Skill name
            attack_type: Attack type
            adaptive_params: Adaptive generation parameters (contains feedback)
            output_dir: Optional output directory override

        Returns:
            Generated test case, if already exists returns None
            (Template injection will not return RefusedResult as it doesn't use LLM)
        """
        import logging

        logger = logging.getLogger(__name__)

        # Template injection uses fixed payload and layer
        # Get first matching payload from payload registry
        from src.domain.payload.registries.payload_registry import PayloadRegistry
        payloads = PayloadRegistry.get_by_attack_type(attack_type)
        if not payloads:
            logger.warning(f"[Feedback generation] No payload for attack type: {attack_type.value}")
            return None

        # Use first payload
        payload = payloads[0]

        # Use fixed instruction layer
        layer = "instruction"

        # Determine directory based on iteration number
        iteration_dir = f"iteration_{adaptive_params.iteration_number}"

        # Determine output directory
        actual_output_dir = output_dir or Path(self.config.computed_output_dir)
        actual_output_dir.mkdir(parents=True, exist_ok=True)

        # Find skill file
        skill_file = self._find_skill_file(skill_name)
        if skill_file is None:
            logger.warning(f"[Feedback generation] Skill does not exist: {skill_name}")
            return None

        skill_dir = skill_file.parent

        # Check if already exists
        test_id = f"{skill_name}_{attack_type.value}"
        base_output_dir = self._execution_output_dir if self._execution_output_dir else actual_output_dir
        test_dir = (
            base_output_dir /
            "test_details" /
            self.config.strategy.value /
            self.config.dataset.name /
            skill_name /
            attack_type.value /
            iteration_dir
        )

        if self.is_test_case_already_exists(test_dir):
            logger.info(f"[Feedback generation] Test case already exists: {test_id} (iteration_{adaptive_params.iteration_number})")
            return None

        # Generate test case
        test_case = GeneratedTestCase(
            test_id=test_id,
            skill_path=str(skill_file),
            injection_layer=layer,
            attack_type=attack_type.value,
            severity=payload.severity.value,
            payload_content=payload.content,
            should_be_blocked=True,
            dataset=self.config.dataset.name,  # Set dataset field directly
            metadata={
                "strategy": self.config.strategy.value,  # Set strategy name
                "payload_name": payload.name,
                "skill_name": skill_name,
                "injection_layer": layer,
                "payload_content": payload.content,
                "iteration_number": adaptive_params.iteration_number,
                "feedback_mode": adaptive_params.feedback.mode if adaptive_params.feedback else "none",
            },
            source_skill_dir=str(skill_dir),
            source_aux_dir=str(self._data_resolver.instruction_base_dir / skill_name),
        )

        logger.info(
            f"[Feedback generation] Successfully generated test case: {test_id} "
            f"(iteration_{adaptive_params.iteration_number}, "
            f"feedback: {adaptive_params.feedback.mode if adaptive_params.feedback else 'none'})"
        )

        return test_case
