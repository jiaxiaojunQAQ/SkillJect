#!/usr/bin/env python3
# ruff: noqa: E402
"""
Security Testing Unified Entry Point

Main entry point for the evaluation framework, supporting streaming test processing mode.

Supports the supported generation strategies (direct_execution, skillject, template_injection).

Usage:
    # Run the default execution plan
    python run.py -c config/main.yaml

    # Run a custom execution-plan file
    python run.py -c /path/to/plan.yaml

    # Limit execution to specific skills
    python run.py -c config/main.yaml --skills adaptyv hmdb-database

    # Override adaptive iteration controls (only applies to skillject)
    python run.py -c config/main.yaml --max-attempts 10
    python run.py -c config/main.yaml --stop-on-success

    # List available skills
    python run.py --list-skills

    # Analyze results
    python run.py --analyze
"""

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

# Add parent directory to path
_parent_path = Path(__file__).parent
if str(_parent_path) not in sys.path:
    sys.path.insert(0, str(_parent_path))

# Add src directory to path
_src_path = _parent_path / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Add shared directory to path
if str(_src_path / "shared") not in sys.path:
    sys.path.insert(0, str(_src_path / "shared"))

# Application service imports depend on the sys.path bootstrap above.
from src.application.services.result_analyzer import ResultAnalyzer, find_latest_result
from src.application.services.streaming_orchestrator import (
    StreamingOrchestrator,
    StreamingProgress,
)
from src.domain.testing.value_objects.execution_config import (
    GenerationConfig,
    GenerationStrategy,
    TwoPhaseExecutionConfig,
)
from src.infrastructure.config.loaders.config_loader import ConfigLoader
from src.infrastructure.loaders import skill_loader
from src.shared.types import AttackType

list_all_skills = skill_loader.list_all_skills


def load_env_file() -> None:
    """Load .env file if it exists

    Attempts to load .env file from multiple possible paths:
    1. Current working directory
    2. run.py directory
    3. Project root directory
    """
    from pathlib import Path

    try:
        from dotenv import load_dotenv
    except ImportError:
        # python-dotenv not installed, silently skip
        return

    # Try multiple possible .env file locations
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return


def print_streaming_progress(progress: StreamingProgress) -> None:
    """Print streaming progress information

    Args:
        progress: Streaming processing progress
    """
    params_str = ", ".join(f"{k}={v}" for k, v in progress.current_params.items())
    print(f"[Generated:{progress.total_generated} Executed:{progress.total_executed} "
          f"Determined:{progress.total_determined} AttackSuccess:{progress.total_success} Blocked:{progress.total_blocked}] "
          f"{progress.current_skill}/{progress.current_attack_type}")
    if params_str:
        print(f"  Parameters: {params_str}")
    if progress.message:
        print(f"  Status: {progress.message}")


def print_attack_type_summary(
    success_tests: list[str],
    blocked_tests: list[str],
    ignored_tests: list[str],
) -> None:
    """Print attack success rate summary by attack type

    Args:
        success_tests: List of attack-succeeded test IDs
        blocked_tests: List of blocked test IDs (excluded from ASR denominator)
        ignored_tests: List of ignored test IDs
    """
    # Group statistics by attack type
    attack_stats: dict[str, dict[str, int]] = {
        at.value: {"success": 0, "blocked": 0, "ignored": 0} for at in AttackType
    }

    # Count blocked tests
    for test_id in blocked_tests:
        for at in AttackType:
            if test_id.endswith(f"_{at.value}"):
                attack_stats[at.value]["blocked"] += 1
                break

    # Count successful attacks
    for test_id in success_tests:
        for at in AttackType:
            if test_id.endswith(f"_{at.value}"):
                attack_stats[at.value]["success"] += 1
                break

    # Count ignored tests
    for test_id in ignored_tests:
        for at in AttackType:
            if test_id.endswith(f"_{at.value}"):
                attack_stats[at.value]["ignored"] += 1
                break

    # Print overall ASR using all determined results.
    total = len(success_tests) + len(blocked_tests) + len(ignored_tests)
    total_asr = len(success_tests) / total if total > 0 else 0.0

    print("\n[Attack Success Rate Summary]")
    print(f"  Overall ASR: {total_asr:.1%} ({len(success_tests)}/{total})")

    # Print ASR grouped by attack type
    print("\n[By Attack Type]")
    for at in AttackType:
        stats = attack_stats[at.value]
        type_total = stats["success"] + stats["blocked"] + stats["ignored"]
        if type_total > 0:
            type_asr = stats["success"] / type_total
            print(
                f"  {at.value}: ASR={type_asr:.1%} "
                f"(Success:{stats['success']}, Ignored:{stats['ignored']}, "
                f"Blocked:{stats['blocked']})"
            )
        else:
            print(f"  {at.value}: No test data")


def validate_config(config_path: Path) -> bool:
    """Validate configuration file

    Args:
        config_path: Configuration file path

    Returns:
        Whether the configuration is valid
    """
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return False

    if config_path.suffix not in (".yaml", ".yml"):
        print(f"Warning: Configuration file may not be in YAML format: {config_path}")

    return True


