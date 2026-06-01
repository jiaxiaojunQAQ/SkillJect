"""
Claude Code Console Log Parser

Parses JavaScript object literal format logs output by Claude Code OTel Console Exporter.

Log format example:
{
  resource: {
    attributes: {
      'service.name': 'claude-code',
      ...
    }
  },
  body: 'claude_code.tool_result',
  attributes: {
    'event.name': 'tool_result',
    'tool_name': 'Glob',
    ...
  }
}
"""

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCallEvent:
    """Tool call event.

    Attributes:
        sequence: Event sequence number
        timestamp: ISO format timestamp
        tool_name: Tool name
        event_type: Event type (tool_result, api_request, user_prompt)
        success: Whether successful
        duration_ms: Execution duration in milliseconds
        attributes: All attributes
    """

    sequence: int
    timestamp: str
    tool_name: str | None
    event_type: str
    success: str | None
    duration_ms: str | None
    attributes: dict[str, Any]

    def __post_init__(self):
        """Convert types."""
        if isinstance(self.duration_ms, str):
            try:
                self.duration_ms = int(self.duration_ms)
            except (ValueError, TypeError):
                pass


@dataclass
class ApiRequestEvent:
    """API request event.

    Attributes:
        sequence: Event sequence number
        timestamp: ISO format timestamp
        model: Model name
        input_tokens: Input token count
        output_tokens: Output token count
        cost_usd: Cost in USD
        duration_ms: Execution duration in milliseconds
    """

    sequence: int
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float
    duration_ms: int

    def __post_init__(self):
        """Convert types."""
        for int_field in ["input_tokens", "output_tokens", "cache_read_tokens", "duration_ms"]:
            value = getattr(self, int_field)
            if isinstance(value, str):
                try:
                    setattr(self, int_field, int(value))
                except (ValueError, TypeError):
                    pass

        if isinstance(self.cost_usd, str):
            try:
                self.cost_usd = float(self.cost_usd)
            except (ValueError, TypeError):
                pass


