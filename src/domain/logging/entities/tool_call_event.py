"""Tool call event and trace data structures.

This module defines the core data structures for representing tool calls
made by Claude Code agents, including individual events and complete traces.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToolCallEvent:
    """Represents a single tool call event.

    Attributes:
        span_id: Unique identifier for this span (from OTel)
        parent_span_id: ID of the parent span, used to build call tree
        tool_name: Name of the tool (e.g., "Bash", "Read", "Edit")
        start_time: When the tool call started
        end_time: When the tool call completed
        parameters: Input parameters passed to the tool
        result: Output result returned by the tool
        status: Status of the call (pending, success, error)
        model: LLM model used (if applicable)
        tokens_used: Number of tokens consumed (if applicable)
        children: List of child span IDs that were triggered by this call
        tool_use_id: Anthropic SDK identifier pairing tool_use to tool_result
        cache_read_input_tokens: Tokens read from input cache (from stream-json)
        cache_creation_input_tokens: Tokens used to create input cache (from stream-json)
        output_tokens: Output tokens used (from stream-json)
    """

    span_id: str
    parent_span_id: str | None
    tool_name: str
    start_time: datetime
    end_time: datetime | None
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    status: str
    model: str | None = None
    tokens_used: int | None = None
    children: list[str] = field(default_factory=list)
    tool_use_id: str | None = None
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass
class ToolCallTrace:
    """Represents a complete tool call trace.

    A trace contains all tool calls made during a single test execution,
    organized as a tree structure based on parent-child relationships.

    Attributes:
        test_id: Identifier for the test
        events: Mapping of span_id to ToolCallEvent
        root_span_ids: List of top-level span IDs (no parent)
        total_calls: Total number of tool calls in the trace
        total_duration_ms: Total execution time in milliseconds
    """

    test_id: str
    events: dict[str, ToolCallEvent]
    root_span_ids: list[str]
    total_calls: int
    total_duration_ms: int

    def get_event_tree(self) -> list[ToolCallEvent]:
        """Get events in tree order (BFS from roots).

        Returns:
            List of events starting from roots, then children level by level
        """
        result = []
        queue = list(self.root_span_ids)

        while queue:
            span_id = queue.pop(0)
            if span_id in self.events:
                event = self.events[span_id]
                result.append(event)
                queue.extend(event.children)

        return result

    def get_timeline(self) -> list[ToolCallEvent]:
        """Get events in chronological order.

        Returns:
            List of events sorted by start_time
        """
        events = list(self.events.values())
        events.sort(key=lambda e: e.start_time)
        return events