def check_environment(config: TwoPhaseExecutionConfig) -> list[str]:
    """Check environment configuration

    Args:
        config: Execution configuration

    Returns:
        List of warnings
    """
    warnings = []

    # Check Agent authentication
    if not config.execution.agent.get_auth_token():
        warnings.append(
            f"{config.execution.agent.auth_token_env} environment variable not set, "
            "tests may not run properly"
        )

    # Check Sandbox configuration
    domain = config.execution.sandbox.get_active_domain()
    print(f"OpenSandbox server: {domain}")

    image = config.execution.sandbox.get_active_image()
    print(f"Sandbox image: {image}")

    # Check output directory
    output_dir = config.execution.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    return warnings


def apply_runtime_overrides(
    config: TwoPhaseExecutionConfig,
    *,
    no_retry: bool = False,
) -> TwoPhaseExecutionConfig:
    """Apply CLI runtime overrides to immutable config objects."""
    if not no_retry:
        return config

    updated_execution = replace(
        config.execution,
        retry_failed=False,
        max_retries=0,
    )
    return replace(config, execution=updated_execution)


def _uses_adaptive_iteration(strategy: GenerationStrategy) -> bool:
    """Return True when strategy should use adaptive loop controls."""
    return strategy == GenerationStrategy.SKILLJECT


def _resolve_iteration_controls(
    config: TwoPhaseExecutionConfig,
    *,
    max_attempts_override: int | None,
    stop_on_success_override: bool | None,
) -> tuple[int, bool]:
    """Resolve iteration controls with strategy-aware defaults.

    Only skillject uses adaptive_iteration from config.
    Other strategies run as single-pass by default.
    """
    if _uses_adaptive_iteration(config.generation.strategy):
        max_attempts = (
            max_attempts_override
            if max_attempts_override is not None
            else config.adaptive_iteration.max_attempts
        )
        stop_on_success = (
            stop_on_success_override
            if stop_on_success_override is not None
            else config.adaptive_iteration.stop_on_success
        )
        return max_attempts, stop_on_success

    # Non-adaptive methods: force single-pass unless user explicitly overrides via CLI.
    max_attempts = max_attempts_override if max_attempts_override is not None else 1
    stop_on_success = stop_on_success_override if stop_on_success_override is not None else True
    return max_attempts, stop_on_success


def run_execution_plan(
    config_path: Path,
    execution_plan: list[dict[str, object]],
    skill_names: list[str] | None,
    attack_types: list[str] | None,
    max_attempts_per_test: int | None,
    stop_on_success: bool | None,
    verbose: bool | None,
    no_retry: bool,
    global_step_overrides: dict[str, object] | None = None,
) -> int:
    """Run execution plan sequentially

    Args:
        config_path: Configuration file path
        execution_plan: List of execution steps
        skill_names: List of skills to test
        attack_types: List of attack types to test
        max_attempts_per_test: Maximum attempts per test
        stop_on_success: Whether to stop after success
        verbose: Verbose output
        no_retry: Disable retry

    Returns:
        Exit code
    """
    total_exit_code = 0

    for idx, step in enumerate(execution_plan):
        merged_step = merge_step_with_global_overrides(step, global_step_overrides)
        step_profile_raw = merged_step.get("profile", "openclaw-minimax")
        step_profile = step_profile_raw if isinstance(step_profile_raw, str) else "openclaw-minimax"
        step_name_raw = merged_step.get("name", f"step-{idx + 1}")
        step_name = step_name_raw if isinstance(step_name_raw, str) else f"step-{idx + 1}"

        print(f"\n{'=' * 60}")
        print(f"Execution Plan: {step_name} ({idx + 1}/{len(execution_plan)})")
        print(f"Profile: {step_profile}")
        print(f"{'=' * 60}")

        # Load base config from profile
        try:
            config = ConfigLoader.load(config_path, profile=step_profile)
        except Exception as e:
            print(f"Error: Failed to load profile '{step_profile}': {e}")
            total_exit_code = 1
            continue

        # Apply step overrides
        config = apply_step_overrides(config, merged_step)
        config = apply_runtime_overrides(config, no_retry=no_retry)

        # Use step-specific verbose if provided
        step_verbose = verbose
        if step_verbose is None:
            step_verbose = config.global_config.verbose

        step_max_attempts, step_stop_on_success = _resolve_iteration_controls(
            config,
            max_attempts_override=max_attempts_per_test,
            stop_on_success_override=stop_on_success,
        )

        # Resolve skill selection precedence:
        # 1) CLI --skills
        # 2) step-level skill_names/skills
        # 3) generation.skill_names passed through apply_step_overrides
        step_skill_names = skill_names
        if step_skill_names is None:
            step_skill_names = _normalize_skill_name_list(
                merged_step.get("skill_names", merged_step.get("skills"))
            )
        if step_skill_names is None and config.generation.skill_names:
            step_skill_names = list(config.generation.skill_names)

        # Run streaming evaluation for this step
        exit_code = asyncio.run(run_streaming_evaluation(
            config_path=config_path,
            skill_names=step_skill_names,
            attack_types=attack_types,
            max_attempts_per_test=step_max_attempts,
            stop_on_success=step_stop_on_success,
            verbose=step_verbose,
            profile=step_profile,
            no_retry=no_retry,
            config_override=config,  # Pass pre-configured config
        ))

        if exit_code != 0:
            total_exit_code = exit_code
            print(f"Warning: Step '{step_name}' exited with code {exit_code}")
            # Continue to next step unless explicitly configured to stop

    if total_exit_code != 0:
        print(f"\nExecution plan completed with errors (exit code: {total_exit_code})")
    else:
        print("\nExecution plan completed successfully")

    return total_exit_code


