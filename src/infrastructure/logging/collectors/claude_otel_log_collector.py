"""
Claude Code OTel Log Collector

Independent Claude Code log collector, does not depend on removed modules.

Responsibilities:
- collect(): Collect logs from execution results
- format_for_analysis(): Format logs for subsequent analysis
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.domain.logging.entities.tool_call_event import (
    ToolCallEvent as DomainToolCallEvent,
)
from src.domain.logging.entities.tool_call_event import (
    ToolCallTrace,
)
from src.infrastructure.logging.builders.tool_call_trace_builder import ToolCallTraceBuilder
from src.infrastructure.logging.collectors.base_collector import LogCollector
from src.infrastructure.logging.parsers.claude_console_log_parser import (
    ApiRequestEvent,
    ClaudeConsoleLogParser,
    ToolCallEvent,
)
from src.infrastructure.logging.parsers.otel_span_parser import OtelSpanParser


class ClaudeOtelLogCollector:
    """
    Claude Code specific OTel log collector.

    Claude Code uses OpenTelemetry for logging.
    This collector parses OTel logs and extracts key events.

    Note: This class does not inherit from LogCollector because it uses
    async methods and a different interface signature.
    """

    # OTel keywords
    OTEL_KEYWORDS = [
        "otel",
        "telemetry",
        "trace",
        "span",
        "metric",
        "logrecord",
        "timestamp",
        "instrumentation",
        "claude_code",
        "anthropic",
    ]

    # OTel metadata patterns (for filtering)
    OTEL_PATTERNS = [
        r"^\d{4}-\d{2}-\d{2}",  # Timestamp format
        r"^\[(INFO|DEBUG|WARN|ERROR|TRACE)\]",  # Log level
    ]

    def __init__(self, config: BaseAgentConfig, strict_parsing: bool = False):
        """
        Initialize OTel log collector.

        Args:
            config: Agent configuration object
            strict_parsing: Whether to use strict mode for OTel span parsing
        """
        self.config = config
        self.agent_name = config.name
        self._span_parser = OtelSpanParser(strict=strict_parsing)
        self._console_parser = ClaudeConsoleLogParser()
        self._trace_builder = ToolCallTraceBuilder()
        self._tool_call_trace: Any | None = None  # ToolCallTrace
        self._tool_call_events: list[ToolCallEvent] = []
        self._api_request_events: list[ApiRequestEvent] = []

    async def collect(
        self,
        execution: Any,
        agent: Any,
    ) -> dict[str, Any]:
        """
        Collect Claude Code OTel logs.

        Args:
            execution: Agent execution result
            agent: Agent instance (kept for context)

        Returns:
            Structured log dictionary
        """
        # Extract logs using base class shared method
        logs = LogCollector.extract_logs_from_execution(execution)
        raw_stdout = "\n".join(logs.get("stdout", []))
        raw_stderr = "\n".join(logs.get("stderr", []))

        # Merge stdout and stderr for OTel parsing (OTel logs may be in either stream)
        raw_output = f"{raw_stdout}\n{raw_stderr}"

        # Prioritize Console format parser (handles OTEL_LOGS_EXPORTER=console output)
        console_result = self._console_parser.parse(raw_output)
        self._tool_call_events = console_result.get("tool_calls", [])
        self._api_request_events = console_result.get("api_requests", [])

        # Build tool call trace
        self._tool_call_trace = None
        if self._tool_call_events:
            # Build trace from tool call events
            test_id = (
                getattr(self, "_test_id", None) or getattr(execution, "test_id", None) or "unknown"
            )
            self._tool_call_trace = self._build_trace_from_console_events(test_id)

        # If Console parser didn't find data, try the original span parser
        if not self._tool_call_trace:
            spans = self._span_parser.parse(raw_output)
            if spans:
                test_id = (
                    getattr(self, "_test_id", None)
                    or getattr(execution, "test_id", None)
                    or "unknown"
                )
                self._tool_call_trace = self._trace_builder.build(spans, test_id)

        # Parse logs
        events = self._parse_logs(logs)

        # Add tool call summary to events
        if self._tool_call_events:
            events.append(
                {
                    "type": "tool_calls_summary",
                    "level": "info",
                    "message": f"Parsed {len(self._tool_call_events)} tool calls from Console logs",
                }
            )
        elif self._tool_call_trace:
            events.append(
                {
                    "type": "tool_calls_summary",
                    "level": "info",
                    "message": "Parsed tool calls from OTel spans",
                }
            )

        # Build log dictionary
        return {
            "raw_stdout": logs.get("stdout", []),
            "raw_stderr": logs.get("stderr", []),
            "events": events,
            "formatted_output": self.format_for_analysis(
                {
                    "raw_stdout": logs.get("stdout", []),
                    "raw_stderr": logs.get("stderr", []),
                    "events": events,
                    "metadata": {
                        "agent_name": self.agent_name,
                        "collector_type": "otel",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            ),
            "metadata": {
                "agent_name": self.agent_name,
                "collector_type": "otel",
                "timestamp": datetime.now().isoformat(),
                "tool_call_trace": self._tool_call_trace,
                "tool_call_count": len(self._tool_call_events) if self._tool_call_events else 0,
                "api_request_count": len(self._api_request_events)
                if self._api_request_events
                else 0,
                "parse_errors": self._console_parser.get_errors() + self._span_parser.get_errors(),
                "parser_used": "console"
                if self._tool_call_events
                else "span"
                if self._tool_call_trace
                else "none",
            },
        }

    def get_tool_call_trace(self) -> Any | None:
        """
        Get the collected tool call trace.

        Returns:
            ToolCallTrace object or None
        """
        return self._tool_call_trace

    def _parse_logs(self, logs: dict[str, list]) -> list[dict[str, Any]]:
        """
        Parse Claude Code logs.

        Args:
            logs: Log dictionary containing stdout and stderr

        Returns:
            List of events
        """
        events = []
        stdout_text = "\n".join(logs.get("stdout", []))

        # Check if contains OTel keywords
        has_otel = any(keyword.lower() in stdout_text.lower() for keyword in self.OTEL_KEYWORDS)

        if has_otel:
            events.append(
                {
                    "type": "otel_log_detected",
                    "level": "info",
                    "message": "OpenTelemetry logs detected in stdout",
                }
            )

        # Extract actual log content
        for line in logs.get("stdout", []):
            if not line.strip():
                continue

            # Try to parse as JSON (OTel event format)
            try:
                event_data = json.loads(line)
                if isinstance(event_data, dict):
                    events.append(
                        {
                            "type": "otel_event",
                            "level": event_data.get("level", "info"),
                            "message": event_data.get("message", ""),
                        }
                    )
            except json.JSONDecodeError:
                # Not JSON, add as regular log event
                events.append(
                    {
                        "type": "log_line",
                        "level": "info",
                        "message": line,
                    }
                )

        return events

    def format_for_analysis(
        self,
        logs: dict[str, Any],
    ) -> str:
        """
        Format logs for analysis.

        Args:
            logs: Log dictionary returned by collect()

        Returns:
            Formatted log string
        """
        raw_stdout = logs.get("raw_stdout", [])
        raw_stderr = logs.get("raw_stderr", [])
        metadata = logs.get("metadata", {})

        # Extract agent response
        agent_response = self._extract_agent_response(raw_stdout)

        # Build formatted output
        output_lines = []

        # Add metadata
        output_lines.append(f"=== {metadata.get('agent_name', 'unknown')} OTel Log ===")
        output_lines.append(f"Timestamp: {metadata.get('timestamp', 'unknown')}")

        # Add agent response
        if agent_response:
            output_lines.append("\nAgent Response:")
            output_lines.append(agent_response)
            output_lines.append("")

        # Add stderr (if any)
        if raw_stderr:
            output_lines.append("Errors:")
            for line in raw_stderr:
                output_lines.append(f"  {line}")
            output_lines.append("")

        # Add event statistics
        events = logs.get("events", [])
        if events:
            output_lines.append("\nEvents:")
            output_lines.append(f"  Total: {len(events)}")

            # Event type statistics
            event_types = {}
            for event in events:
                event_type = event.get("type", "unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1

            for event_type, count in event_types.items():
                output_lines.append(f"    {event_type}: {count}")

        return "\n".join(output_lines)

    def _build_trace_from_console_events(self, test_id: str) -> ToolCallTrace:
        """Build tool call trace from Console log events.

        Args:
            test_id: Test ID

        Returns:
            ToolCallTrace object
        """
        # Build standard ToolCallEvent objects
        events: dict[str, DomainToolCallEvent] = {}
        root_span_ids: list[str] = []

        for _, tc_event in enumerate(self._tool_call_events):
            # Generate unique span_id
            span_id = f"console_{tc_event.sequence}_{uuid.uuid4().hex[:8]}"

            # Extract parameters from Console event
            attributes = tc_event.attributes or {}
            parameters = self._extract_tool_parameters(tc_event.tool_name, attributes)
            result = self._extract_tool_result(tc_event.tool_name, attributes)

            # Parse timestamp
            start_time = self._parse_timestamp(tc_event.timestamp)

            # Calculate end time
            end_time = None
            if tc_event.duration_ms and isinstance(tc_event.duration_ms, (int, float)):
                end_time = datetime.fromtimestamp(
                    start_time.timestamp() + tc_event.duration_ms / 1000, tz=timezone.utc
                )

            # Create standard ToolCallEvent
            domain_event = DomainToolCallEvent(
                span_id=span_id,
                parent_span_id=None,  # Console logs don't have parent-child relationship info
                tool_name=tc_event.tool_name or "unknown",
                start_time=start_time,
                end_time=end_time,
                parameters=parameters,
                result=result,
                status="success" if tc_event.success else "error",
            )

            events[span_id] = domain_event
            root_span_ids.append(span_id)  # All events treated as root events

        # Calculate total duration
        total_duration_ms = 0
        if self._tool_call_events:
            for tc_event in self._tool_call_events:
                if tc_event.duration_ms and isinstance(tc_event.duration_ms, (int, float)):
                    total_duration_ms += tc_event.duration_ms

        # Build ToolCallTrace
        return ToolCallTrace(
            test_id=test_id,
            events=events,
            root_span_ids=root_span_ids,
            total_calls=len(events),
            total_duration_ms=int(total_duration_ms),
        )

    def _extract_tool_parameters(self, tool_name: str | None, attributes: dict) -> dict:
        """Extract tool parameters from Console event attributes.

        Args:
            tool_name: Tool name
            attributes: Event attributes

        Returns:
            Tool parameters dictionary
        """
        import json

        parameters = {}
        normalized_tool = (tool_name or "").strip().lower()

        # Extract command-related parameters
        if normalized_tool == "bash":
            # Prioritize top-level command field
            if "command" in attributes:
                parameters["command"] = attributes["command"]

            # Parse tool_parameters JSON string (contains full_command and other details)
            if "tool_parameters" in attributes:
                try:
                    tool_params = json.loads(attributes["tool_parameters"])
                    # Extract full_command (complete command)
                    if "full_command" in tool_params:
                        parameters["command"] = tool_params["full_command"]
                    # Extract other fields
                    if "bash_command" in tool_params:
                        parameters["bash_command"] = tool_params["bash_command"]
                    if "description" in tool_params:
                        parameters["description"] = tool_params["description"]
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Keep original logic if JSON parsing fails
                    pass

            # Extract other top-level parameters (as fallback)
            if "description" in attributes and "description" not in parameters:
                parameters["description"] = attributes["description"]
            if "timeout" in attributes:
                parameters["timeout"] = attributes["timeout"]

        # Extract file operation related parameters
        elif normalized_tool in {"read", "edit", "write", "glob", "glob2"}:
            if "file_path" in attributes:
                parameters["file_path"] = attributes["file_path"]
                parameters["path"] = attributes["file_path"]
            if "path" in attributes:
                parameters["file_path"] = attributes["path"]
                parameters["path"] = attributes["path"]
            if "pattern" in attributes:
                parameters["pattern"] = attributes["pattern"]
            if "content" in attributes:
                parameters["content"] = attributes["content"]
            if "old_string" in attributes:
                parameters["old_string"] = attributes["old_string"]
            if "new_string" in attributes:
                parameters["new_string"] = attributes["new_string"]

        elif normalized_tool in {"grep", "search"}:
            if "pattern" in attributes:
                parameters["pattern"] = attributes["pattern"]
            if "path" in attributes:
                parameters["path"] = attributes["path"]
                parameters["file_path"] = attributes["path"]
            if "file_path" in attributes:
                parameters["path"] = attributes["file_path"]
                parameters["file_path"] = attributes["file_path"]
            if "query" in attributes:
                parameters["query"] = attributes["query"]

        # Extract Task related parameters
        elif normalized_tool in {"task", "skill"}:
            for key in ("prompt", "description", "subagent_type", "skill_name", "name"):
                if key in attributes:
                    parameters[key] = attributes[key]

        # Extract WebFetch/WebSearch related parameters
        elif normalized_tool in {"webfetch", "websearch"}:
            if "url" in attributes:
                parameters["url"] = attributes["url"]
            if "query" in attributes:
                parameters["query"] = attributes["query"]

        # Save original attributes for debugging
        parameters["_raw_attributes"] = attributes

        return parameters

    def _extract_tool_result(self, tool_name: str | None, attributes: dict) -> dict:
        """Extract tool result from Console event attributes.

        Args:
            tool_name: Tool name
            attributes: Event attributes

        Returns:
            Tool result dictionary
        """
        result = {}

        # Extract result content
        if "result" in attributes:
            result["output"] = attributes["result"]
        if "output" in attributes:
            result["output"] = attributes["output"]
        if "stdout" in attributes:
            result["stdout"] = attributes["stdout"]
        if "stderr" in attributes:
            result["stderr"] = attributes["stderr"]
        if "error" in attributes:
            result["error"] = attributes["error"]
        if "exit_code" in attributes:
            result["exit_code"] = attributes["exit_code"]

        return result if result else None

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            datetime object
        """
        if not timestamp_str:
            return datetime.now(timezone.utc)

        try:
            # Try to parse ISO format
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)

    def _extract_agent_response(self, stdout: list) -> str:
        """
        Extract agent response from stdout.

        Args:
            stdout: List of stdout lines

        Returns:
            Agent response text, empty string if not found
        """
        filtered_lines = []

        for line in stdout:
            if not line.strip():
                continue

            # Check if this is an OTel metadata line
            is_metadata = False
            for pattern in self.OTEL_PATTERNS:
                if re.search(pattern, line) or any(
                    keyword.lower() in line.lower()
                    for keyword in self.OTEL_KEYWORDS[:6]  # Only check first 6 as metadata markers
                ):
                    is_metadata = True
                    break

            if not is_metadata:
                filtered_lines.append(line)

        return "\n".join(filtered_lines) if filtered_lines else ""

    def __repr__(self) -> str:
        """
        Return string representation of the collector.
        """
        return f"ClaudeOtelLogCollector(agent_name='{self.agent_name}')"
# mypy: disable-error-code="var-annotated,return-value"
