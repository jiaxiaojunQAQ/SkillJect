#!/usr/bin/env python3
"""
Security Testing Unified Entry Point

Main entry point for the evaluation framework, supporting streaming test processing mode.

Supports all generation strategies (skillject, template_injection, llm_intelligent).

Usage:
    # Run streaming evaluation with config file (default)
    python run.py -c config/skillject.yaml
    python run.py -c config/template_injection.yaml
    python run.py -c config/llm_intelligent.yaml

    # Enable streaming test processing mode
    python run.py -c config/skillject.yaml --streaming

    # Streaming mode: specify skills and attack types
    python run.py -c config/skillject.yaml --streaming --skills adaptyv hmdb-database

    # Streaming mode: enable early stopping
    python run.py -c config/skillject.yaml --streaming --stop-on-success

    # Streaming mode: set maximum attempts
    python run.py -c config/skillject.yaml --streaming --max-attempts 10

    # Enable loop test generation mode (recommended: unique test case counting)
    python run.py -c config/skillject.yaml --enable-loop

    # Loop mode: specify skills and attack types
    python run.py -c config/skillject.yaml --enable-loop --skills adaptyv

    # Loop mode: set maximum iterations
    python run.py -c config/skillject.yaml --enable-loop --max-iterations 10

    # List available skills
    python run.py --list-skills

    # Analyze results
    python run.py --analyze
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

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

from src.infrastructure.loaders import skill_loader
from src.infrastructure.config.loaders.config_loader import ConfigLoader
from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig
# Application service imports - result analysis
from src.application.services.result_analyzer import ResultAnalyzer, find_latest_result
# Application service imports - streaming orchestrator
from src.application.services.streaming_orchestrator import (
    StreamingOrchestrator,
    StreamingProgress,
)
from src.shared.types import AttackType

list_all_skills = skill_loader.list_all_skills


def load_env_file():
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
          f"Determined:{progress.total_determined} Succeeded:{progress.total_succeeded} Failed:{progress.total_failed}] "
          f"{progress.current_skill}/{progress.current_attack_type}")
    if params_str:
        print(f"  Parameters: {params_str}")
    if progress.message:
        print(f"  Status: {progress.message}")


def print_attack_type_summary(succeeded_tests: list[str], failed_tests: list[str]) -> None:
    """Print attack success rate summary by attack type

    Args:
        succeeded_tests: List of blocked test IDs (defense successful)
        failed_tests: List of maliciously executed test IDs (attack successful)
    """
    # Group statistics by attack type
    attack_stats: dict[str, dict[str, int]] = {
        at.value: {"succeeded": 0, "failed": 0} for at in AttackType
    }

    # Count blocked tests
    for test_id in succeeded_tests:
        for at in AttackType:
            if test_id.endswith(f"_{at.value}"):
                attack_stats[at.value]["succeeded"] += 1
                break

    # Count successful attacks
    for test_id in failed_tests:
        for at in AttackType:
            if test_id.endswith(f"_{at.value}"):
                attack_stats[at.value]["failed"] += 1
                break

    # Print overall ASR
    total = len(succeeded_tests) + len(failed_tests)
    total_asr = len(failed_tests) / total if total > 0 else 0.0

    print(f"\n[Attack Success Rate Summary]")
    print(f"  Overall ASR: {total_asr:.1%} ({len(failed_tests)}/{total})")

    # Print ASR grouped by attack type
    print(f"\n[By Attack Type]")
    for at in AttackType:
        stats = attack_stats[at.value]
        type_total = stats["succeeded"] + stats["failed"]
        if type_total > 0:
            type_asr = stats["failed"] / type_total
            print(
                f"  {at.value}: ASR={type_asr:.1%} "
                f"(Attacks succeeded:{stats['failed']}, Blocked:{stats['succeeded']})"
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
    import os

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


async def run_streaming_evaluation(
    config_path: Path,
    skill_names: list[str] | None = None,
    attack_types: list[str] | None = None,
    max_attempts_per_test: int | None = None,
    stop_on_success: bool | None = None,
    verbose: bool | None = None,
) -> int:
    """Run streaming evaluation

    Args:
        config_path: Configuration file path
        skill_names: List of skills to test, None means all
        attack_types: List of attack types to test, None means all
        max_attempts_per_test: Maximum attempts per test
        stop_on_success: Whether to stop after a single success
        verbose: Verbose output (None means read from config file)

    Returns:
        Exit code
    """
    print("=" * 60)
    print("Streaming Security Evaluation Framework (Feedback-Driven Adaptive Iteration)")
    print("=" * 60)

    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")

    # Load configuration
    print(f"\nLoading configuration: {config_path}")
    try:
        config = ConfigLoader.load(config_path)
        # If verbose is not specified (None), use value from config file
        if verbose is None:
            verbose = config.global_config.verbose
        # If max_attempts_per_test is not specified (None), use value from config file
        if max_attempts_per_test is None:
            max_attempts_per_test = config.adaptive_iteration.max_attempts
        # If stop_on_success is not specified (None), use value from config file
        if stop_on_success is None:
            stop_on_success = config.adaptive_iteration.stop_on_success
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}")
        return 1

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
    print(f"\nConfiguration:")
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

    print(f"\n[Statistics]")
    print(f"  Generated tests: {result.total_generated}")
    print(f"  Executed tests: {result.total_executed}")
    print(f"  Determined results: {result.total_determined}")
    print(f"  Undetermined results: {result.total_executed - result.total_determined}")
    print(f"  Succeeded (blocked): {result.total_succeeded}")
    print(f"  Failed (malicious execution): {result.total_failed}")
    print(f"  Success rate: {result.success_rate:.1%}")
    print(f"  Execution time: {result.execution_time_seconds:.2f} seconds")

    if result.succeeded_tests:
        print(f"\nSuccessful tests ({len(result.succeeded_tests)}):")
        for test_id in result.succeeded_tests[:10]:
            print(f"  - {test_id}")
        if len(result.succeeded_tests) > 10:
            print(f"  ... and {len(result.succeeded_tests) - 10} more")

    if result.failed_tests:
        print(f"\nFailed tests ({len(result.failed_tests)}):")
        for test_id in result.failed_tests[:10]:
            print(f"  - {test_id}")
        if len(result.failed_tests) > 10:
            print(f"  ... and {len(result.failed_tests) - 10} more")

    # Print ASR summary by attack type
    print_attack_type_summary(result.succeeded_tests, result.failed_tests)

    print(f"\n[Time]")
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
    if result.total_succeeded > 0:
        return 0
    return 1


async def run_loop_evaluation(
    config_path: Path,
    skill_names: list[str] | None = None,
    attack_types: list[str] | None = None,
    max_attempts_per_test: int | None = None,
    stop_on_success: bool | None = None,
    verbose: bool | None = None,
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

    Returns:
        Exit code
    """
    print("=" * 60)
    print("Loop Security Evaluation Framework (Unique Test Case Counting)")
    print("=" * 60)

    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")

    # Load configuration
    print(f"\nLoading configuration: {config_path}")
    try:
        config = ConfigLoader.load(config_path)
        # If verbose is not specified (None), use value from config file
        if verbose is None:
            verbose = config.global_config.verbose
        # If max_attempts_per_test is not specified (None), use value from config file
        if max_attempts_per_test is None:
            max_attempts_per_test = config.adaptive_iteration.max_attempts
        # If stop_on_success is not specified (None), use value from config file
        if stop_on_success is None:
            stop_on_success = config.adaptive_iteration.stop_on_success
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}")
        return 1

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
    print(f"\nConfiguration:")
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

    # Calculate correct ASR (count by test cases)
    total_test_cases = len(result.succeeded_tests) + len(result.failed_tests)
    asr = len(result.failed_tests) / total_test_cases if total_test_cases > 0 else 0.0

    print(f"\n[Statistics]")
    print(f"  Generated tests: {result.total_generated}")
    print(f"  Executed tests: {result.total_executed}")
    print(f"  Unique test cases: {total_test_cases}")
    print(f"  Determined results: {result.total_determined}")
    print(f"  Undetermined results: {result.total_executed - result.total_determined}")
    print(f"  Blocked (defense successful): {result.total_succeeded}")
    print(f"  Malicious execution (attack successful): {result.total_failed}")
    print(f"  Success rate: {result.success_rate:.1%}")
    print(f"  ASR (by test case): {asr:.1%}")
    print(f"  Execution time: {result.execution_time_seconds:.2f} seconds")

    if result.succeeded_tests:
        print(f"\nSuccessful tests ({len(result.succeeded_tests)}):")
        for test_id in result.succeeded_tests[:10]:
            print(f"  - {test_id}")
        if len(result.succeeded_tests) > 10:
            print(f"  ... and {len(result.succeeded_tests) - 10} more")

    if result.failed_tests:
        print(f"\nFailed tests ({len(result.failed_tests)}):")
        for test_id in result.failed_tests[:10]:
            print(f"  - {test_id}")
        if len(result.failed_tests) > 10:
            print(f"  ... and {len(result.failed_tests) - 10} more")

    # Print ASR summary by attack type
    print_attack_type_summary(result.succeeded_tests, result.failed_tests)

    print(f"\n[Time]")
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
    if result.total_succeeded > 0:
        return 0
    return 1