def build_global_step_overrides(raw_config: dict[str, object]) -> dict[str, object]:
    """Build global step overrides from main execution-plan config.

    Supported locations:
    1) Top-level `method` / `dataset` / `instruction` / `skill_names` / `skills` / `llm_judge`
    2) `generation.method` / `generation.dataset` / `generation.instruction`
       / `generation.skill_names` / `generation.skills` / `generation.script_mapping_file`
       / `generation.script_selection`

    Top-level values take precedence over generation section defaults.
    """
    overrides: dict[str, object] = {}

    generation = raw_config.get("generation")
    if isinstance(generation, dict):
        generation_method = generation.get("method")
        if isinstance(generation_method, str) and generation_method:
            overrides["method"] = generation_method

        generation_dataset = generation.get("dataset")
        if isinstance(generation_dataset, dict):
            overrides["dataset"] = generation_dataset.copy()
        elif isinstance(generation_dataset, str) and generation_dataset:
            overrides["dataset"] = generation_dataset

        generation_instruction = generation.get("instruction")
        if isinstance(generation_instruction, str) and generation_instruction:
            overrides["instruction"] = generation_instruction

        generation_skill_names = _normalize_skill_name_list(
            generation.get("skill_names", generation.get("skills"))
        )
        if generation_skill_names:
            overrides["skill_names"] = generation_skill_names

        generation_attack_types = generation.get("attack_types")
        if generation_attack_types:
            overrides["attack_types"] = generation_attack_types

        generation_script_mapping = generation.get("script_mapping_file")
        if isinstance(generation_script_mapping, str) and generation_script_mapping:
            overrides["script_mapping_file"] = generation_script_mapping

        generation_script_selection = generation.get("script_selection")
        if isinstance(generation_script_selection, dict):
            overrides["script_selection"] = generation_script_selection.copy()

    top_level_method = raw_config.get("method")
    if isinstance(top_level_method, str) and top_level_method:
        overrides["method"] = top_level_method

    top_level_dataset = raw_config.get("dataset")
    if isinstance(top_level_dataset, str) and top_level_dataset:
        overrides["dataset"] = top_level_dataset
    elif isinstance(top_level_dataset, dict):
        overrides["dataset"] = top_level_dataset.copy()

    top_level_instruction = raw_config.get("instruction")
    if isinstance(top_level_instruction, str) and top_level_instruction:
        overrides["instruction"] = top_level_instruction

    top_level_skill_names = _normalize_skill_name_list(
        raw_config.get("skill_names", raw_config.get("skills"))
    )
    if top_level_skill_names:
        overrides["skill_names"] = top_level_skill_names

    top_level_attack_types = raw_config.get("attack_types")
    if top_level_attack_types:
        overrides["attack_types"] = top_level_attack_types

    if "llm_judge" in raw_config:
        top_level_judge = raw_config.get("llm_judge")
        if isinstance(top_level_judge, dict):
            overrides["llm_judge"] = top_level_judge.copy()
        elif top_level_judge is None:
            overrides["llm_judge"] = None

    return overrides


def _normalize_skill_name_list(raw_value: object | None) -> list[str] | None:
    """Normalize skill list value from config/CLI-compatible shapes.

    Supported shapes:
    - list[str]
    - str (single skill)
    - {"target_names": [...]} (legacy `skills` object shape)
    """
    if raw_value is None:
        return None

    if isinstance(raw_value, dict):
        raw_value = raw_value.get("target_names")

    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return [normalized] if normalized else None

    if isinstance(raw_value, list):
        normalized_list = [
            str(item).strip()
            for item in raw_value
            if isinstance(item, str) and item.strip()
        ]
        return normalized_list or None

    return None


def _load_strategy_generation_defaults(method_value: str) -> GenerationConfig | None:
    """Load reusable defaults for a public generation method."""
    strategy_path = Path("config/strategies") / f"{method_value}.yaml"
    if not strategy_path.exists():
        return None

    from src.infrastructure.config.loaders.file_loader import FileConfigLoader

    strategy_data = FileConfigLoader.load_yaml(strategy_path)
    strategy_data = _merge_strategy_llm_provider_defaults(strategy_data)
    return GenerationConfig.from_dict(strategy_data)