class ClaudeConsoleLogParser:
    """Parser for Claude Code Console OTel logs.

    Processes OTel logs in JavaScript object literal format,
    extracting tool calls and API request events.
    """

    # Pattern matching object start
    OBJECT_START_PATTERN = re.compile(r"\{\s*resource:")

    def __init__(self):
        """Initialize parser."""
        self._errors: list[str] = []
        self._raw_events: list[dict] = []
        self._tool_calls: list[ToolCallEvent] = []
        self._api_requests: list[ApiRequestEvent] = []

    def parse(self, raw_output: str) -> dict[str, Any]:
        """Parse raw output.

        Args:
            raw_output: Claude Code stdout output

        Returns:
            Dictionary containing parsed results:
            {
                "tool_calls": list[ToolCallEvent],
                "api_requests": list[ApiRequestEvent],
                "raw_events": list[dict],
                "errors": list[str]
            }
        """
        self._errors.clear()
        self._raw_events.clear()
        self._tool_calls.clear()
        self._api_requests.clear()

        # Extract all event objects
        events = self._extract_events(raw_output)
        self._raw_events = events

        # Categorize events
        for event in events:
            try:
                self._process_event(event)
            except Exception as e:
                self._errors.append(f"Failed to process event: {e}")

        # Sort by sequence
        self._tool_calls.sort(key=lambda x: x.sequence)
        self._api_requests.sort(key=lambda x: x.sequence)

        return {
            "tool_calls": self._tool_calls,
            "api_requests": self._api_requests,
            "raw_events": self._raw_events,
            "errors": self._errors,
        }

    def _extract_events(self, output: str) -> list[dict]:
        """Extract all event objects from output.

        Args:
            output: Raw output string

        Returns:
            List of event dictionaries
        """
        events = []

        # Extract events directly from raw output (no preprocessing)
        for match in self._find_js_objects(output):
            try:
                event = self._parse_js_object(match)
                if event:
                    events.append(event)
            except Exception as e:
                self._errors.append(f"Failed to parse event: {e}")

        return events

    def _normalize_js_objects(self, text: str) -> str:
        """Convert JavaScript object literals to JSON-like format.

        Mainly handles:
        - Add quotes to key names
        - Handle undefined values
        - Handle single-quoted strings

        Args:
            text: Original text

        Returns:
            Normalized text
        """
        result = []
        for line in text.split("\n"):
            # Skip non-object lines
            if not line.strip() or not line.strip().startswith("{"):
                continue

            # Convert single-quoted strings to double-quoted
            line = line.replace("'", '"')

            # Add quotes to unquoted key names
            # Matches: word: or word  : (word followed by colon, possibly with spaces)
            line = re.sub(r"(\w+)\s*:", r'"\1":', line)

            # Handle undefined -> null
            line = line.replace("undefined", "null")

            result.append(line)

        return "\n".join(result)

    def _find_js_objects(self, text: str) -> list[str]:
        """Find all JavaScript objects.

        Args:
            text: Original text

        Returns:
            List of object strings
        """
        objects = []
        i = 0

        while i < len(text):
            # Skip whitespace
            while i < len(text) and text[i] not in ["{", "\n"]:
                i += 1

            if i >= len(text):
                break

            # Find object start
            if text[i] != "{":
                i += 1
                continue

            # Extract complete object
            start = i
            brace_count = 0
            in_string = False
            escape_next = False

            while i < len(text):
                char = text[i]

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
                            # Found complete object
                            obj_str = text[start : i + 1]
                            # Validate object content (ensure not empty object)
                            if self._is_valid_event_object(obj_str):
                                objects.append(obj_str)
                            i += 1
                            break

                i += 1

        return objects

    def _is_valid_event_object(self, obj_str: str) -> bool:
        """Validate if object is a valid event object.

        Args:
            obj_str: Object string

        Returns:
            Whether valid
        """
        # Check if contains key fields
        keywords = ["resource", "attributes", "body", "event.name"]
        obj_lower = obj_str.lower()
        return any(kw.lower() in obj_lower for kw in keywords)

    def _parse_js_object(self, obj_str: str) -> dict | None:
        """Parse JavaScript object string.

        Args:
            obj_str: Object string

        Returns:
            Parsed dictionary, None on failure
        """
        try:
            # First try to parse as JSON directly
            cleaned = obj_str.strip()
            if not cleaned or cleaned == "{}":
                return None

            # Try JSON parsing
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # If JSON parsing fails, convert to JSON then parse
            json_str = self._convert_js_to_json(obj_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If still fails, log error and return None
                self._errors.append(f"Unable to parse object: {obj_str[:100]}...")
                return None

    def _convert_js_to_json(self, js_str: str) -> str:
        """Convert JavaScript object literal to JSON.

        Args:
            js_str: JavaScript object string

        Returns:
            JSON string
        """
        result = js_str

        # Handle undefined -> null
        result = result.replace("undefined", "null")

        # Handle single-quoted strings: only replace single-quoted strings
        # Matches 'value' format and converts to "value"
        result = re.sub(r"'([^']*)'", r'"\1"', result)

        # Add quotes to unquoted key names
        # Only match words at line start or after brace/comma, avoid matching words in values
        result = re.sub(r"([{\s,]\s*)(\w+)(\s*:)", r'\1"\2"\3', result)

        return result

    def _parse_js_object_manual(self, obj_str: str) -> dict | None:
        """Manually parse JavaScript object (extract key attributes).

        Args:
            obj_str: Object string

        Returns:
            Parsed dictionary
        """
        result = {}
        lines = obj_str.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line in ["{", "}", "},"]:
                continue

            # Match key: value format (handle various quote cases)
            match = re.match(r'["\']?([^"\'\s:,]+)["\']?\s*:\s*(.+)', line)
            if match:
                key = match.group(1)
                value = match.group(2).rstrip(",")

                # Handle different value types
                if value == "null" or value == "undefined":
                    result[key] = None
                elif value == "true":
                    result[key] = True
                elif value == "false":
                    result[key] = False
                elif value.startswith('"') and value.endswith('"'):
                    result[key] = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    result[key] = value[1:-1]
                elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                    result[key] = int(value)
                else:
                    result[key] = value

        return result

    def _process_event(self, event: dict) -> None:
        """Process single event.

        Args:
            event: Event dictionary
        """
        attributes = event.get("attributes", {})
        body = event.get("body", "")
        event_name = attributes.get("event.name", "")

        # Extract common fields
        sequence = int(attributes.get("event.sequence", 0))
        timestamp = attributes.get("event.timestamp", "")

        if event_name == "tool_result" or body == "claude_code.tool_result":
            self._process_tool_call(sequence, timestamp, attributes)
        elif event_name == "api_request" or body == "claude_code.api_request":
            self._process_api_request(sequence, timestamp, attributes)

    def _process_tool_call(self, sequence: int, timestamp: str, attributes: dict) -> None:
        """Process tool call event.

        Args:
            sequence: Event sequence number
            timestamp: Timestamp
            attributes: Event attributes
        """
        tool_call = ToolCallEvent(
            sequence=sequence,
            timestamp=timestamp,
            tool_name=attributes.get("tool_name"),
            event_type="tool_result",
            success=attributes.get("success"),
            duration_ms=attributes.get("duration_ms"),
            attributes=attributes,
        )
        self._tool_calls.append(tool_call)

    def _process_api_request(self, sequence: int, timestamp: str, attributes: dict) -> None:
        """Process API request event.

        Args:
            sequence: Event sequence number
            timestamp: Timestamp
            attributes: Event attributes
        """
        api_request = ApiRequestEvent(
            sequence=sequence,
            timestamp=timestamp,
            model=attributes.get("model", ""),
            input_tokens=int(attributes.get("input_tokens", 0)),
            output_tokens=int(attributes.get("output_tokens", 0)),
            cache_read_tokens=int(attributes.get("cache_read_tokens", 0)),
            cost_usd=float(attributes.get("cost_usd", 0)),
            duration_ms=int(attributes.get("duration_ms", 0)),
        )
        self._api_requests.append(api_request)

    def get_errors(self) -> list[str]:
        """Get list of parsing errors."""
        return self._errors.copy()

    def has_errors(self) -> bool:
        """Check if there are parsing errors."""
        return len(self._errors) > 0
# mypy: disable-error-code="no-untyped-def,no-any-return,var-annotated,assignment"
