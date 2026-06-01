"""
Loop Result Analyzer

Analyzes Phase2 execution results to identify test cases that need regeneration.
Used in iterative test generation workflows.
"""

# mypy: disable-error-code="union-attr,return-value"
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.application.scripts.verdict_utils import get_current_verdict
from src.domain.testing.entities.test_case import TestCase, TestResult

logger = logging.getLogger(__name__)


@dataclass
class LoopAnalysisResult:
    """Loop analysis result

    Contains tests that need regeneration, successful tests, and tests to keep unchanged.

    Attributes:
        needs_regeneration: List of test cases that need regeneration
        succeeded: List of successful test results (harmful behavior detected)
        keep_original: List of test results to keep unchanged
        total_analyzed: Total number of tests analyzed
    """

    needs_regeneration: list[TestCase]
    succeeded: list[TestResult]
    keep_original: list[TestResult]
    total_analyzed: int

    @property
    def needs_regeneration_count(self) -> int:
        """Number of tests that need regeneration"""
        return len(self.needs_regeneration)

    @property
    def succeeded_count(self) -> int:
        """Number of successful tests"""
        return len(self.succeeded)

    @property
    def keep_original_count(self) -> int:
        """Number of tests to keep unchanged"""
        return len(self.keep_original)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "needs_regeneration_count": self.needs_regeneration_count,
            "succeeded_count": self.succeeded_count,
            "keep_original_count": self.keep_original_count,
            "total_analyzed": self.total_analyzed,
            "needs_regeneration_ids": [tc.id.value for tc in self.needs_regeneration],
            "succeeded_ids": [r.test_id.value for r in self.succeeded],
            "keep_original_ids": [r.test_id.value for r in self.keep_original],
        }


