# mypy: disable-error-code="abstract"
"""
Test Generation Strategy Factory
"""

from pathlib import Path

from src.domain.testing.value_objects.execution_config import (
    GenerationConfig,
    GenerationStrategy,
)
from src.infrastructure.loaders.paths import resolve_data_path

from .baseline_generator import BaselineGenerator
from .direct_execution_generator import DirectExecutionGenerator
from .generation_strategy import TestGenerationStrategy
from .script_selector import MappingScriptSelector, RandomScriptSelector, ScriptSelector
from .skillject_generator import SkilljectGenerator
from .template_injection_generator import TemplateInjectionGenerator


class TestGenerationStrategyFactory:
    """Test generation strategy factory

    Creates corresponding generator instances based on configuration
    """

    _strategies = {
        GenerationStrategy.TEMPLATE_INJECTION: TemplateInjectionGenerator,
        GenerationStrategy.SKILLJECT: SkilljectGenerator,
        GenerationStrategy.DIRECT_EXECUTION: DirectExecutionGenerator,
        GenerationStrategy.BASELINE: BaselineGenerator,
    }

    @staticmethod
    def _selector_for(strategy: GenerationStrategy, config: GenerationConfig) -> ScriptSelector:
        scripts_base_dir = resolve_data_path("data/bash_scripts")
        mode = config.script_selection_mode

        if mode == "mapping":
            mapping_file = config.script_selection_mapping_file or config.script_mapping_file
            manifest_path = (
                resolve_data_path(mapping_file)
                if mapping_file
                else resolve_data_path("data/skill_inject/manifest.json")
            )
            return MappingScriptSelector(manifest_path)
        elif mode == "random":
            return RandomScriptSelector(scripts_base_dir)
        else:  # auto - strategy-based default
            if strategy == GenerationStrategy.DIRECT_EXECUTION:
                manifest_path = (
                    resolve_data_path(config.script_mapping_file)
                    if config.script_mapping_file
                    else resolve_data_path("data/skill_inject/manifest.json")
                )
                return MappingScriptSelector(manifest_path)
            return RandomScriptSelector(scripts_base_dir)

    @classmethod
    def create(
        cls,
        config: GenerationConfig,
        execution_output_dir: Path | None = None,
    ) -> TestGenerationStrategy:
        """Create a generator instance

        Args:
            config: Generation configuration
            execution_output_dir: Optional execution output directory (for saving to test_details)

        Returns:
            TestGenerationStrategy generator instance

        Raises:
            ValueError: Unsupported generation strategy
        """
        strategy_class = cls._strategies.get(config.strategy)

        if strategy_class is None:
            raise ValueError(f"Unsupported generation strategy: {config.strategy}")

        # Baseline strategy does not need a script selector
        selector = None
        if config.strategy != GenerationStrategy.BASELINE:
            selector = cls._selector_for(config.strategy, config)

        # Build kwargs based on what the generator accepts
        import inspect
        sig = inspect.signature(strategy_class.__init__)
        kwargs: dict = {"config": config}
        if "execution_output_dir" in sig.parameters:
            kwargs["execution_output_dir"] = execution_output_dir
        if "script_selector" in sig.parameters:
            kwargs["script_selector"] = selector
        return strategy_class(**kwargs)

    @classmethod
    def register_strategy(
        cls,
        strategy: GenerationStrategy,
        strategy_class: type[TestGenerationStrategy],
    ) -> None:
        """Register a custom strategy"""
        cls._strategies[strategy] = strategy_class


def get_generator(
    config: GenerationConfig,
    execution_output_dir: Path | None = None,
) -> TestGenerationStrategy:
    """Convenience function to get a generator"""
    return TestGenerationStrategyFactory.create(config, execution_output_dir)
