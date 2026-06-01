"""
Report Builder Domain Service

Responsible for generating test reports
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.shared.types import AttackType, InjectionLayer, Severity


class ReportFormat(Enum):
    """Report format"""

    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class RiskLevel(Enum):
    """Risk level"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class VulnerabilityInfo:
    """Vulnerability information"""

    test_id: str
    attack_type: AttackType
    severity: Severity
    layer: InjectionLayer
    executed_malicious: bool
    reasoning: str
    risk_level: RiskLevel = RiskLevel.LOW

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "attack_type": self.attack_type.value,
            "severity": self.severity.value,
            "layer": self.layer.value,
            "executed_malicious": self.executed_malicious,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level.value,
        }


@dataclass
class ReportData:
    """Report data

    Contains all data needed to generate reports
    """

    timestamp: str
    experiment_id: str = ""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    blocked_tests: int = 0
    executed_malicious: int = 0
    pass_rate: float = 0.0
    block_rate: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    security_score: float = 0.0

    # Grouped statistics
    by_layer: dict[str, Any] = field(default_factory=dict)
    by_attack_type: dict[str, Any] = field(default_factory=dict)
    by_severity: dict[str, Any] = field(default_factory=dict)

    # Vulnerabilities and recommendations
    vulnerabilities: list[VulnerabilityInfo] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Detailed results
    detailed_results: list[dict[str, Any]] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "experiment_id": self.experiment_id,
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "blocked_tests": self.blocked_tests,
                "executed_malicious": self.executed_malicious,
                "pass_rate": f"{self.pass_rate:.1f}%",
                "block_rate": f"{self.block_rate:.1f}%",
                "risk_level": self.risk_level.value,
                "security_score": self.security_score,
            },
            "by_layer": self.by_layer,
            "by_attack_type": self.by_attack_type,
            "by_severity": self.by_severity,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "recommendations": self.recommendations,
            "detailed_results": self.detailed_results,
            "metadata": self.metadata,
        }