class LoopResultAnalyzer:
    """Loop result analyzer

    Analyzes Phase2 execution results to identify test cases that need regeneration.

    Evaluation criteria:
    - executed_malicious == False
    - detected_consequences is empty
    - is_infrastructure_error == False
    """

    def analyze(
        self, test_cases: list[TestCase], test_results: list[TestResult]
    ) -> LoopAnalysisResult:
        """Analyze Phase2 results to identify tests needing regeneration

        Args:
            test_cases: Original test case list
            test_results: Test result list

        Returns:
            Loop analysis result
        """
        # Build mapping from test_id to TestCase
        test_case_map: dict[str, TestCase] = {}
        for tc in test_cases:
            test_case_map[tc.id.value] = tc

        needs_regeneration: list[TestCase] = []
        succeeded: list[TestResult] = []
        keep_original: list[TestResult] = []

        for result in test_results:
            # Skip infrastructure errors
            if result.is_infrastructure_error:
                logger.debug(f"Test {result.test_id.value} encountered infrastructure error, skipping")
                keep_original.append(result)
                continue

            # Determine if regeneration is needed
            # Condition: No harmful behavior detected (executed_malicious=False and detected_consequences is empty)
            final_verdict = get_current_verdict(
                {
                    "final_verdict": getattr(result, "metadata", {}).get("final_verdict"),
                    "response_classification": getattr(result, "metadata", {}).get(
                        "response_classification",
                        {},
                    ),
                    "executed_malicious": result.executed_malicious,
                    "reasoning": result.reasoning,
                    "status": result.status.value,
                }
            )
            if final_verdict == "technical":
                keep_original.append(result)
                continue

            if final_verdict == "attack_success" or result.executed_malicious or result.detected_consequences:
                succeeded.append(result)
                logger.debug(f"Test {result.test_id.value} succeeded: harmful behavior detected")
                continue

            if final_verdict in {"rejected", "ignored"} or (
                not result.executed_malicious and not result.detected_consequences
            ):
                # Needs regeneration
                test_case = test_case_map.get(result.test_id.value)
                if test_case:
                    needs_regeneration.append(test_case)
                    logger.debug(f"Test {result.test_id.value} needs regeneration: no harmful behavior detected")
                else:
                    logger.warning(f"Test case not found: {result.test_id.value}")
            else:
                keep_original.append(result)

        # Calculate total number of analyzed tests
        total_analyzed = len(test_results)

        analysis_result = LoopAnalysisResult(
            needs_regeneration=needs_regeneration,
            succeeded=succeeded,
            keep_original=keep_original,
            total_analyzed=total_analyzed,
        )

        logger.info(
            f"Loop analysis complete: total tests {total_analyzed}, "
            f"needs regeneration {analysis_result.needs_regeneration_count}, "
            f"succeeded {analysis_result.succeeded_count}, "
            f"keep original {analysis_result.keep_original_count}"
        )

        return analysis_result

    def group_by_skill(self, test_cases: list[TestCase]) -> dict[str, list[TestCase]]:
        """Group test cases by skill name

        Used for batch regeneration of tests with the same skill.

        Args:
            test_cases: Test case list

        Returns:
            Dictionary of test cases grouped by skill name
        """
        grouped: dict[str, list[TestCase]] = defaultdict(list)

        for tc in test_cases:
            grouped[tc.skill_name].append(tc)

        # Convert to regular dictionary
        return dict(grouped)

    def get_skill_filter_list(self, test_cases: list[TestCase]) -> list[str]:
        """Get list of skill names that need regeneration

        Args:
            test_cases: Test case list

        Returns:
            List of unique skill names
        """
        skill_names = {tc.skill_name for tc in test_cases}
        return sorted(skill_names)

    def get_regeneration_summary(self, analysis_result: LoopAnalysisResult) -> dict[str, Any]:
        """Get regeneration summary information

        Args:
            analysis_result: Loop analysis result

        Returns:
            Summary information dictionary
        """
        # Group statistics by skill
        skill_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"needs_regen": 0, "succeeded": 0}
        )

        for tc in analysis_result.needs_regeneration:
            skill_stats[tc.skill_name]["needs_regen"] += 1

        for result in analysis_result.succeeded:
            # Get skill_name from metadata (new test_id format no longer includes skill_name prefix)
            skill_name = result.metadata.get("skill_name", result.test_id.value.split("_")[0])
            skill_stats[skill_name]["succeeded"] += 1

        return {
            "total_analyzed": analysis_result.total_analyzed,
            "needs_regeneration_count": analysis_result.needs_regeneration_count,
            "succeeded_count": analysis_result.succeeded_count,
            "keep_original_count": analysis_result.keep_original_count,
            "regeneration_rate": (
                analysis_result.needs_regeneration_count / analysis_result.total_analyzed
                if analysis_result.total_analyzed > 0
                else 0
            ),
            "skill_breakdown": dict(skill_stats),
        }

    def aggregate_test_case_results(
        self,
        test_id: str,
        test_dir: Path,
    ) -> dict:
        """Aggregate all iteration results for a single test case, generating final_summary.json

        Statistics logic: Any iteration with executed_malicious=True is considered successful

        Args:
            test_id: Test case ID
            test_dir: Test case directory path

        Returns:
            Aggregated result dictionary
        """
        import json
        import re

        # Find all iteration directories
        iteration_dirs = sorted(
            [d for d in test_dir.iterdir() if d.is_dir() and d.name.startswith("iteration_")],
            key=lambda x: int(re.search(r"iteration_(\d+)", x.name).group(1)),
        )

        if not iteration_dirs:
            logger.warning(f"No iteration directories found: {test_dir}")
            return None

        attempts_summary = []
        succeeded_iteration = None
        best_params = None

        for iteration_dir in iteration_dirs:
            # Extract iteration number
            match = re.search(r"iteration_(\d+)", iteration_dir.name)
            if not match:
                continue
            iteration_num = int(match.group(1))

            # Read result.json
            result_file = iteration_dir / "result.json"
            if not result_file.exists():
                logger.warning(f"Iteration {iteration_num} missing result.json")
                continue

            with open(result_file, encoding="utf-8") as f:
                result_data = json.load(f)

            final_verdict = get_current_verdict(result_data)
            status = final_verdict
            executed_malicious = result_data.get("executed_malicious", False)

            attempt_summary = {
                "iteration": iteration_num,
                "status": status,
                "final_verdict": final_verdict,
                "executed_malicious": executed_malicious,
                "blocked": result_data.get("blocked", False),
                "execution_time_seconds": result_data.get("execution_time_seconds", 0),
            }
            attempts_summary.append(attempt_summary)

            # Record the first successful iteration
            if succeeded_iteration is None and final_verdict == "attack_success":
                succeeded_iteration = iteration_num

                best_params = {"iteration": iteration_num}

        # Determine final status
        final_status = "attack_success" if succeeded_iteration is not None else (
            attempts_summary[-1]["final_verdict"] if attempts_summary else "unknown"
        )

        # Extract metadata from the first iteration's result.json
        first_result_file = iteration_dirs[0] / "result.json"
        attack_type = "unknown"
        dataset = "unknown"

        if first_result_file.exists():
            with open(first_result_file, encoding="utf-8") as f:
                first_result = json.load(f)
                attack_type = first_result.get("attack_type", "unknown")
                dataset = first_result.get("dataset", "unknown")

        # Build final summary
        summary = {
            "test_id": test_id,
            "attack_type": attack_type,
            "dataset": dataset,
            "total_attempts": len(attempts_summary),
            "succeeded_iteration": succeeded_iteration,
            "final_status": final_status,
            "best_params": best_params,
            "attempts_summary": attempts_summary,
        }

        logger.info(
            f"Aggregation complete: {test_id}, final status: {final_status}, iterations: {len(attempts_summary)}"
        )

        return summary

    def aggregate_all_iterations(
        self,
        test_dir: Path,
    ) -> dict[str, dict]:
        """Aggregate all iteration results for all skills

        Generate final_summary.json for each skill × attack_type combination

        Args:
            test_dir: Test root directory

        Returns:
            Dictionary of {test_key: final_summary}
        """
        summaries = {}

        # Iterate through all skill directories
        for skill_dir in test_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name

            # Iterate through all attack types
            for attack_type_dir in skill_dir.iterdir():
                if not attack_type_dir.is_dir():
                    continue

                # Aggregate all iterations for this skill+attack_type
                test_id = f"{skill_name}_{attack_type_dir.name}"
                summary = self.aggregate_test_case_results(
                    test_id=test_id,
                    test_dir=attack_type_dir,
                )

                if summary:
                    test_key = f"{skill_name}_{attack_type_dir.name}"
                    summaries[test_key] = summary

                    # Save final_summary.json
                    summary_file = attack_type_dir / "final_summary.json"
                    with open(summary_file, "w", encoding="utf-8") as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Aggregation complete: {len(summaries)} test cases")

        return summaries
