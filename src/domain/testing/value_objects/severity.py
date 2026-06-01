"""
Severity Value Object

Extends severity definition, adding comparison and description functionality.
"""

from enum import Enum

from src.shared.types import Severity


class SeverityLevel(Enum):
    """Severity level (with ordering)"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_severity(cls, severity: Severity) -> "SeverityLevel":
        """Convert from Severity"""
        mapping = {
            Severity.LOW: cls.LOW,
            Severity.MEDIUM: cls.MEDIUM,
            Severity.HIGH: cls.HIGH,
            Severity.CRITICAL: cls.CRITICAL,
        }
        return mapping.get(severity, cls.LOW)

    def __lt__(self, other: "SeverityLevel") -> bool:
        return self.value < other.value

    def __le__(self, other: "SeverityLevel") -> bool:
        return self.value <= other.value

    def __gt__(self, other: "SeverityLevel") -> bool:
        return self.value > other.value

    def __ge__(self, other: "SeverityLevel") -> bool:
        return self.value >= other.value

    def is_high_or_critical(self) -> bool:
        """Check if high or critical severity"""
        return self in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)

    def get_description(self) -> str:
        """Get severity description"""
        descriptions = {
            SeverityLevel.LOW: "Low - Minor security risk",
            SeverityLevel.MEDIUM: "Medium - Moderate security risk, needs attention",
            SeverityLevel.HIGH: "High - Severe security risk, should be handled immediately",
            SeverityLevel.CRITICAL: "Critical - Extremely severe security risk, must be handled immediately",
        }
        return descriptions.get(self, "Unknown")

    def get_color_code(self) -> str:
        """Get terminal color code"""
        colors = {
            SeverityLevel.LOW: "\033[92m",  # Green
            SeverityLevel.MEDIUM: "\033[93m",  # Yellow
            SeverityLevel.HIGH: "\033[91m",  # Red
            SeverityLevel.CRITICAL: "\033[95m",  # Purple
        }
        return colors.get(self, "")

    def get_reset_code(self) -> str:
        """Get color reset code"""
        return "\033[0m"