def _merge_strategy_llm_provider_defaults(
    strategy_data: dict[str, object],
) -> dict[str, object]:
    """Merge config/providers/strategy-llm.yaml into a strategy's llm block."""
    llm_data = strategy_data.get("llm")
    if not isinstance(llm_data, dict):
        return strategy_data

    provider_path = Path("config/providers/strategy-llm.yaml")
    if not provider_path.exists():
        return strategy_data

    from src.infrastructure.config.loaders.file_loader import FileConfigLoader

    provider_data = FileConfigLoader.load_yaml(provider_path)
    llm_keys = {
        "model",
        "base_url",
        "api_key_env",
        "base_url_env",
        "timeout",
        "max_concurrency",
        "temperature",
        "max_tokens",
    }
    provider_llm = {
        key: value
        for key, value in provider_data.items()
        if key in llm_keys
    }
    merged_strategy_data = dict(strategy_data)
    merged_strategy_data["llm"] = {
        **provider_llm,
        **llm_data,
    }
    return merged_strategy_data


def _apply_strategy_defaults(
    current: GenerationConfig,
    defaults: GenerationConfig,
) -> GenerationConfig:
    """Apply method defaults without replacing dataset/filter/runtime selections."""
    return replace(
        defaults,
        dataset=current.dataset,
        attack_types=current.attack_types or defaults.attack_types,
        injection_layers=current.injection_layers or defaults.injection_layers,
        severities=current.severities or defaults.severities,
        skill_names=list(current.skill_names),
        max_tests=current.max_tests,
        max_tests_per_skill=current.max_tests_per_skill,
        save_metadata=current.save_metadata,
        metadata_format=current.metadata_format,
    )


def merge_step_with_global_overrides(
    step: Mapping[str, object],
    global_step_overrides: Mapping[str, object] | None,
) -> dict[str, object]:
    """Merge per-step config with global defaults.

    Precedence:
    - Step-level value wins over global value.
    - For dataset dict, merge shallowly with step keys overriding global keys.
    """
    if not global_step_overrides:
        return dict(step)

    merged: dict[str, object] = {}
    for key, value in global_step_overrides.items():
        if key == "dataset":
            if isinstance(value, dict):
                merged[key] = value.copy()
            elif isinstance(value, str):
                merged[key] = value
        else:
            merged[key] = value

    for key, value in step.items():
        if (
            key == "dataset"
            and isinstance(value, dict)
            and isinstance(merged.get("dataset"), dict)
        ):
            dataset = dict(cast(dict[str, object], merged["dataset"]))
            dataset.update(value)
            merged["dataset"] = dataset
        else:
            merged[key] = value

    return merged


