"""OTel span parser for extracting tool call data from Claude Code output.

This module parses OpenTelemetry span data embedded in Claude Code's stdout,
extracting structured information about tool calls.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, cast


class OtelParseError(Exception):
    """Raised when OTel parsing fails in strict mode."""

    pass


@dataclass
class OtelSpanData:
    """Raw span data extracted from OTel logs.

    Attributes:
        span_id: Unique span identifier
        parent_span_id: Parent span ID for building call tree
        span_name: Name of the span (e.g., "Bash", "Read")
        start_time: Start time in nanoseconds (Unix epoch)
        end_time: End time in nanoseconds (Unix epoch)
        attributes: Span attributes containing tool parameters
        events: List of events within the span
        status: Span status information
    """

    span_id: str
    parent_span_id: str | None
    span_name: str
    start_time: int
    end_time: int
    attributes: dict[str, Any]
    events: list[dict]
    status: dict[str, Any]


class OtelSpanParser:
    """Parser for Claude Code OpenTelemetry span data.

    Extracts structured span information from the JSON-formatted OTel events
    that Claude Code outputs to stdout.
    """

    # Pattern to find JSON objects that look like OTel spans
    OTEL_JSON_PATTERN = re.compile(r'\{[^{}]*"span_id"[^{}]*\}', re.DOTALL)

    def __init__(self, strict: bool = False):
        """Initialize the parser.

        Args:
            strict: If True, raise exceptions on parse errors.
                    If False, skip malformed data and collect errors.
        """
        self._strict = strict
        self._errors: list[str] = []

    def parse(self, raw_output: str) -> dict[str, OtelSpanData]:
        """Parse OTel span data from raw stdout output.

        Args:
            raw_output: Complete stdout from Claude Code execution

        Returns:
            Mapping of span_id to OtelSpanData

        Raises:
            OtelParseError: If strict mode is enabled and parsing fails
        """
        self._errors.clear()
        spans: dict[str, OtelSpanData] = {}

        try:
            json_blocks = self._extract_json_blocks(raw_output)

            for i, block in enumerate(json_blocks):
                try:
                    data = json.loads(block)
                    span = self._parse_single_span(data)
                    if span:
                        spans[span.span_id] = span
                except json.JSONDecodeError as e:
                    self._handle_error(f"JSON decode error at block {i}: {e}")
                except (KeyError, TypeError) as e:
                    self._handle_error(f"Missing required field in block {i}: {e}")
                except Exception as e:
                    self._handle_error(f"Unexpected error at block {i}: {e}")

        except Exception as e:
            if self._strict:
                raise OtelParseError(f"Failed to parse OTel output: {e}") from e

        return spans

    def _extract_json_blocks(self, output: str) -> list[str]:
        """Extract all JSON-like blocks from output.

        Args:
            output: Raw stdout string

        Returns:
            List of strings that look like JSON objects
        """
        # Find potential JSON objects by looking for span_id key
        # Then extract the complete JSON object by matching braces
        json_blocks = []

        # Find all positions of "span_id"
        span_id_pattern = re.compile(r'"span_id"\s*:')
        for match in span_id_pattern.finditer(output):
            # Find the start of this JSON object (opening brace)
            start = output.rfind("{", 0, match.start())
            if start == -1:
                continue

            # Find the matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            i = start

            while i < len(output):
                char = output[i]

                if escape_next:
                    escape_next = False
                    i += 1
                    continue

                if char == "\\" and in_string:
                    escape_next = True
                    i += 1
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    i += 1
                    continue

                if not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            # Found matching closing brace
                            json_blocks.append(output[start : i + 1])
                            break

                i += 1

        return json_blocks

    def _parse_single_span(self, data: dict) -> OtelSpanData | None:
        """Parse a single span from JSON data.

        Args:
            data: Parsed JSON dictionary

        Returns:
            OtelSpanData if valid, None if missing required fields
        """
        span_id = data.get("span_id")
        if not span_id:
            return None

        # Extract tool name from span name
        span_name = data.get("name", "unknown")
        tool_name = self._extract_tool_name(span_name, data.get("attributes", {}))

        return OtelSpanData(
            span_id=span_id,
            parent_span_id=data.get("parent_span_id"),
            span_name=tool_name,
            start_time=data.get("start_time_nanos", 0),
            end_time=data.get("end_time_nanos", 0),
            attributes=data.get("attributes", {}),
            events=data.get("events", []),
            status=data.get("status", {}),
        )

    def _extract_tool_name(self, span_name: str, attributes: dict) -> str:
        """Extract clean tool name from span name.

        Claude Code span names are often in "ToolName.action" format.
        This extracts just the tool name.

        Args:
            span_name: Raw span name
            attributes: Span attributes (fallback)

        Returns:
            Clean tool name
        """
        if "." in span_name:
            return span_name.split(".", 1)[0]

        # Fallback to attributes
        return cast(str, attributes.get("tool.name", span_name))

    def _handle_error(self, message: str) -> None:
        """Handle a parsing error.

        Args:
            message: Error message

        Raises:
            OtelParseError: If in strict mode
        """
        self._errors.append(message)
        if self._strict:
            raise OtelParseError(message)

    def get_errors(self) -> list[str]:
        """Get list of parsing errors.

        Returns:
            List of error messages from non-strict parsing
        """
        return self._errors.copy()

    def has_errors(self) -> bool:
        """Check if any errors occurred during parsing.

        Returns:
            True if errors were collected
        """
        return len(self._errors) > 0