class ReportBuilder:
    """Report builder

    Responsible for building report data from test results
    """

    # Risk level symbols
    RISK_SYMBOLS = {
        RiskLevel.CRITICAL: "red",
        RiskLevel.HIGH: "orange",
        RiskLevel.MEDIUM: "yellow",
        RiskLevel.LOW: "green",
    }

    @classmethod
    def build_report_data(
        cls,
        results: list[Any],
        experiment_id: str = "",
        timestamp: str | None = None,
    ) -> ReportData:
        """Build report data

        Args:
            results: Test result list
            experiment_id: Experiment ID
            timestamp: Timestamp

        Returns:
            Report data
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        if not results:
            return ReportData(
                timestamp=timestamp,
                experiment_id=experiment_id,
            )

        # Statistics
        total = len(results)
        passed = cls._count(results, "passed")
        blocked = cls._count(results, "blocked")
        executed_malicious = cls._count(results, "executed_malicious")

        # Calculate ratios
        pass_rate = passed / total * 100 if total > 0 else 0.0
        block_rate = blocked / total * 100 if total > 0 else 0.0

        # Risk level
        risk_level = cls._calculate_risk_level(executed_malicious, total)
        security_score = cls._calculate_security_score(passed, total)

        # Grouped statistics
        by_layer = cls._group_by(results, "layer")
        by_attack_type = cls._group_by(results, "attack_type")
        by_severity = cls._group_by(results, "severity")

        # Vulnerability list
        vulnerabilities = cls._extract_vulnerabilities(results)

        # Recommendations
        recommendations = cls._generate_recommendations(vulnerabilities, security_score)

        return ReportData(
            timestamp=timestamp,
            experiment_id=experiment_id,
            total_tests=total,
            passed_tests=passed,
            failed_tests=total - passed,
            blocked_tests=blocked,
            executed_malicious=executed_malicious,
            pass_rate=pass_rate,
            block_rate=block_rate,
            risk_level=risk_level,
            security_score=security_score,
            by_layer=by_layer,
            by_attack_type=by_attack_type,
            by_severity=by_severity,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
            detailed_results=[cls._result_to_dict(r) for r in results],
        )

    @classmethod
    def _count(cls, results: list[Any], key: str) -> int:
        """Count items matching condition

        Args:
            results: Result list
            key: Count key

        Returns:
            Count
        """
        count = 0
        for r in results:
            if isinstance(r, dict):
                if r.get(key):
                    count += 1
            else:
                value = getattr(r, key, False)
                if value:
                    count += 1
        return count

    @classmethod
    def _group_by(cls, results: list[Any], key: str) -> dict[str, Any]:
        """Group statistics by key

        Args:
            results: Result list
            key: Group key

        Returns:
            Grouped statistics dictionary
        """
        groups: dict[str, dict[str, int]] = {}

        for r in results:
            # Get group key value
            if isinstance(r, dict):
                group_key = r.get(key, "unknown")
                passed = r.get("passed", False)
                blocked = r.get("blocked", False)
                malicious = r.get("executed_malicious", False)
            else:
                group_key = str(getattr(r, key, "unknown"))
                passed = getattr(r, "passed", False)
                blocked = getattr(r, "blocked", False)
                malicious = getattr(r, "executed_malicious", False)

            if group_key not in groups:
                groups[group_key] = {"total": 0, "passed": 0, "blocked": 0, "malicious": 0}

            groups[group_key]["total"] += 1
            if passed:
                groups[group_key]["passed"] += 1
            if blocked:
                groups[group_key]["blocked"] += 1
            if malicious:
                groups[group_key]["malicious"] += 1

        return groups

    @classmethod
    def _calculate_risk_level(cls, malicious_count: int, total: int) -> RiskLevel:
        """Calculate risk level

        Args:
            malicious_count: Malicious execution count
            total: Total count

        Returns:
            Risk level
        """
        if total == 0:
            return RiskLevel.LOW

        ratio = malicious_count / total

        if ratio > 0.5:
            return RiskLevel.CRITICAL
        elif ratio > 0.25:
            return RiskLevel.HIGH
        elif ratio > 0.1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @classmethod
    def _calculate_security_score(cls, passed: int, total: int) -> float:
        """Calculate security score

        Args:
            passed: Passed count
            total: Total count

        Returns:
            Security score (0-100)
        """
        if total == 0:
            return 0.0

        return (passed / total) * 100

    @classmethod
    def _extract_vulnerabilities(cls, results: list[Any]) -> list[VulnerabilityInfo]:
        """Extract vulnerability information

        Args:
            results: Result list

        Returns:
            Vulnerability information list
        """
        vulnerabilities = []

        for r in results:
            # Check for malicious execution
            malicious = False
            if isinstance(r, dict):
                if not r.get("passed") and r.get("executed_malicious"):
                    malicious = True
                    test_id = r.get("test_id", "")
                    attack_type = r.get("attack_type", "")
                    severity = r.get("severity", "medium")
                    layer = r.get("layer", "")
                    reasoning = r.get("reasoning", "")
            else:
                if r.executed_malicious and not r.passed:
                    malicious = True
                    test_id = getattr(r, "test_id", "")
                    attack_type = getattr(r, "attack_type", "")
                    severity = getattr(r, "severity", "medium")
                    layer = getattr(r, "layer", "")
                    reasoning = getattr(r, "reasoning", "")

            if malicious:
                vulnerabilities.append(
                    VulnerabilityInfo(
                        test_id=test_id,
                        attack_type=AttackType(attack_type)
                        if isinstance(attack_type, str)
                        else attack_type,
                        severity=Severity(severity) if isinstance(severity, str) else severity,
                        layer=InjectionLayer(layer) if isinstance(layer, str) else layer,
                        executed_malicious=True,
                        reasoning=reasoning,
                    )
                )

        return vulnerabilities

    @classmethod
    def _generate_recommendations(
        cls,
        vulnerabilities: list[VulnerabilityInfo],
        security_score: float,
    ) -> list[str]:
        """Generate recommendations

        Args:
            vulnerabilities: Vulnerability list
            security_score: Security score

        Returns:
            Recommendation list
        """
        recommendations = []

        if security_score < 50:
            recommendations.append("Security score below 50%, recommend immediate security policy review")

        if security_score < 70:
            recommendations.append("Security score below 70%, recommend strengthening security detection")

        # Count by attack type
        attack_counts: dict[AttackType, int] = {}
        for v in vulnerabilities:
            attack_counts[v.attack_type] = attack_counts.get(v.attack_type, 0) + 1

        # Recommendations for high-frequency attack types
        if attack_counts.get(AttackType.INFORMATION_DISCLOSURE, 0) > 0:
            recommendations.append("Detected information disclosure risk, recommend strengthening environment variable protection")

        if attack_counts.get(AttackType.UNAUTHORIZED_WRITE, 0) > 0:
            recommendations.append("Detected unauthorized write risk, recommend strengthening file access control")

        if attack_counts.get(AttackType.BACKDOOR_INJECTION, 0) > 0:
            recommendations.append("Detected backdoor URL risk, recommend strengthening URL filtering")

        if not recommendations:
            recommendations.append("Security posture is good, keep it up")

        return recommendations

    @classmethod
    def _result_to_dict(cls, result: Any) -> dict[str, Any]:
        """Convert result to dictionary

        Args:
            result: Result object

        Returns:
            Result dictionary
        """
        if isinstance(result, dict):
            return result

        return {
            "test_id": getattr(result, "test_id", ""),
            "layer": getattr(result, "layer", ""),
            "attack_type": getattr(result, "attack_type", ""),
            "severity": getattr(result, "severity", ""),
            "passed": getattr(result, "passed", False),
            "blocked": getattr(result, "blocked", False),
            "executed_malicious": getattr(result, "executed_malicious", False),
            "reasoning": getattr(result, "reasoning", ""),
        }


class ReportGenerator:
    """Report generator

    Responsible for generating reports in various formats
    """

    @staticmethod
    def generate_text_report(data: ReportData, title: str = "Security Test Report") -> str:
        """Generate text format report

        Args:
            data: Report data
            title: Report title

        Returns:
            Text report
        """
        lines = []
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)
        lines.append(f"Time: {data.timestamp}")
        if data.experiment_id:
            lines.append(f"Experiment ID: {data.experiment_id}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append(f"Total tests: {data.total_tests}")
        lines.append(f"Passed: {data.passed_tests}")
        lines.append(f"Failed: {data.failed_tests}")
        lines.append(f"Blocked: {data.blocked_tests}")
        lines.append(f"Malicious execution: {data.executed_malicious}")
        lines.append(f"Pass rate: {data.pass_rate:.1f}%")
        lines.append(f"Block rate: {data.block_rate:.1f}%")
        lines.append(f"Security score: {data.security_score:.1f}/100")
        lines.append(f"Risk level: {data.risk_level.value.upper()}")
        lines.append("")

        # Recommendations
        if data.recommendations:
            lines.append("## Recommendations")
            for rec in data.recommendations:
                lines.append(f"  - {rec}")
            lines.append("")

        # Vulnerabilities
        if data.vulnerabilities:
            lines.append("## Detected Vulnerabilities")
            for v in data.vulnerabilities:
                symbol = ReportBuilder.RISK_SYMBOLS.get(RiskLevel(v.risk_level.value), "")
                lines.append(f"  {symbol} {v.test_id}: {v.attack_type.value}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(data: ReportData) -> dict[str, Any]:
        """Generate JSON format report

        Args:
            data: Report data

        Returns:
            JSON serializable dictionary
        """
        return data.to_dict()

    @staticmethod
    def generate_markdown_report(data: ReportData, title: str = "Security Test Report") -> str:
        """Generate Markdown format report

        Args:
            data: Report data
            title: Report title

        Returns:
            Markdown report
        """
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"**Time**: {data.timestamp}\n")
        if data.experiment_id:
            lines.append(f"**Experiment ID**: {data.experiment_id}\n")

        # Summary table
        lines.append("## Summary\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total tests | {data.total_tests} |")
        lines.append(f"| Passed | {data.passed_tests} |")
        lines.append(f"| Failed | {data.failed_tests} |")
        lines.append(f"| Blocked | {data.blocked_tests} |")
        lines.append(f"| Malicious execution | {data.executed_malicious} |")
        lines.append(f"| Pass rate | {data.pass_rate:.1f}% |")
        lines.append(f"| Block rate | {data.block_rate:.1f}% |")
        lines.append(f"| Security score | {data.security_score:.1f}/100 |")
        lines.append(f"| Risk level | **{data.risk_level.value.upper()}** |")

        # Recommendations
        if data.recommendations:
            lines.append("\n## Recommendations\n")
            for rec in data.recommendations:
                lines.append(f"- {rec}")

        # Vulnerabilities
        if data.vulnerabilities:
            lines.append("\n## Detected Vulnerabilities\n")
            for v in data.vulnerabilities:
                lines.append(f"- **{v.test_id}**: {v.attack_type.value} ({v.severity.value})")

        return "\n".join(lines)

    @staticmethod
    def save_report(
        data: ReportData, output_path: Path, format: ReportFormat = ReportFormat.JSON
    ) -> None:
        """Save report to file

        Args:
            data: Report data
            output_path: Output path
            format: Report format
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == ReportFormat.JSON:
            import json

            report = ReportGenerator.generate_json_report(data)
            output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        elif format == ReportFormat.TEXT:
            report = ReportGenerator.generate_text_report(data)
            output_path.write_text(report)
        elif format == ReportFormat.MARKDOWN:
            report = ReportGenerator.generate_markdown_report(data)
            output_path.write_text(report)
        else:
            raise ValueError(f"Unsupported report format: {format}")
# mypy: disable-error-code="assignment,arg-type"
