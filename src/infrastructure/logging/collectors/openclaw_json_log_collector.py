# mypy: disable-error-code="override"
"""
OpenClaw JSON Log Collector

Specialized JSON log collector for OpenClaw that extracts tool chain information
from structured JSON logs.

OpenClaw outputs line-delimited JSON (LDJSON) when --json flag is used.
This collector extends JsonLogCollector to also extract tool call events.

JSON log format from OpenClaw may contain:
{"level":"info","timestamp":"...","message":"..."}
{"level":"info","tool":"Bash","input":{"command":"ls"},"output":{"result":"..."}}
{"level":"info","type":"tool_call","tool_name":"Read","parameters":{"file_path":"..."}}
"""

import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from src.domain.logging.entities.tool_call_event import (
    ToolCallEvent as DomainToolCallEvent,
)
from src.domain.logging.entities.tool_call_event import (
    ToolCallTrace,
)
from src.infrastructure.logging.collectors.json_log_collector import JsonLogCollector


class OpenClawJsonLogCollector(JsonLogCollector):
    """
    OpenClaw-specific JSON log collector with tool chain extraction.

    Inherits from JsonLogCollector and adds tool call detection using
    adaptive field detection for OpenClaw JSON output.
    """

    # Adaptive field detection for tool call extraction
    TOOL_NAME_FIELDS = ["tool", "tool_name", "name", "type", "event"]
    INPUT_FIELDS = ["input", "parameters", "params", "args", "data"]
    OUTPUT_FIELDS = ["output", "result", "response", "return"]
    DURATION_FIELDS = ["duration", "duration_ms", "elapsed_ms", "elapsed"]
    STATUS_FIELDS = ["status", "success", "error", "state"]
    TIMESTAMP_FIELDS = ["timestamp", "time", "datetime", "ts"]

    # Tool call type indicators
    TOOL_CALL_TYPE_VALUES = [
        "tool_call", "tool", "function", "method", "action",
        "bash", "read", "write", "edit", "glob", "webfetch",
        "browser", "search", "execute"
    ]
    CANONICAL_TOOL_NAME_MAP = {
        "exec": "bash",
    }

    def __init__(self, config: Any, strict_parsing: bool = False):
        """
        Initialize OpenClaw JSON log collector.

        Args:
            config: Agent configuration object
            strict_parsing: If True, only parse valid JSON lines
        """
        super().__init__(config, strict_parsing)
        self._tool_call_events: list[dict[str, Any]] = []
        self._tool_call_trace: ToolCallTrace | None = None
        self._all_events: list[dict[str, Any]] = []
        self._execution_chain: dict[str, Any] = {"nodes": [], "edges": []}

    async def collect_from_execution(
        self,
        execution: Any,
        agent: Any = None,
        session_jsonl_lines: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Collect JSON logs from OpenSandbox Execution object with tool chain extraction.

        Args:
            execution: Agent execution result (OpenSandbox Execution object)
            agent: Agent instance (optional, for context)

        Returns:
            Structured log dictionary with tool_call_trace in metadata
        """
        # Clear previous collection state
        self._tool_call_events.clear()
        self._tool_call_trace = None
        self._all_events.clear()
        self._execution_chain = {"nodes": [], "edges": []}

        # Use parent class to collect base logs
        result = await super().collect_from_execution(execution, agent)

        # Prefer direct session JSONL parsing when available.
        if session_jsonl_lines:
            session_events = self._parse_session_jsonl_lines(session_jsonl_lines)
            if session_events:
                result["events"] = session_events
                result["raw_stdout"] = [entry["line"] for entry in session_jsonl_lines]
                result["raw_stderr"] = []
                result["metadata"]["log_source"] = "openclaw_session_jsonl"
                result["metadata"]["session_files"] = sorted(
                    {
                        event.get("session_file", "")
                        for event in session_events
                        if event.get("session_file")
                    }
                )
                result["metadata"]["session_entries"] = len(session_events)

        normalized_events = self._normalize_events(result.get("events", []))
        self._all_events = normalized_events
        self._execution_chain = self._build_execution_chain(normalized_events)
        self._tool_call_events = [
            event for event in normalized_events if event.get("kind") == "tool_call"
        ]

        # Build tool call trace if we found any tool calls
        if self._tool_call_events:
            test_id = getattr(self, "_test_id", None) or getattr(execution, "test_id", None) or "unknown"
            self._tool_call_trace = self._build_tool_call_trace(test_id)

        canonical_counts = Counter(
            event.get("tool_name_canonical", "unknown")
            for event in self._tool_call_events
        )

        # Add compact, structured metadata
        result["metadata"]["tool_call_trace"] = self._tool_call_trace
        result["metadata"]["tool_call_count"] = len(self._tool_call_events)
        result["metadata"]["all_events"] = self._all_events
        result["metadata"]["execution_chain"] = self._execution_chain
        result["metadata"]["canonical_tool_breakdown"] = dict(canonical_counts)
        result["metadata"]["collector_type"] = "openclaw_json"

        return result

    def _parse_session_jsonl_lines(self, session_jsonl_lines: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Parse OpenClaw session JSONL lines into normalized json_log events."""
        events: list[dict[str, Any]] = []
        for entry in session_jsonl_lines:
            line = (entry.get("line") or "").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                if not self._strict_parsing:
                    events.append(
                        {
                            "type": "text_log",
                            "level": "info",
                            "message": line,
                            "source": "openclaw_session",
                            "session_file": entry.get("path", ""),
                        }
                    )
                continue

            if not isinstance(data, dict):
                continue

            events.append(
                {
                    "type": "json_log",
                    "level": data.get("level", data.get("severity", "info")),
                    "message": data.get("message", ""),
                    "data": data,
                    "source": "openclaw_session",
                    "session_file": entry.get("path", ""),
                }
            )
        return events

    @classmethod
    def _canonical_tool_name(cls, tool_name: str) -> str:
        lowered = (tool_name or "").strip().lower()
        return cls.CANONICAL_TOOL_NAME_MAP.get(lowered, lowered or "unknown")

    @staticmethod
    def _parse_timestamp_value(timestamp_str: Any) -> datetime:
        if isinstance(timestamp_str, str) and timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _normalize_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize OpenClaw events into a full execution-event stream."""
        normalized: list[dict[str, Any]] = []

        for index, event in enumerate(events):
            source = event.get("source", "execution_output")
            session_file = event.get("session_file", "")

            if event.get("type") != "json_log":
                normalized.append(
                    {
                        "event_id": f"text_{index}",
                        "parent_event_id": None,
                        "kind": event.get("type", "text_log"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": source,
                        "session_file": session_file,
                        "data": {"message": event.get("message", "")},
                    }
                )
                continue

            data = event.get("data", {})
            if not isinstance(data, dict):
                continue

            raw_type = str(data.get("type", "json_log"))
            event_id = str(data.get("id") or f"event_{index}_{uuid.uuid4().hex[:8]}")
            parent_id = data.get("parentId")
            base_timestamp = self._parse_timestamp_value(data.get("timestamp")).isoformat()

            base_node = {
                "event_id": event_id,
                "parent_event_id": str(parent_id) if parent_id else None,
                "kind": raw_type,
                "timestamp": base_timestamp,
                "source": source,
                "session_file": session_file,
                "data": data,
            }
            normalized.append(base_node)

            message = data.get("message")
            if not isinstance(message, dict):
                continue

            role = str(message.get("role", "unknown"))
            message_timestamp = self._parse_timestamp_value(
                message.get("timestamp", data.get("timestamp"))
            ).isoformat()

            message_node_id = f"{event_id}:message"
            normalized.append(
                {
                    "event_id": message_node_id,
                    "parent_event_id": event_id,
                    "kind": "message",
                    "role": role,
                    "timestamp": message_timestamp,
                    "source": source,
                    "session_file": session_file,
                    "data": message,
                }
            )

            if role == "toolResult":
                tool_name_raw = str(message.get("toolName", "unknown"))
                normalized.append(
                    {
                        "event_id": f"{message_node_id}:tool_result",
                        "parent_event_id": message_node_id,
                        "kind": "tool_result",
                        "tool_call_id": message.get("toolCallId"),
                        "tool_name_raw": tool_name_raw,
                        "tool_name_canonical": self._canonical_tool_name(tool_name_raw),
                        "status": "error" if message.get("isError") else "success",
                        "timestamp": message_timestamp,
                        "source": source,
                        "session_file": session_file,
                        "result": {
                            "content": message.get("content"),
                            "details": message.get("details"),
                        },
                        "data": message,
                    }
                )

            for content_index, content in enumerate(message.get("content", []) or []):
                if not isinstance(content, dict):
                    continue

                content_type = str(content.get("type", "content"))
                content_node_id = f"{message_node_id}:content:{content_index}"
                common_content_node = {
                    "event_id": content_node_id,
                    "parent_event_id": message_node_id,
                    "kind": "content",
                    "content_type": content_type,
                    "timestamp": message_timestamp,
                    "source": source,
                    "session_file": session_file,
                    "data": content,
                }
                normalized.append(common_content_node)

                if content_type == "toolCall":
                    tool_name_raw = str(content.get("name", "unknown"))
                    normalized.append(
                        {
                            "event_id": str(content.get("id") or content_node_id),
                            "parent_event_id": content_node_id,
                            "kind": "tool_call",
                            "tool_call_id": content.get("id"),
                            "tool_name_raw": tool_name_raw,
                            "tool_name_canonical": self._canonical_tool_name(tool_name_raw),
                            "parameters": content.get("arguments", {}) or {},
                            "timestamp": message_timestamp,
                            "source": source,
                            "session_file": session_file,
                            "data": content,
                        }
                    )

        return normalized

    def _build_execution_chain(self, normalized_events: list[dict[str, Any]]) -> dict[str, Any]:
        """Build execution chain edges from normalized events."""
        nodes = [dict(event) for event in normalized_events]
        edges: list[dict[str, Any]] = []

        for event in normalized_events:
            parent_id = event.get("parent_event_id")
            if parent_id:
                edges.append(
                    {
                        "type": "parent",
                        "from": parent_id,
                        "to": event["event_id"],
                    }
                )

        tool_call_nodes = {
            event.get("tool_call_id"): event["event_id"]
            for event in normalized_events
            if event.get("kind") == "tool_call" and event.get("tool_call_id")
        }
        for event in normalized_events:
            if event.get("kind") != "tool_result":
                continue
            tool_call_id = event.get("tool_call_id")
            if tool_call_id and tool_call_id in tool_call_nodes:
                edges.append(
                    {
                        "type": "tool_result",
                        "from": tool_call_nodes[tool_call_id],
                        "to": event["event_id"],
                        "tool_call_id": tool_call_id,
                    }
                )

        return {"nodes": nodes, "edges": edges}

    def _extract_tool_calls_from_events(self, events: list[dict[str, Any]]) -> None:
        """
        Extract tool call events from parsed JSON log events.

        Args:
            events: List of parsed event dictionaries
        """
        for event in events:
            if event.get("type") != "json_log":
                continue

            data = event.get("data", {})
            if not data:
                continue

            # Check if this entry looks like a tool call
            if self._is_tool_call_entry(data):
                self._tool_call_events.append(data)

    def _extract_behaviors_from_events(self, events: list[dict[str, Any]]) -> None:
        """Extract all behavior events from json_log entries."""
        behavior_events: list[dict[str, Any]] = []
        for index, event in enumerate(events):
            if event.get("type") != "json_log":
                continue

            data = event.get("data", {})
            if not isinstance(data, dict):
                continue

            behavior_type = self._classify_behavior(data)
            behavior_events.append(
                {
                    "index": index,
                    "timestamp": self._parse_timestamp(data).isoformat(),
                    "behavior_type": behavior_type,
                    "action": self._extract_action_name(data),
                    "tool_name": self._extract_tool_name(data),
                    "status": self._extract_status(data),
                    "source": event.get("source", "execution_output"),
                    "session_file": event.get("session_file", ""),
                    "data": data,
                }
            )
        self._behavior_events = behavior_events

    def _extract_action_name(self, data: dict[str, Any]) -> str:
        """Extract human-readable action name."""
        for key in ["action", "event", "type", "message"]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "unknown"

    def _classify_behavior(self, data: dict[str, Any]) -> str:
        """Classify behavior type for a log entry."""
        if self._is_tool_call_entry(data):
            return "tool_call"

        type_or_event = " ".join(
            str(data.get(key, "")).lower() for key in ["type", "event", "action"]
        )
        if any(role in type_or_event for role in ["assistant", "user", "system", "message", "chat"]):
            return "message"

        input_data = self._extract_first_match(data, self.INPUT_FIELDS)
        if isinstance(input_data, dict):
            input_keys = set(input_data.keys())
            if {"command", "cmd", "shell", "bash"} & input_keys:
                return "command"
            if {"file_path", "path", "source", "target"} & input_keys:
                return "file_io"
            if {"url", "uri", "host", "endpoint"} & input_keys:
                return "network"

        if any(k in data for k in ["error", "exception", "stack"]):
            return "error"
        if str(data.get("level", "")).lower() == "error":
            return "error"
        return "other"

    def _summarize_behaviors(self, behaviors: list[dict[str, Any]]) -> dict[str, int]:
        """Build behavior type counts."""
        summary: dict[str, int] = {}
        for behavior in behaviors:
            behavior_type = behavior.get("behavior_type", "other")
            summary[behavior_type] = summary.get(behavior_type, 0) + 1
        return summary

    def _is_tool_call_entry(self, data: dict[str, Any]) -> bool:
        """
        Determine if a JSON entry represents a tool call.

        Args:
            data: Parsed JSON data

        Returns:
            True if this is a tool call entry
        """
        # Check type field
        type_value = data.get("type", "")
        if isinstance(type_value, str):
            type_lower = type_value.lower()
            if any(t in type_lower for t in self.TOOL_CALL_TYPE_VALUES):
                return True

        # Check for tool name in known fields
        tool_name = self._extract_first_match(data, self.TOOL_NAME_FIELDS)
        if tool_name and isinstance(tool_name, str):
            tool_lower = tool_name.lower()
            # Check if it's a known tool name
            if any(t in tool_lower for t in self.TOOL_CALL_TYPE_VALUES):
                return True
            # Also accept if it looks like a tool (non-generic name)
            if len(tool_name) > 2 and "log" not in tool_lower and "message" not in tool_lower:
                return True

        # Check for input/parameters with command-like content
        input_data = self._extract_first_match(data, self.INPUT_FIELDS)
        if input_data and isinstance(input_data, dict):
            # Look for command-like fields in input
            if any(k in input_data for k in ["command", "cmd", "file_path", "path", "url"]):
                return True

        return False

    def _extract_first_match(self, data: dict[str, Any], fields: list[str]) -> Any:
        """
        Extract first matching field from data.

        Args:
            data: Dictionary to search
            fields: List of field names to try

        Returns:
            Value of first matching field, or None
        """
        for field in fields:
            if field in data:
                return data[field]
        return None

    def _extract_tool_name(self, data: dict[str, Any]) -> str:
        """
        Extract tool name from entry.

        Args:
            data: Tool call entry data

        Returns:
            Tool name string
        """
        tool_name = self._extract_first_match(data, self.TOOL_NAME_FIELDS)
        if tool_name:
            return str(tool_name)
        return "unknown"

    def _extract_parameters(self, data: dict[str, Any]) -> dict:
        """
        Extract tool parameters from entry.

        Args:
            data: Tool call entry data

        Returns:
            Parameters dictionary
        """
        input_data = self._extract_first_match(data, self.INPUT_FIELDS)
        if isinstance(input_data, dict):
            return input_data
        elif input_data:
            return {"value": input_data}
        return {}

    def _extract_result(self, data: dict[str, Any]) -> dict:
        """
        Extract tool result from entry.

        Args:
            data: Tool call entry data

        Returns:
            Result dictionary
        """
        output_data = self._extract_first_match(data, self.OUTPUT_FIELDS)
        if isinstance(output_data, dict):
            return output_data
        elif output_data:
            return {"value": output_data}
        return {}

    def _extract_duration_ms(self, data: dict[str, Any]) -> int | None:
        """
        Extract duration in milliseconds.

        Args:
            data: Tool call entry data

        Returns:
            Duration in ms or None
        """
        duration = self._extract_first_match(data, self.DURATION_FIELDS)
        if duration is not None:
            try:
                return int(duration)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_status(self, data: dict[str, Any]) -> str:
        """
        Extract tool call status.

        Args:
            data: Tool call entry data

        Returns:
            Status string: "success", "error", or "pending"
        """
        status = self._extract_first_match(data, self.STATUS_FIELDS)
        if status is not None:
            if isinstance(status, bool):
                return "success" if status else "error"
            status_str = str(status).lower()
            if status_str in ["success", "ok", "true", "completed", "done"]:
                return "success"
            elif status_str in ["error", "failed", "false", "timeout"]:
                return "error"
        return "success"

    def _parse_timestamp(self, data: dict[str, Any]) -> datetime:
        """
        Parse timestamp from entry data.

        Args:
            data: Tool call entry data

        Returns:
            datetime object
        """
        timestamp_str = self._extract_first_match(data, self.TIMESTAMP_FIELDS)
        if timestamp_str:
            try:
                # Handle ISO format
                ts = timestamp_str.replace("Z", "+00:00")
                return datetime.fromisoformat(ts)
            except (ValueError, AttributeError):
                pass
        return datetime.now(timezone.utc)

    def _build_tool_call_trace(self, test_id: str) -> ToolCallTrace:
        """
        Build ToolCallTrace from extracted tool call events.

        Args:
            test_id: Test identifier

        Returns:
            ToolCallTrace object
        """
        events: dict[str, DomainToolCallEvent] = {}
        root_span_ids: list[str] = []

        tool_results = {
            event.get("tool_call_id"): event
            for event in self._all_events
            if event.get("kind") == "tool_result" and event.get("tool_call_id")
        }

        for i, tool_data in enumerate(self._tool_call_events):
            # Generate unique span_id
            span_id = f"openclaw_{i}_{uuid.uuid4().hex[:8]}"

            tool_call_id = tool_data.get("tool_call_id")
            matched_result = tool_results.get(tool_call_id) if tool_call_id else None

            tool_name = str(tool_data.get("tool_name_canonical", "unknown"))
            parameters = tool_data.get("parameters", {}) or {}
            result = matched_result.get("result") if matched_result else None
            status = matched_result.get("status", "success") if matched_result else "success"
            start_time = self._parse_timestamp_value(tool_data.get("timestamp"))
            end_time = self._parse_timestamp_value(matched_result.get("timestamp")) if matched_result else None

            # Calculate end time
            duration_ms = None
            if end_time:
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                if duration_ms < 0:
                    duration_ms = 0
                    end_time = start_time

            # Create domain tool call event
            domain_event = DomainToolCallEvent(
                span_id=span_id,
                parent_span_id=None,  # OpenClaw JSON doesn't have parent info
                tool_name=tool_name,
                start_time=start_time,
                end_time=end_time,
                parameters=parameters,
                result=result,
                status=status,
            )

            events[span_id] = domain_event
            root_span_ids.append(span_id)

        # Calculate total duration
        total_duration_ms = 0
        for event in events.values():
            if event.end_time:
                total_duration_ms += int((event.end_time - event.start_time).total_seconds() * 1000)

        return ToolCallTrace(
            test_id=test_id,
            events=events,
            root_span_ids=root_span_ids,
            total_calls=len(events),
            total_duration_ms=total_duration_ms,
        )

    def get_tool_call_trace(self) -> ToolCallTrace | None:
        """
        Get the collected tool call trace.

        Returns:
            ToolCallTrace object or None
        """
        return self._tool_call_trace