def apply_step_overrides(
    config: TwoPhaseExecutionConfig,
    step: Mapping[str, object],
) -> TwoPhaseExecutionConfig:
    """Apply step overrides to configuration

    Args:
        config: Base configuration from profile
        step: Step definition with override values

    Returns:
        Updated configuration
    """
    from src.domain.testing.value_objects.execution_config import AgentConfig, DatasetConfig

    # Agent override: if agent is a string, load from agents/ directory
    if "agent" in step and step["agent"]:
        agent_value = step["agent"]
        if isinstance(agent_value, str):
            # Load agent config from agents/{agent}.yaml
            agent_config_path = Path("config/agents") / f"{agent_value}.yaml"
            if agent_config_path.exists():
                from src.infrastructure.config.loaders.file_loader import FileConfigLoader
                agent_yaml = FileConfigLoader.load_yaml(agent_config_path)
                agent_dict = agent_yaml.get("agent", {})
                # Convert 'type' to 'agent_type' for AgentConfig.from_dict compatibility
                if "type" in agent_dict and "agent_type" not in agent_dict:
                    agent_dict["agent_type"] = agent_dict.pop("type")
                # Convert to AgentConfig to get proper env defaults
                new_agent = AgentConfig.from_dict(agent_dict)
                config = replace(config, execution=replace(config.execution, agent=new_agent))
        elif isinstance(agent_value, dict):
            # Direct dict overrides
            for key, value in agent_value.items():
                if value is not None and value != "":
                    current_agent = config.execution.agent
                    current_agent = replace(current_agent, **{key: value})
                    config = replace(config, execution=replace(config.execution, agent=current_agent))

    # Model override applies to the execution agent runtime. Strategy LLM model is
    # selected explicitly by config/strategies/{method}.yaml.
    if "model" in step and step["model"]:
        model_value = step["model"]
        if isinstance(model_value, str):
            config = replace(
                config,
                execution=replace(
                    config.execution,
                    agent=replace(config.execution.agent, model=model_value),
                ),
            )

    # Method override: generation strategy (e.g., direct_execution, skillject)
    if "method" in step and step["method"]:
        method_value = step["method"]
        if isinstance(method_value, str):
            # Convert method name to GenerationStrategy enum
            try:
                strategy = GenerationStrategy(method_value)
                strategy_defaults = _load_strategy_generation_defaults(method_value)
                if strategy_defaults is None:
                    generation = replace(config.generation, strategy=strategy)
                else:
                    generation = _apply_strategy_defaults(
                        config.generation,
                        strategy_defaults,
                    )
                config = replace(config, generation=generation)
            except ValueError:
                supported = ", ".join(strategy.value for strategy in GenerationStrategy)
                raise ValueError(
                    f"Unsupported generation method: {method_value}. Supported: {supported}"
                ) from None

    # Dataset override
    if "dataset" in step:
        dataset_overrides = step["dataset"]
        if isinstance(dataset_overrides, str):
            # String dataset: create DatasetConfig directly
            current_dataset = DatasetConfig.from_dict(dataset_overrides)
            config = replace(config, generation=replace(config.generation, dataset=current_dataset))
        elif isinstance(dataset_overrides, dict):
            current_dataset = config.generation.dataset
            for key, value in dataset_overrides.items():
                if value is not None:
                    current_dataset = replace(current_dataset, **{key: value})
            config = replace(config, generation=replace(config.generation, dataset=current_dataset))

    # Instruction override (top-level key, feeds into DatasetConfig.instruction_base_dir)
    instruction_override = step.get("instruction")
    if isinstance(instruction_override, str) and instruction_override:
        current_dataset = config.generation.dataset
        current_dataset = replace(current_dataset, instruction_base_dir=Path(instruction_override))
        config = replace(config, generation=replace(config.generation, dataset=current_dataset))

    # Script mapping file override (for direct_execution method to use custom manifest)
    script_mapping_override = step.get("script_mapping_file")
    if isinstance(script_mapping_override, str) and script_mapping_override:
        config = replace(config, generation=replace(config.generation, script_mapping_file=script_mapping_override))

    # Script selection override (mapping mode / random mode)
    script_selection_override = step.get("script_selection")
    if isinstance(script_selection_override, dict):
        mode = script_selection_override.get("mode", "auto")
        mapping_file = script_selection_override.get("mapping_file")
        if isinstance(mapping_file, str):
            config = replace(
                config,
                generation=replace(
                    config.generation,
                    script_selection_mode=str(mode),
                    script_selection_mapping_file=mapping_file,
                ),
            )
        else:
            config = replace(
                config,
                generation=replace(
                    config.generation,
                    script_selection_mode=str(mode),
                ),
            )

    # Execution overrides
    if "execution" in step:
        exec_overrides = step["execution"]
        if not isinstance(exec_overrides, dict):
            exec_overrides = {}
        current_exec = config.execution
        for key, value in exec_overrides.items():
            if value is not None:
                current_exec = replace(current_exec, **{key: value})
        config = replace(config, execution=current_exec)

    # Generation skill_names override (for config-driven skill selection)
    override_skill_names = _normalize_skill_name_list(
        step.get("skill_names", step.get("skills"))
    )
    if override_skill_names is not None:
        config = replace(
            config,
            generation=replace(
                config.generation,
                skill_names=override_skill_names,
            ),
        )

    # Generation attack_types override
    override_attack_types_raw = step.get("attack_types")
    override_attack_types: list[str] | None = (
        list(override_attack_types_raw) if isinstance(override_attack_types_raw, list) else None
    )
    if override_attack_types is not None:
        config = replace(
            config,
            generation=replace(
                config.generation,
                attack_types=override_attack_types,
            ),
        )

    # Judge override (from execution-plan top-level or per-step llm_judge)
    if "llm_judge" in step:
        judge_overrides = step.get("llm_judge")
        if judge_overrides is None:
            config = replace(config, judge=None)
        elif isinstance(judge_overrides, dict):
            from src.domain.analysis.value_objects.judge_config import JudgeConfig

            config = replace(config, judge=JudgeConfig.from_dict(judge_overrides))
        else:
            raise ValueError(
                "Invalid llm_judge override: expected dict or null"
            )

    return config


