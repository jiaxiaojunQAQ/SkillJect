"""
JSON Log Collector

Specialized log collector for parsing JSON-formatted logs from CLI agents.
Designed for OpenClaw agent which outputs structured JSON when --json flag is used.

JSON log format example from OpenClaw:
{"level":"info","timestamp":"2026-03-30T12:00:00Z","message":"Processing request"}
{"level":"error","timestamp":"2026-03-30T12:00:01Z","message":"Request failed","error":"timeout"}

This collector:
1. Parses line-delimited JSON (LDJSON) output
2. Extracts structured log entries
3. Handles mixed JSON and plain text output
4. Provides formatted output for analysis
"""

import json
from datetime import datetime
from typing import Any

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.infrastructure.logging.collectors.base_collector import (
    LogCollection,
    LogCollector,
    LogEntry,
    LogLevel,
)


class JsonLogCollector(LogCollector):
    """
    JSON log collector for parsing JSON-formatted logs.

    Designed for OpenClaw and other CLI agents that output JSON logs.
    Supports line-delimited JSON (LDJSON) format where each line is a valid JSON object.
    """

    # JSON keywords that indicate structured JSON logging
    JSON_KEYWORDS = ["level", "timestamp", "message", "error"]

    def __init__(self, config: BaseAgentConfig, strict_parsing: bool = False):
        """
        Initialize JSON log collector.

        Args:
            config: Agent configuration object
            strict_parsing: If True, only parse valid JSON lines; if False, fall back to text parsing
        """
        self.config = config
        # Handle configs that may not have a 'name' attribute (e.g., testing AgentConfig)
        self.agent_name = getattr(config, "name", "unknown-agent")
        self._strict_parsing = strict_parsing
        self._parse_errors: list[str] = []

    async def collect_from_execution(
        self,
        execution: Any,
        agent: Any = None,
    ) -> dict[str, Any]:
        """
        Collect JSON logs from OpenSandbox Execution object.

        This is an async method specifically for processing OpenSandbox Execution
        objects. For the standard LogCollector interface, use collect().

        Args:
            execution: Agent execution result (OpenSandbox Execution object)
            agent: Agent instance (optional, for context)

        Returns:
            Structured log dictionary with keys:
            - raw_stdout: List of raw stdout lines
            - raw_stderr: List of raw stderr lines
            - events: List of parsed log events
            - formatted_output: Formatted log string for analysis
            - metadata: Log metadata including timestamps, agent name, etc.
        """
        # Clear previous parse errors to prevent unbounded growth
        self._parse_errors.clear()

        # Capture timestamp once for consistency
        collection_timestamp = datetime.now()

        # Extract logs from execution (using base class shared method)
        logs = LogCollector.extract_logs_from_execution(execution)
        raw_stdout = logs.get("stdout", [])
        raw_stderr = logs.get("stderr", [])

        # Merge stdout and stderr for JSON parsing
        raw_output = "\n".join(raw_stdout + raw_stderr)

        # Parse JSON logs
        events = self._parse_json_logs(raw_output)

        # Build formatted output
        formatted_output = self._format_for_analysis(raw_stdout, raw_stderr, events, collection_timestamp)

        # Count event types in single pass
        json_count = sum(1 for e in events if e.get("type") == "json_log")
        text_count = len(events) - json_count

        # Build metadata
        metadata = {
            "agent_name": self.agent_name,
            "collector_type": "json",
            "timestamp": collection_timestamp.isoformat(),
            "parse_errors": len(self._parse_errors),
            "json_entries": json_count,
            "text_entries": text_count,
        }

        return {
            "raw_stdout": raw_stdout,
            "raw_stderr": raw_stderr,
            "events": events,
            "formatted_output": formatted_output,
            "metadata": metadata,
        }

    def collect(self, execution_result: dict[str, Any]) -> LogCollection:
        """
        Collect logs from execution result (synchronous interface for LogCollector).

        Args:
            execution_result: Execution result dictionary with stdout/stderr

        Returns:
            LogCollection object
        """
        # Clear previous parse errors to prevent unbounded growth
        self._parse_errors.clear()

        collection = LogCollection()

        # Collect stdout and stderr
        stdout = execution_result.get("stdout", [])
        if isinstance(stdout, list):
            collection.raw_stdout = [str(line) for line in stdout]
        else:
            collection.raw_stdout = [str(stdout)]

        stderr = execution_result.get("stderr", [])
        if isinstance(stderr, list):
            collection.raw_stderr = [str(line) for line in stderr]
        else:
            collection.raw_stderr = [str(stderr)]

        # Parse logs
        combined = "\n".join(collection.raw_stdout + collection.raw_stderr)
        collection.entries = self.parse(combined)

        # Add metadata
        collection.metadata = {
            "agent_name": self.agent_name,
            "collector_type": "json",
            "parse_errors": len(self._parse_errors),
        }

        return collection

    def parse(self, raw_output: str) -> list[LogEntry]:
        """
        Parse raw output and extract log entries.

        Args:
            raw_output: Raw output string

        Returns:
            List of parsed log entries
        """
        entries = []

        for line in raw_output.split("\n"):
            if not line.strip():
                continue

            # Try to parse as JSON
            json_entry = self._try_parse_json(line)
            if json_entry:
                entries.append(json_entry)
            elif not self._strict_parsing:
                # Fall back to text log
                entries.append(
                    LogEntry(
                        timestamp=datetime.now(),
                        level=self._detect_log_level(line),
                        source="json_collector",
                        message=line,
                    )
                )

        return entries

    def _try_parse_json(self, line: str) -> LogEntry | None:
        """
        Try to parse a line as JSON.

        Args:
            line: Line to parse

        Returns:
            LogEntry if successful, None otherwise
        """
        try:
            data = json.loads(line)

            if not isinstance(data, dict):
                return None

            # Extract common JSON log fields
            level_str = data.get("level", data.get("severity", "info"))
            level = self._str_to_log_level(level_str)

            # Parse timestamp if available
            timestamp = datetime.now()
            if "timestamp" in data or "time" in data:
                timestamp_str = data.get("timestamp", data.get("time", ""))
                timestamp = self._parse_timestamp(timestamp_str)

            return LogEntry(
                timestamp=timestamp,
                level=level,
                source="json",
                message=data.get("message", ""),
                metadata=data,
            )
        except (json.JSONDecodeError, ValueError):
            self._parse_errors.append(f"Failed to parse JSON: {line[:100]}")
            return None

    def _str_to_log_level(self, level_str: str) -> LogLevel:
        """
        Convert string to LogLevel.

        Args:
            level_str: Log level string

        Returns:
            LogLevel enum value
        """
        level_mapping = {
            "trace": LogLevel.DEBUG,
            "debug": LogLevel.DEBUG,
            "info": LogLevel.INFO,
            "information": LogLevel.INFO,
            "warn": LogLevel.WARNING,
            "warning": LogLevel.WARNING,
            "error": LogLevel.ERROR,
            "err": LogLevel.ERROR,
            "fatal": LogLevel.CRITICAL,
            "critical": LogLevel.CRITICAL,
            "severe": LogLevel.CRITICAL,
        }
        return level_mapping.get(level_str.lower(), LogLevel.INFO)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            datetime object
        """
        if not timestamp_str:
            return datetime.now()

        try:
            # Try ISO format
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now()

    def _detect_log_level(self, line: str) -> LogLevel:
        """
        Detect log level from plain text line.

        Args:
            line: Line to analyze

        Returns:
            Detected log level
        """
        line_lower = line.lower()

        if any(kw in line_lower for kw in ["critical", "fatal", "severe"]):
            return LogLevel.CRITICAL
        elif any(kw in line_lower for kw in ["error", "failed", "failure"]):
            return LogLevel.ERROR
        elif any(kw in line_lower for kw in ["warning", "warn"]):
            return LogLevel.WARNING
        elif "info" in line_lower:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG

    def _parse_json_logs(self, raw_output: str) -> list[dict[str, Any]]:
        """
        Parse JSON logs from raw output.

        Args:
            raw_output: Raw output string

        Returns:
            List of parsed log event dictionaries
        """
        events = []

        for line in raw_output.split("\n"):
            if not line.strip():
                continue

            # Try to parse as JSON
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    events.append({
                        "type": "json_log",
                        "level": data.get("level", data.get("severity", "info")),
                        "message": data.get("message", ""),
                        "data": data,
                    })
            except json.JSONDecodeError:
                # Not JSON, treat as text log
                if not self._strict_parsing:
                    events.append({
                        "type": "text_log",
                        "level": "info",
                        "message": line,
                    })

        return events

    def _format_for_analysis(
        self,
        stdout: list[str],
        stderr: list[str],
        events: list[dict[str, Any]],
        timestamp: datetime | None = None,
    ) -> str:
        """
        Format logs for analysis.

        Args:
            stdout: Raw stdout lines
            stderr: Raw stderr lines
            events: Parsed events
            timestamp: Collection timestamp (uses current time if not provided)

        Returns:
            Formatted log string
        """
        lines = []

        # Add header
        lines.append(f"=== {self.agent_name} JSON Log ===")
        lines.append(f"Timestamp: {(timestamp or datetime.now()).isoformat()}")

        # Add agent response (filter out JSON metadata)
        response_lines = []
        for line in stdout:
            if line.strip() and not self._is_json_metadata(line):
                response_lines.append(line)

        if response_lines:
            lines.append("\nAgent Response:")
            lines.extend(response_lines)

        # Add stderr if any
        if stderr:
            lines.append("\nErrors:")
            lines.extend(stderr)

        # Add event statistics
        if events:
            lines.append("\nEvents:")
            # Count in single pass (assume only json_log and text_log types exist)
            json_count = sum(1 for e in events if e.get("type") == "json_log")
            text_count = len(events) - json_count
            lines.append(f"  JSON entries: {json_count}")
            lines.append(f"  Text entries: {text_count}")

        return "\n".join(lines)

    def _is_json_metadata(self, line: str) -> bool:
        """
        Check if line is JSON metadata (for filtering).

        Args:
            line: Line to check

        Returns:
            True if line appears to be JSON metadata
        """
        line_stripped = line.strip()
        if not line_stripped.startswith("{"):
            return False

        # Check if line contains JSON log keywords
        return any(keyword in line.lower() for keyword in self.JSON_KEYWORDS)

    def get_errors(self) -> list[str]:
        """
        Get list of parse errors.

        Returns:
            List of error messages
        """
        return self._parse_errors

    def clear_errors(self) -> None:
        """Clear parse errors."""
        self._parse_errors.clear()

    def __repr__(self) -> str:
        """Return string representation of the collector."""
        return f"JsonLogCollector(agent_name='{self.agent_name}', strict_parsing={self._strict_parsing})"
# mypy: disable-error-code="arg-type"
