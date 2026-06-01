"""
Statistics Aggregator Domain Service

Responsible for aggregating and calculating statistics data
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# Grouped Statistics Utilities (merged from src/statistics.py)
# =============================================================================


@dataclass
class GroupStatsLegacy:
    """Grouped statistics data structure (legacy compatible)

    Note: New code should use GroupStats, this class is mainly for backward compatibility
    """

    total: int = 0
    passed: int = 0
    blocked: int = 0
    malicious_executed: int = 0
    pass_rate: str = "0.0%"
    block_rate: str = "0.0%"
    # Extended fields for extra statistics like risk
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self.total,
            "passed": self.passed,
            "blocked": self.blocked,
            "malicious_executed": self.malicious_executed,
            "pass_rate": self.pass_rate,
            "block_rate": self.block_rate,
            **self.extra,
        }


class StatisticsGrouper:
    """Unified grouped statistics calculator (merged from src/statistics.py)

    Provides field-based grouping statistics functionality, supporting both object and dictionary data formats.
    Mainly for backward compatibility with old code like result_analyzer.py
    """

    @staticmethod
    def group_by_field(
        results: list[Any],
        field: str,
        get_value: Callable[[Any], str] = None,
    ) -> dict[str, GroupStatsLegacy]:
        """
        Group statistics by field

        Args:
            results: Result list
            field: Field name
            get_value: Custom value getter function

        Returns:
            Grouped statistics dictionary
        """
        groups: dict[str, GroupStatsLegacy] = {}

        for result in results:
            if get_value:
                key = get_value(result)
            else:
                key = getattr(result, field, "")

            if key not in groups:
                groups[key] = GroupStatsLegacy()

            groups[key].total += 1
            if getattr(result, "passed", False):
                groups[key].passed += 1
            if getattr(result, "blocked", False):
                groups[key].blocked += 1
            # Support both attribute names
            if getattr(result, "executed_malicious", False) or getattr(
                result, "malicious_executed", False
            ):
                groups[key].malicious_executed += 1

        # Calculate percentages
        for stats in groups.values():
            if stats.total > 0:
                stats.pass_rate = f"{stats.passed / stats.total * 100:.1f}%"
                stats.block_rate = f"{stats.blocked / stats.total * 100:.1f}%"

        return groups

    @staticmethod
    def group_dict_by_field(
        results: list[dict],
        field: str,
    ) -> dict[str, GroupStatsLegacy]:
        """
        Group statistics by field (dictionary version)

        Args:
            results: Dictionary result list
            field: Field name

        Returns:
            Grouped statistics dictionary
        """
        return StatisticsGrouper.group_by_field(results, field, lambda r: r.get(field, ""))

    @staticmethod
    def group_dict_by_field_with_dict_result(
        results: list[dict],
        field: str,
    ) -> dict[str, dict]:
        """
        Group statistics by field (dictionary version, returns dictionary result)

        This method is compatible with existing code scenarios expecting dictionary return values

        Args:
            results: Dictionary result list
            field: Field name

        Returns:
            Grouped statistics dictionary (values are plain dictionaries)
        """
        groups = StatisticsGrouper.group_dict_by_field(results, field)
        return {k: v.to_dict() for k, v in groups.items()}


# =============================================================================
# DDD Statistics Aggregator (original)
# =============================================================================


@dataclass
class GroupStats:
    """Grouped statistics"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    malicious: int = 0

    @property
    def pass_rate(self) -> float:
        """Pass rate"""
        return self.passed / self.total * 100 if self.total > 0 else 0.0

    @property
    def block_rate(self) -> float:
        """Block rate"""
        return self.blocked / self.total * 100 if self.total > 0 else 0.0

    @property
    def malicious_rate(self) -> float:
        """Malicious execution rate"""
        return self.malicious / self.total * 100 if self.total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "blocked": self.blocked,
            "malicious": self.malicious,
            "pass_rate": f"{self.pass_rate:.1f}%",
            "block_rate": f"{self.block_rate:.1f}%",
            "malicious_rate": f"{self.malicious_rate:.1f}%",
        }


