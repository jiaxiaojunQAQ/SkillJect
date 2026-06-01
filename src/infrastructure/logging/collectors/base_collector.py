"""
Log collection infrastructure

Provides unified log collection interfaces and implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Log entry.

    Represents a single log record.
    """

    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class LogCollection:
    """Log collection result.

    Represents the complete result of a log collection operation.
    """

    entries: list[LogEntry] = field(default_factory=list)
    raw_stdout: list[str] = field(default_factory=list)
    raw_stderr: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_entry(self, entry: LogEntry) -> None:
        """Add a log entry.

        Args:
            entry: Log entry to add
        """
        self.entries.append(entry)

    def filter_by_level(self, level: LogLevel) -> list[LogEntry]:
        """Filter entries by log level.

        Args:
            level: Log level to filter by

        Returns:
            List of filtered log entries
        """
        return [e for e in self.entries if e.level == level]

    def filter_by_source(self, source: str) -> list[LogEntry]:
        """Filter entries by source.

        Args:
            source: Log source to filter by

        Returns:
            List of filtered log entries
        """
        return [e for e in self.entries if e.source == source]

    def has_errors(self) -> bool:
        """Check if there are any error log entries."""
        return any(e.level in (LogLevel.ERROR, LogLevel.CRITICAL) for e in self.entries)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "raw_stdout": self.raw_stdout,
            "raw_stderr": self.raw_stderr,
            "metadata": self.metadata,
        }


class LogCollector(ABC):
    """Abstract interface for log collectors.

    Defines the interface that all log collectors must implement.
    """

    @staticmethod
    def extract_logs_from_execution(execution: Any) -> dict[str, list[str]]:
        """Extract logs from OpenSandbox Execution object.

        This is a shared utility method for all collectors that process
        OpenSandbox Execution objects (not dict-based execution results).

        Args:
            execution: OpenSandbox Execution object with logs attribute

        Returns:
            Dictionary with "stdout" and "stderr" lists of log text
        """
        logs = {"stdout": [], "stderr": []}

        # Extract stdout
        if hasattr(execution, "logs") and hasattr(execution.logs, "stdout"):
            for msg in execution.logs.stdout:
                if hasattr(msg, "text"):
                    logs["stdout"].append(msg.text)

        # Extract stderr
        if hasattr(execution, "logs") and hasattr(execution.logs, "stderr"):
            for msg in execution.logs.stderr:
                if hasattr(msg, "text"):
                    logs["stderr"].append(msg.text)

        return logs

    @abstractmethod
    def collect(self, execution_result: dict[str, Any]) -> LogCollection:
        """Collect logs.

        Args:
            execution_result: Execution result

        Returns:
            Log collection result
        """
        pass

    @abstractmethod
    def parse(self, raw_output: str) -> list[LogEntry]:
        """Parse raw output.

        Args:
            raw_output: Raw output string

        Returns:
            List of parsed log entries
        """
        pass

    def desensitize(self, content: str, show_chars: int = 4) -> str:
        """Desensitize sensitive content.

        Args:
            content: Original content
            show_chars: Number of characters to show at start and end

        Returns:
            Desensitized content
        """
        # Import ResponseAnalyzer from domain.analysis.services
        from ...domain.analysis.services.response_analyzer import ResponseAnalyzer

        return ResponseAnalyzer().desensitize(content, show_chars)


class StdoutCollector(LogCollector):
    """Standard output collector.

    Collects logs from stdout/stderr.
    """

    def collect(self, execution_result: dict[str, Any]) -> LogCollection:
        """Collect logs."""
        collection = LogCollection()

        # Collect stdout
        stdout = execution_result.get("stdout", [])
        if isinstance(stdout, list):
            collection.raw_stdout = [str(line) for line in stdout]
        else:
            collection.raw_stdout = [str(stdout)]

        # Collect stderr
        stderr = execution_result.get("stderr", [])
        if isinstance(stderr, list):
            collection.raw_stderr = [str(line) for line in stderr]
        else:
            collection.raw_stderr = [str(stderr)]

        # Parse logs
        combined = "\n".join(collection.raw_stdout + collection.raw_stderr)
        collection.entries = self.parse(combined)

        return collection

    def parse(self, raw_output: str) -> list[LogEntry]:
        """Parse raw output."""
        entries = []

        for line in raw_output.split("\n"):
            if not line.strip():
                continue

            # Simple parsing: treat each line as a log entry
            level = self._detect_log_level(line)
            entries.append(
                LogEntry(
                    timestamp=datetime.now(),
                    level=level,
                    source="stdout",
                    message=line,
                )
            )

        return entries

    def _detect_log_level(self, line: str) -> LogLevel:
        """Detect log level from line content."""
        line_lower = line.lower()

        if "critical" in line_lower or "fatal" in line_lower:
            return LogLevel.CRITICAL
        elif "error" in line_lower:
            return LogLevel.ERROR
        elif "warning" in line_lower or "warn" in line_lower:
            return LogLevel.WARNING
        elif "info" in line_lower:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG


class OtelCollector(LogCollector):
    """OpenTelemetry log collector.

    Specialized for parsing Claude Code's OpenTelemetry logs.
    """

    def collect(self, execution_result: dict[str, Any]) -> LogCollection:
        """Collect logs."""
        collection = LogCollection()

        # Collect raw output
        stdout = execution_result.get("stdout", [])
        if isinstance(stdout, list):
            collection.raw_stdout = [str(line) for line in stdout]
        else:
            collection.raw_stdout = [str(stdout)]

        # Parse OTEL logs
        combined = "\n".join(collection.raw_stdout)
        collection.entries = self.parse(combined)

        return collection

    def parse(self, raw_output: str) -> list[LogEntry]:
        """Parse OpenTelemetry logs."""
        entries = []

        # OTEL log format parsing
        for line in raw_output.split("\n"):
            if not line.strip():
                continue

            # Check if this is an OTEL log
            if self._is_otel_log(line):
                entry = self._parse_otel_log(line)
                if entry:
                    entries.append(entry)
            else:
                # Regular log
                entries.append(
                    LogEntry(
                        timestamp=datetime.now(),
                        level=LogLevel.INFO,
                        source="otel",
                        message=line,
                    )
                )

        return entries

    def _is_otel_log(self, line: str) -> bool:
        """Check if line is an OTEL log."""
        # OTEL logs typically contain specific fields
        otel_indicators = ["span_id", "trace_id", "severity_text"]
        return any(indicator in line for indicator in otel_indicators)

    def _parse_otel_log(self, line: str) -> LogEntry | None:
        """Parse OTEL log line."""
        import json

        try:
            data = json.loads(line)

            return LogEntry(
                timestamp=datetime.now(),
                level=self._otel_level_to_log_level(data.get("severity_text", "info")),
                source="otel",
                message=data.get("body", data.get("message", "")),
                metadata=data,
            )
        except json.JSONDecodeError:
            return None

    def _otel_level_to_log_level(self, otel_level: str) -> LogLevel:
        """Convert OTEL log level to LogLevel."""
        mapping = {
            "trace": LogLevel.DEBUG,
            "debug": LogLevel.DEBUG,
            "info": LogLevel.INFO,
            "warn": LogLevel.WARNING,
            "error": LogLevel.ERROR,
            "fatal": LogLevel.CRITICAL,
        }
        return mapping.get(otel_level.lower(), LogLevel.INFO)
# mypy: disable-error-code="import-untyped,no-any-return,var-annotated"
