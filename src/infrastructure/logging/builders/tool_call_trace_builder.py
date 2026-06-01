"""Tool call trace builder.

This module builds complete tool call traces from parsed OTel span data,
establishing parent-child relationships and extracting tool-specific parameters.
"""

from datetime import datetime, timezone
from typing import Any

from src.domain.logging.entities.tool_call_event import ToolCallEvent, ToolCallTrace
from src.infrastructure.logging.parsers.otel_span_parser import OtelSpanData


class ToolCallTraceBuilder:
    """Builds tool call traces from OTel span data.

    This class converts raw OtelSpanData objects into structured ToolCallEvent
    objects and builds complete call trees with parent-child relationships.
    """

    def __init__(self) -> None:
        self._events: dict[str, ToolCallEvent] = {}
        self._root_span_ids: list[str] = []

    def build(self, spans: dict[str, OtelSpanData], test_id: str) -> ToolCallTrace:
        """Build a complete tool call trace from span data.

        Args:
            spans: Mapping of span_id to OtelSpanData
            test_id: Test case identifier

        Returns:
            Complete ToolCallTrace with all events and relationships
        """
        self._events.clear()
        self._root_span_ids.clear()

        # Convert each span to a ToolCallEvent
        for span_id, span_data in spans.items():
            event = self._span_to_event(span_data)
            self._events[span_id] = event

        # Build parent-child relationships
        self._build_relationships()

        # Identify root spans
        self._identify_roots()

        # Calculate statistics
        total_duration = self._calculate_total_duration()

        return ToolCallTrace(
            test_id=test_id,
            events=self._events,
            root_span_ids=self._root_span_ids,
            total_calls=len(self._events),
            total_duration_ms=total_duration,
        )

    def _span_to_event(self, span: OtelSpanData) -> ToolCallEvent:
        """Convert OtelSpanData to ToolCallEvent.

        Args:
            span: Raw span data

        Returns:
            Structured tool call event
        """
        parameters, result = self._extract_parameters_and_result(span)

        return ToolCallEvent(
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            tool_name=span.span_name,
            start_time=self._nanos_to_datetime(span.start_time),
            end_time=self._nanos_to_datetime(span.end_time),
            parameters=parameters,
            result=result,
            status=self._determine_status(span),
            model=self._extract_model(span),
            tokens_used=self._extract_tokens(span),
        )

    def _extract_parameters_and_result(
        self, span: OtelSpanData
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Extract tool parameters and result from span attributes.

        Args:
            span: Raw span data

        Returns:
            Tuple of (parameters dict, result dict or None)
        """
        parameters = {}
        result = None
        attrs = span.attributes

        if span.span_name == "Bash":
            parameters = {
                "command": attrs.get("bash.command", ""),
                "timeout": attrs.get("bash.timeout"),
            }
            result = {
                "exit_code": attrs.get("bash.exit_code"),
                "stdout": attrs.get("bash.stdout"),
                "stderr": attrs.get("bash.stderr"),
            }

        elif span.span_name == "Read":
            parameters = {"file_path": attrs.get("read.file_path", "")}
            result = {"content": attrs.get("read.content")}

        else:
            # Generic extraction for other tools
            parameters = {
                k: v
                for k, v in attrs.items()
                if not k.startswith("otel.") and not k.startswith("telemetry.")
            }

        return parameters, result

    def _determine_status(self, span: OtelSpanData) -> str:
        """Determine tool call status from span status.

        Args:
            span: Raw span data

        Returns:
            Status string: "success", "error", or "pending"
        """
        status = span.status.get("status", "unknown")
        if status == "OK":
            return "success"
        elif status == "ERROR":
            return "error"
        return "pending"

    def _build_relationships(self) -> None:
        """Build parent-child relationships between events."""
        for span_id, event in self._events.items():
            parent_id = event.parent_span_id
            if parent_id and parent_id in self._events:
                self._events[parent_id].children.append(span_id)

    def _identify_roots(self) -> None:
        """Identify root spans (those without parents in the trace)."""
        for span_id, event in self._events.items():
            if not event.parent_span_id or event.parent_span_id not in self._events:
                self._root_span_ids.append(span_id)

    def _calculate_total_duration(self) -> int:
        """Calculate total trace duration in milliseconds.

        Returns:
            Duration from earliest start to latest end
        """
        if not self._events:
            return 0

        start_times = [e.start_time for e in self._events.values() if e.start_time]
        end_times = [e.end_time for e in self._events.values() if e.end_time]

        if not start_times or not end_times:
            return 0

        total_duration = max(end_times) - min(start_times)
        return int(total_duration.total_seconds() * 1000)

    @staticmethod
    def _nanos_to_datetime(nanos: int) -> datetime:
        """Convert nanoseconds since epoch to datetime.

        Args:
            nanos: Nanoseconds since Unix epoch

        Returns:
            datetime object in UTC
        """
        return datetime.fromtimestamp(nanos / 1_000_000_000, tz=timezone.utc)

    @staticmethod
    def _extract_model(span: OtelSpanData) -> str | None:
        """Extract LLM model from span attributes.

        Args:
            span: Raw span data

        Returns:
            Model name or None
        """
        return span.attributes.get("llm.model")

    @staticmethod
    def _extract_tokens(span: OtelSpanData) -> int | None:
        """Extract token usage from span attributes.

        Args:
            span: Raw span data

        Returns:
            Token count or None
        """
        tokens = span.attributes.get("llm.tokens_used")
        return int(tokens) if tokens is not None else None