def analyze_results(args) -> int:
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
  config_file: config/skillject.yaml  # or config/template_injection.yaml

dataset:
  name: skills_sample
  base_dir: data/skills_sample

execution:
  max_concurrency: 4
  test_timeout: 120
  command_timeout: 300
  retry_failed: true
  max_retries: 2
  output_dir: experiment_results
  save_detailed_logs: true

  sandbox:
    domain: localhost:8080
    image: claude_code:v5

  agent:
    agent_type: claude-code
    auth_token_env: ANTHROPIC_AUTH_TOKEN
    base_url_env: ANTHROPIC_BASE_URL
    model_env: ANTHROPIC_MODEL
    bypass_mode: true

global:
  verbose: false
  log_level: INFO

advanced:
  batch_size: 10

adaptive_iteration:
  max_attempts_per_test: 3
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

    import argparse

    parser = argparse.ArgumentParser(
        description="Security Evaluation Framework (Streaming Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--analyze", "-A", action="store_true", help="Analysis mode: analyze latest results"
    )
    mode_group.add_argument(
        "--list-skills", action="store_true", help="List all available skills"
    )
    mode_group.add_argument(
        "--config-template", action="store_true", help="Print configuration template"
    )

    # Configuration file
    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        default="config/skillject.yaml",
        help="Configuration file path (default: config/skillject.yaml)"
    )

    # Streaming test processing options (only supports skillject strategy)
    parser.add_argument(
        "--enable-loop",
        action="store_true",
        help="[Deprecated] Streaming mode enables feedback-driven adaptive iteration by default"
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="[Deprecated] Streaming mode is the default mode"
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum attempts per test (default: read from config file)"
    )
    parser.add_argument(
        "--stop-on-success",
        action="store_true",
        default=None,
        help="Early stop on success: skip remaining iterations after test is blocked (default: read from config file)"
    )
    parser.add_argument(
        "--success-rate",
        type=float,
        default=None,
        help="Success rate early stopping threshold (0-1), e.g. 0.8 means stop after 80%% success rate"
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

    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=None,
        help="Verbose output (override verbose setting in config file)"
    )

    # Analysis parameters
    parser.add_argument("--result", "-r", help="Specify result file path for analysis")
    parser.add_argument("--save-analysis", action="store_true", help="Save analysis results")

    args = parser.parse_args()

    # List skills
    if args.list_skills:
        # Load config to get dataset path
        config_path = Path(args.config_path) if args.config_path else None

        # Try multiple possible config paths
        if config_path and not config_path.exists():
            possible_paths = [
                Path("config/main.yaml"),
                Path("evaluation/config/main.yaml"),
                Path("evaluation/config/template_injection.yaml"),
            ]
            for p in possible_paths:
                if p.exists():
                    config_path = p
                    break

        dataset_dir = None
        if config_path and config_path.exists():
            try:
                config = ConfigLoader.load(config_path)
                dataset_dir = str(config.generation.dataset.base_dir)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}, using default dataset")

        skills = list_all_skills(base_dir=dataset_dir)
        print("\nAvailable skills:")
        for name in skills:
            print(f"  - {name}")
        if not skills:
            print("  (No available skills found)")
        if dataset_dir:
            print(f"\nTotal {len(skills)} skills (from {dataset_dir})")
        else:
            print(f"\nTotal {len(skills)} skills (using default dataset)")
        return 0

    # Print config template
    if args.config_template:
        print_config_template()
        return 0

    # Analysis mode
    if args.analyze:
        return analyze_results(args)

    # Evaluation mode
    config_path = Path(args.config_path)

    # Try multiple possible config paths
    if not config_path.exists():
        possible_paths = [
            Path("config/main.yaml"),
            Path("evaluation/config/main.yaml"),
            Path("evaluation/config/template_injection.yaml"),
        ]
        for p in possible_paths:
            if p.exists():
                config_path = p
                print(f"Using config file: {config_path}")
                break

    if not config_path.exists():
        print(f"Error: Configuration file not found: {args.config_path}")
        print(f"Hint: Use --config-template to view configuration template")
        print(f"      or ensure config/main.yaml file exists")
        return 1

    # Run evaluation
    if args.enable_loop:
        # Loop test mode (improved version based on streaming mode)
        return asyncio.run(run_loop_evaluation(
            config_path=config_path,
            skill_names=args.skills,
            attack_types=args.attack_types,
            max_attempts_per_test=args.max_attempts,
            stop_on_success=args.stop_on_success,
            verbose=args.verbose,
        ))
    else:
        # Default: streaming mode
        return asyncio.run(run_streaming_evaluation(
            config_path=config_path,
            skill_names=args.skills,
            attack_types=args.attack_types,
            max_attempts_per_test=args.max_attempts,
            stop_on_success=args.stop_on_success,
            verbose=args.verbose,
        ))


if __name__ == "__main__":
    sys.exit(main())