class StatisticsAggregator:
    """Statistics aggregator

    Responsible for aggregating statistical data from test results
    """

    def __init__(self):
        self._results: list[Any] = []

    def add_results(self, results: list[Any]) -> None:
        """Add results

        Args:
            results: Result list
        """
        self._results.extend(results)

    def clear(self) -> None:
        """Clear results"""
        self._results.clear()

    def get_total(self) -> int:
        """Get total count"""
        return len(self._results)

    def count_by(self, key: str, value: Any) -> int:
        """Count by specified key-value pair

        Args:
            key: Statistics key
            value: Target value

        Returns:
            Count
        """
        count = 0
        for r in self._results:
            r_value = self._get_value(r, key)
            if r_value == value:
                count += 1
        return count

    def count_passed(self) -> int:
        """Count passed"""
        return self._count_by_condition("passed", True)

    def count_failed(self) -> int:
        """Count failed"""
        return self._count_by_condition("passed", False)

    def count_blocked(self) -> int:
        """Count blocked"""
        return self._count_by_condition("blocked", True)

    def count_malicious(self) -> int:
        """Count malicious executions"""
        return self._count_by_condition("executed_malicious", True)

    def group_by_layer(self) -> dict[str, GroupStats]:
        """Group by injection layer

        Returns:
            Layer statistics dictionary
        """
        return self._group_by("layer")

    def group_by_attack_type(self) -> dict[str, GroupStats]:
        """Group by attack type

        Returns:
            Attack type statistics dictionary
        """
        return self._group_by("attack_type")

    def group_by_severity(self) -> dict[str, GroupStats]:
        """Group by severity

        Returns:
            Severity statistics dictionary
        """
        return self._group_by("severity")

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics

        Returns:
            Summary statistics dictionary
        """
        total = self.get_total()

        return {
            "total_tests": total,
            "passed": self.count_passed(),
            "failed": self.count_failed(),
            "blocked": self.count_blocked(),
            "malicious": self.count_malicious(),
            "pass_rate": self.count_passed() / total * 100 if total > 0 else 0.0,
            "block_rate": self.count_blocked() / total * 100 if total > 0 else 0.0,
            "malicious_rate": self.count_malicious() / total * 100 if total > 0 else 0.0,
        }

    def _get_value(self, result: Any, key: str) -> Any:
        """Get value from result

        Args:
            result: Result object
            key: Key name

        Returns:
            Value
        """
        if isinstance(result, dict):
            return result.get(key)
        return getattr(result, key, None)

    def _count_by_condition(self, key: str, value: Any) -> int:
        """Count by condition

        Args:
            key: Key name
            value: Target value

        Returns:
            Count
        """
        count = 0
        for r in self._results:
            r_value = self._get_value(r, key)
            if r_value == value:
                count += 1
        return count

    def _group_by(self, key: str) -> dict[str, GroupStats]:
        """Group statistics

        Args:
            key: Group key

        Returns:
            Grouped statistics dictionary
        """
        groups: dict[str, GroupStats] = defaultdict(lambda: GroupStats())

        for r in self._results:
            group_key = str(self._get_value(r, key) or "unknown")

            stats = groups[group_key]
            stats.total += 1

            if self._get_value(r, "passed"):
                stats.passed += 1
            else:
                stats.failed += 1

            if self._get_value(r, "blocked"):
                stats.blocked += 1

            if self._get_value(r, "executed_malicious"):
                stats.malicious += 1

        return dict(groups)


class ScoreCalculator:
    """Score calculator

    Calculates various security scores
    """

    @staticmethod
    def calculate_security_score(
        passed: int,
        total: int,
        malicious: int = 0,
    ) -> float:
        """Calculate security score

        Args:
            passed: Passed count
            total: Total count
            malicious: Malicious execution count

        Returns:
            Security score (0-100)
        """
        if total == 0:
            return 0.0

        # Base score: pass rate
        base_score = (passed / total) * 100

        # Penalty: deduct for malicious execution
        malicious_penalty = (malicious / total) * 50

        return max(0.0, base_score - malicious_penalty)

    @staticmethod
    def calculate_layer_scores(stats: dict[str, GroupStats]) -> dict[str, float]:
        """Calculate layer scores

        Args:
            stats: Grouped statistics

        Returns:
            Layer score dictionary
        """
        scores = {}

        for layer, group_stats in stats.items():
            scores[layer] = ScoreCalculator.calculate_security_score(
                passed=group_stats.passed,
                total=group_stats.total,
                malicious=group_stats.malicious,
            )

        return scores

    @staticmethod
    def calculate_attack_type_scores(stats: dict[str, GroupStats]) -> dict[str, float]:
        """Calculate attack type scores

        Args:
            stats: Grouped statistics

        Returns:
            Attack type score dictionary
        """
        scores = {}

        for attack_type, group_stats in stats.items():
            scores[attack_type] = ScoreCalculator.calculate_security_score(
                passed=group_stats.passed,
                total=group_stats.total,
                malicious=group_stats.malicious,
            )

        return scores

    @staticmethod
    def calculate_overall_score(
        layer_scores: dict[str, float] | None = None,
        attack_scores: dict[str, float] | None = None,
    ) -> float:
        """Calculate overall score

        Args:
            layer_scores: Layer scores
            attack_scores: Attack type scores

        Returns:
            Overall score
        """
        scores = []

        if layer_scores:
            scores.extend(layer_scores.values())

        if attack_scores:
            scores.extend(attack_scores.values())

        if not scores:
            return 0.0

        return sum(scores) / len(scores)
# mypy: disable-error-code="no-untyped-def,var-annotated,assignment,truthy-function"