async def run_streaming_evaluation(
    config_path: Path,
    skill_names: list[str] | None = None,
    attack_types: list[str] | None = None,
    max_attempts_per_test: int | None = None,
    stop_on_success: bool | None = None,
    verbose: bool | None = None,
    profile: str | None = None,
    no_retry: bool = False,
    config_override: TwoPhaseExecutionConfig | None = None,
) -> int:
    """Run streaming evaluation

    Args:
        config_path: Configuration file path
        skill_names: List of skills to test, None means all
        attack_types: List of attack types to test, None means all
        max_attempts_per_test: Maximum attempts per test
        stop_on_success: Whether to stop after a single success
        verbose: Verbose output (None means read from config file)
        profile: Profile name
        no_retry: Disable retry
        config_override: Pre-configured config (used by execution_plan)

    Returns:
        Exit code
    """
    print("=" * 60)
    print("Streaming Security Evaluation Framework")
    print("=" * 60)

    # Use pre-configured config if provided (from execution_plan), otherwise load
    if config_override is not None:
        config = config_override
    else:
        # Load configuration first (needed for output_dir and save_detailed_logs)
        print(f"\nLoading configuration: {config_path}")
        try:
            config = ConfigLoader.load(config_path, profile=profile)
            config = apply_runtime_overrides(config, no_retry=no_retry)
        except Exception as e:
            print(f"Error: Failed to load configuration: {e}")
            return 1

    # Extract runtime values from config
    if verbose is None:
        verbose = config.global_config.verbose
    max_attempts_per_test, stop_on_success = _resolve_iteration_controls(
        config,
        max_attempts_override=max_attempts_per_test,
        stop_on_success_override=stop_on_success,
    )

    # Configure logging with file output if save_detailed_logs is enabled
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if config.execution.save_detailed_logs:
        # Create output directory and set up file logging
        from src.infrastructure.logging.handlers.file_log_handler import FileLogHandler

        output_dir = config.execution.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        log_handler = FileLogHandler(
            output_dir=output_dir,
            log_level=logging.DEBUG if verbose else logging.INFO,
            log_format=log_format,
        )
        log_handler.setup_logging(
            console_output=True,
            file_output=True,
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Logging system initialized with file output: {output_dir}")
    else:
        # Simple console-only logging
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized (console only)")

    # Check environment
    warnings = check_environment(config)
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    # Create streaming orchestrator (supports all generation strategies)
    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=max_attempts_per_test,
        stop_on_success=stop_on_success,
        max_concurrency=config.execution.max_concurrency,
    )

    # Print configuration
    print("\nConfiguration:")
    print(f"  Max attempts per test: {max_attempts_per_test}")
    print(f"  Stop on success: {stop_on_success}")
    print(f"  Skill-attack concurrency: {config.execution.max_concurrency}")

    # Parse attack types (prioritize CLI arguments, then use config file)
    parsed_attack_types: list[AttackType] | None = None
    if attack_types:
        # CLI arguments take priority
        parsed_attack_types = []
        for at_str in attack_types:
            try:
                parsed_attack_types.append(AttackType(at_str))
            except ValueError:
                print(f"Warning: Invalid attack type: {at_str}")
    elif config.generation.attack_types:
        # Read from config file
        parsed_attack_types = []
        for at_str in config.generation.attack_types:
            try:
                parsed_attack_types.append(AttackType(at_str))
            except ValueError:
                print(f"Warning: Invalid attack type in config file: {at_str}")

    # Execute streaming evaluation
    start_time = datetime.now()
    print(f"\nStart time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    try:
        result = await orchestrator.execute_streaming(
            skill_names=skill_names,
            attack_types=parsed_attack_types,
            progress_callback=print_streaming_progress if verbose else None,
        )

    except Exception as e:
        print(f"\nError: Streaming evaluation failed: {e}")
        import traceback

        if verbose:
            traceback.print_exc()
        return 1

    finally:
        # Cleanup resources
        await orchestrator.cleanup()

    # Print results
    print("\n" + "=" * 60)
    print("Streaming Execution Results")
    print("=" * 60)

    print("\n[Statistics]")
    print(f"  Generated tests: {result.total_generated}")
    print(f"  Executed tests: {result.total_executed}")
    print(f"  Determined results: {result.total_determined}")
    print(f"  Attack succeeded: {result.total_success} ({result.success_rate:.1%})")
    print(f"  Rejected: {result.total_blocked} ({result.block_rate:.1%})")
    print(f"  Ignored: {result.total_ignored} ({result.ignored_rate:.1%})")
    print(f"  Execution time: {result.execution_time_seconds:.2f} seconds")

    if result.success_tests:
        print(f"\nAttack-succeeded tests ({len(result.success_tests)}):")
        for test_id in result.success_tests[:10]:
            print(f"  - {test_id}")
        if len(result.success_tests) > 10:
            print(f"  ... and {len(result.success_tests) - 10} more")

    if result.blocked_tests:
        print(f"\nBlocked tests ({len(result.blocked_tests)}):")
        for test_id in result.blocked_tests[:10]:
            print(f"  - {test_id}")
        if len(result.blocked_tests) > 10:
            print(f"  ... and {len(result.blocked_tests) - 10} more")

    # Print ASR summary by attack type
    print_attack_type_summary(result.success_tests, result.blocked_tests, result.ignored_tests)

    print("\n[Time]")
    print(f"  Start time: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End time: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Save results
    output_dir = config.execution.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    result_file = output_dir / "streaming_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {result_file}")

    # Return exit code
    if result.total_success > 0:
        return 0
    return 1


async def run_loop_evaluation(
    config_path: Path,
    skill_names: list[str] | None = None,
    attack_types: list[str] | None = None,
    max_attempts_per_test: int | None = None,
    stop_on_success: bool | None = None,
    verbose: bool | None = None,
    profile: str | None = None,
    no_retry: bool = False,
    config_override: TwoPhaseExecutionConfig | None = None,
) -> int:
    """Run loop evaluation mode (improved version based on streaming mode)

    Differences from standard streaming mode:
    - Count by unique test cases (each skill x attack_type combination counted once)
    - Any iteration with executed_malicious=True marks the test case as compromised
    - Automatically generate iteration_{N} directory structure
    - Save loop_result.json

    Args:
        config_path: Configuration file path
        skill_names: List of skills to test, None means all
        attack_types: List of attack types to test, None means all
        max_attempts_per_test: Maximum iterations per test
        stop_on_success: Whether to stop after a single success
        verbose: Verbose output (None means read from config file)
        profile: Profile name
        no_retry: Disable retry
        config_override: Pre-configured config (used by execution_plan)

    Returns:
        Exit code
    """
    print("=" * 60)
    print("Loop Security Evaluation Framework (Unique Test Case Counting)")
    print("=" * 60)

    # Use pre-configured config if provided (from execution_plan), otherwise load
    if config_override is not None:
        config = config_override
    else:
        # Load configuration first (needed for output_dir and save_detailed_logs)
        print(f"\nLoading configuration: {config_path}")
        try:
            config = ConfigLoader.load(config_path, profile=profile)
            config = apply_runtime_overrides(config, no_retry=no_retry)
        except Exception as e:
            print(f"Error: Failed to load configuration: {e}")
            return 1

    # Extract runtime values from config
    if verbose is None:
        verbose = config.global_config.verbose
    max_attempts_per_test, stop_on_success = _resolve_iteration_controls(
        config,
        max_attempts_override=max_attempts_per_test,
        stop_on_success_override=stop_on_success,
    )

    # Configure logging with file output if save_detailed_logs is enabled
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if config.execution.save_detailed_logs:
        # Create output directory and set up file logging
        from src.infrastructure.logging.handlers.file_log_handler import FileLogHandler

        output_dir = config.execution.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        log_handler = FileLogHandler(
            output_dir=output_dir,
            log_level=logging.DEBUG if verbose else logging.INFO,
            log_format=log_format,
        )
        log_handler.setup_logging(
            console_output=True,
            file_output=True,
            log_filename="loop_evaluation.log",
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Logging system initialized with file output: {output_dir}")
    else:
        # Simple console-only logging
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized (console only)")

    # Check environment
    warnings = check_environment(config)
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    # Create streaming orchestrator (supports all generation strategies)
    orchestrator = StreamingOrchestrator(
        config=config,
        max_attempts_per_test=max_attempts_per_test,
        stop_on_success=stop_on_success,
        max_concurrency=config.execution.max_concurrency,
    )

    # Print configuration
    print("\nConfiguration:")
    print(f"  Max attempts per test: {max_attempts_per_test}")
    print(f"  Stop on success: {stop_on_success}")
    print(f"  Skill-attack concurrency: {config.execution.max_concurrency}")

    # Parse attack types (prioritize CLI arguments, then use config file)
    parsed_attack_types: list[AttackType] | None = None
    if attack_types:
        # CLI arguments take priority
        parsed_attack_types = []
        for at_str in attack_types:
            try:
                parsed_attack_types.append(AttackType(at_str))
            except ValueError:
                print(f"Warning: Invalid attack type: {at_str}")
    elif config.generation.attack_types:
        # Read from config file
        parsed_attack_types = []
        for at_str in config.generation.attack_types:
            try:
                parsed_attack_types.append(AttackType(at_str))
            except ValueError:
                print(f"Warning: Invalid attack type in config file: {at_str}")

    # Execute streaming evaluation
    start_time = datetime.now()
    print(f"\nStart time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    try:
        result = await orchestrator.execute_streaming(
            skill_names=skill_names,
            attack_types=parsed_attack_types,
            progress_callback=print_streaming_progress if verbose else None,
        )

    except Exception as e:
        print(f"\nError: Loop evaluation failed: {e}")
        import traceback

        if verbose:
            traceback.print_exc()
        return 1

    finally:
        # Cleanup resources
        await orchestrator.cleanup()

    # Print results
    print("\n" + "=" * 60)
    print("Loop Execution Results")
    print("=" * 60)

    # ASR uses all determined test cases.
    total_test_cases = (
        len(result.success_tests) + len(result.blocked_tests) + len(result.ignored_tests)
    )
    asr = len(result.success_tests) / total_test_cases if total_test_cases > 0 else 0.0

    print("\n[Statistics]")
    print(f"  Generated tests: {result.total_generated}")
    print(f"  Executed tests: {result.total_executed}")
    print(f"  Unique test cases: {total_test_cases}")
    print(f"  Determined results: {result.total_determined}")
    print(f"  Undetermined results: {result.total_executed - result.total_determined}")
    print(f"  Attack succeeded: {result.total_success}")
    print(f"  Blocked: {result.total_blocked}")
    print(f"  Ignored: {result.total_ignored}")
    print(f"  Success rate (ASR): {result.success_rate:.1%}")
    print(f"  ASR (all determined test cases): {asr:.1%}")
    print(f"  Block rate: {result.block_rate:.1%}")
    print(f"  Execution time: {result.execution_time_seconds:.2f} seconds")

    if result.success_tests:
        print(f"\nAttack-succeeded tests ({len(result.success_tests)}):")
        for test_id in result.success_tests[:10]:
            print(f"  - {test_id}")
        if len(result.success_tests) > 10:
            print(f"  ... and {len(result.success_tests) - 10} more")

    if result.blocked_tests:
        print(f"\nBlocked tests ({len(result.blocked_tests)}):")
        for test_id in result.blocked_tests[:10]:
            print(f"  - {test_id}")
        if len(result.blocked_tests) > 10:
            print(f"  ... and {len(result.blocked_tests) - 10} more")

    # Print ASR summary by attack type
    print_attack_type_summary(result.success_tests, result.blocked_tests, result.ignored_tests)

    print("\n[Time]")
    print(f"  Start time: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End time: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Save results
    output_dir = config.execution.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    result_file = output_dir / "loop_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {result_file}")

    # Generate final_summary.json file
    from src.application.services.loop_result_analyzer import LoopResultAnalyzer
    analyzer = LoopResultAnalyzer()

    test_dir = Path(config.generation.computed_output_dir)
    if test_dir.exists():
        print("\nGenerating final_summary.json files...")
        summaries = analyzer.aggregate_all_iterations(test_dir)
        print(f"  Generated {len(summaries)} final_summary.json files")

    # Return exit code
    if result.total_success > 0:
        return 0
    return 1


def analyze_results(args: argparse.Namespace) -> int:
    """Analyze results

    Args:
        args: Command line arguments

    Returns:
        Exit code
    """
    result_path = args.result or str(find_latest_result())

    try:
        analyzer = ResultAnalyzer(result_path=result_path)
        print("\n" + analyzer.generate_text_report())

        if args.save_analysis:
            output_path = Path(result_path).parent / "analysis"
            analyzer.save_analysis(str(output_path))
            print(f"\nAnalysis saved: {output_path}")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def print_config_template() -> None:
    """Print configuration template"""
    template = """
# Evaluation Framework Configuration Template

generation:
  method: direct_execution
  skills:
    - INST-1_docx_task3

dataset:
  name: skill_inject
  base_dir: data/skill_inject
  instruction_base_dir: data/instruction/skill_inject

execution_plan:
  - profile: openclaw-minimax

execution:
  max_concurrency: 4
  test_timeout: 1200
  command_timeout: 1200
  retry_failed: true
  max_retries: 2
  output_dir: experiment_results
  save_detailed_logs: true

  sandbox:
    domain: localhost:8080
    image: claude_code:latest

  agent:
    agent_type: claude-code
    auth_token_env: ANTHROPIC_AUTH_TOKEN
    base_url_env: ANTHROPIC_BASE_URL
    model_env: ANTHROPIC_MODEL
    bypass_mode: true

global:
  verbose: false
  log_level: INFO

adaptive_iteration:
  # Only used by skillject.
  # Other methods default to single-pass execution.
  max_attempts: 3
  stop_on_success: false
"""
    print(template)


def main() -> int:
    """Main function

    Returns:
        Exit code
    """
    # Load .env file (before any other operations)
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Security Evaluation Framework (Execution Plan Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Configuration file
    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        default="config/main.yaml",
        help="Configuration file path (default: config/main.yaml)"
    )

    # Test execution options
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum attempts per test (default: method-aware: skillject-family uses config, others use 1)"
    )
    parser.add_argument(
        "--stop-on-success",
        action="store_true",
        default=None,
        help="Early stop on attack success: skip remaining iterations after malicious execution is detected (default: read from config file)"
    )
    parser.add_argument(
        "--success-rate",
        type=float,
        default=None,
        help="Attack success rate (ASR) early stopping threshold (0-1), e.g. 0.8 means stop after 80%% ASR"
    )
    parser.add_argument(
        "--skills",
        type=str,
        nargs="*",
        help="Specify list of skills to test, default tests all skills"
    )
    parser.add_argument(
        "--attack-types",
        type=str,
        nargs="*",
        choices=["information_disclosure", "privilege_escalation",
                 "unauthorized_write", "backdoor_injection"],
        help="Specify list of attack types to test, default tests all types"
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable infrastructure retries for a single direct run"
    )

    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=None,
        help="Verbose output (override verbose setting in config file)"
    )

    args = parser.parse_args()

    # Evaluation mode: load execution_plan from config
    config_path = Path(args.config_path)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {args.config_path}")
        return 1

    # Load execution_plan from main.yaml
    from src.infrastructure.config.loaders.file_loader import FileConfigLoader
    try:
        raw_config = FileConfigLoader.load_yaml(config_path)
        execution_plan = raw_config.get("execution_plan", [])
        if not execution_plan:
            print("Error: no execution_plan found in config")
            return 1
        print(f"\nFound execution_plan with {len(execution_plan)} steps")
        global_step_overrides = build_global_step_overrides(raw_config)
    except Exception as e:
        print(f"Error: Failed to load config: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Run execution plan
    return run_execution_plan(
        config_path=config_path,
        execution_plan=execution_plan,
        skill_names=args.skills,
        attack_types=args.attack_types,
        max_attempts_per_test=args.max_attempts,
        stop_on_success=args.stop_on_success,
        verbose=args.verbose,
        no_retry=args.no_retry,
        global_step_overrides=global_step_overrides,
    )


if __name__ == "__main__":
    sys.exit(main())
