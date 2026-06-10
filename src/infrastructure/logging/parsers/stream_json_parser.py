"""Parse Claude CLI stream-json output into structured ToolCallEvent / CommandRecord / StreamUsage.

Input: raw stdout from `claude --output-format stream-json --include-partial-messages --verbose`.
Output: StreamJsonParseResult with non-lossy projections of the stream.

Reference: /home/liaojie/my_os/20_code/autoResearch/experiment-runner/scripts/lib/stream_filter.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from src.domain.logging.entities.tool_call_event import ToolCallEvent
from src.domain.logging.value_objects.command_record import CommandRecord
from src.domain.logging.value_objects.stream_usage import StreamUsage

# Top-level `type` values emitted by `claude --output-format stream-json`.
# Used only to tell genuine stream-json apart from foreign stdout (e.g. OTEL
# telemetry), not to gate parsing.
_RECOGNIZED_EVENT_TYPES = frozenset({"system", "assistant", "user", "result", "stream_event"})


@dataclass
class StreamJsonParseResult:
    """Non-lossy projection of one Claude stream-json transcript.

    Produced by StreamJsonParser; raw bytes are preserved separately by
    RawTraceWriter. This is the parser-layer result; see CollectedTrace
    (collector layer) for the runtime-wrapped form.
    """
    tool_calls: list[ToolCallEvent] = field(default_factory=list)
    commands: list[CommandRecord] = field(default_factory=list)
    usage: list[StreamUsage] = field(default_factory=list)
    assistant_text: str = ""
    # Number of recognized stream-json envelopes seen (system/assistant/user/
    # result/stream_event). Zero on non-empty input means stdout was not
    # stream-json at all — e.g. OTEL telemetry from a CLI version/env mismatch —
    # so downstream command/attack detection is unreliable.
    recognized_events: int = 0


class StreamJsonParser:
    """Stateless-by-call NDJSON dispatcher for Claude stream-json events."""

    def parse(self, raw: str) -> StreamJsonParseResult:
        result = StreamJsonParseResult()
        pending: dict[str, ToolCallEvent] = {}
        text_buffer: list[str] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            typ = obj.get("type")
            if typ in _RECOGNIZED_EVENT_TYPES:
                result.recognized_events += 1
            if typ == "assistant":
                msg = obj.get("message") or {}
                for block in msg.get("content", []):
                    btype = block.get("type")
                    if btype == "text":
                        text = block.get("text", "")
                        if text:
                            text_buffer.append(text)
                    elif btype == "tool_use":
                        event = self._build_tool_use_event(block, msg.get("usage") or {})
                        result.tool_calls.append(event)
                        if event.tool_use_id:
                            pending[event.tool_use_id] = event
                    # thinking blocks: preserved in raw stream.jsonl but not projected
                usage = msg.get("usage") or {}
                # With --include-partial-messages the wrapping `assistant` message
                # carries zeroed usage; the real per-turn usage arrives on the
                # message_delta stream event (handled below). Skip all-zero usage
                # here to avoid polluting the list / double counting.
                if usage and any(
                    int(usage.get(k) or 0)
                    for k in (
                        "input_tokens",
                        "output_tokens",
                        "cache_read_input_tokens",
                        "cache_creation_input_tokens",
                    )
                ):
                    result.usage.append(self._make_usage(usage, kind="turn"))
            elif typ == "stream_event":
                # Real per-turn token usage is delivered on the message_delta
                # stream event (Claude CLI --include-partial-messages mode).
                ev = obj.get("event") or {}
                if ev.get("type") == "message_delta":
                    usage = ev.get("usage") or {}
                    if usage:
                        result.usage.append(self._make_usage(usage, kind="turn"))
            elif typ == "user":
                msg = obj.get("message") or {}
                for block in msg.get("content", []):
                    if block.get("type") == "tool_result":
                        self._apply_tool_result(block, pending, result)
            elif typ == "result":
                # result-turn emits a final usage entry even when usage is empty,
                # so downstream always has exactly one kind="final" marker per stream.
                usage = obj.get("usage") or {}
                result.usage.append(self._make_usage(usage, kind="final"))

        result.assistant_text = "\n".join(text_buffer)
        return result

    def _build_tool_use_event(self, block: dict, usage: dict) -> ToolCallEvent:  # type: ignore[type-arg]
        tool_use_id = block.get("id") or ""
        return ToolCallEvent(
            span_id=tool_use_id or f"toolu_unknown_{id(block)}",
            parent_span_id=None,
            tool_name=block.get("name", "?"),
            start_time=datetime.now(timezone.utc),  # proxy: stream-json carries no timestamps
            end_time=None,
            parameters=dict(block.get("input") or {}),
            result=None,
            status="pending",
            tool_use_id=tool_use_id or None,
            cache_read_input_tokens=usage.get("cache_read_input_tokens"),
            cache_creation_input_tokens=usage.get("cache_creation_input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )

    def _apply_tool_result(
        self,
        block: dict,  # type: ignore[type-arg]
        pending: dict[str, ToolCallEvent],
        result: StreamJsonParseResult,
    ) -> None:
        tool_use_id = block.get("tool_use_id") or ""
        content = block.get("content")
        is_error = bool(block.get("is_error"))
        flat_text = self._flatten_tool_result_content(content)
        event = pending.get(tool_use_id)
        if event is not None:
            event.result = {"content": content, "text": flat_text, "is_error": is_error}
            event.status = "error" if is_error else "success"
            event.end_time = datetime.now(timezone.utc)
            if event.tool_name == "Bash":
                command = (event.parameters or {}).get("command")
                if isinstance(command, str):
                    result.commands.append(
                        CommandRecord(
                            tool_use_id=tool_use_id,
                            command=command,
                            cwd=None,
                            started_at=event.start_time.isoformat() if event.start_time else None,
                            ended_at=event.end_time.isoformat() if event.end_time else None,
                            exit_code=None,
                            stdout=flat_text if not is_error else "",
                            stderr=flat_text if is_error else "",
                            duration_ms=None,
                        )
                    )

    @staticmethod
    def _flatten_tool_result_content(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "".join(parts)
        return ""

    @staticmethod
    def _make_usage(usage: dict, *, kind: Literal["turn", "final"]) -> StreamUsage:  # type: ignore[type-arg]
        return StreamUsage(
            input_tokens=int(usage.get("input_tokens") or 0),
            cache_read_input_tokens=int(usage.get("cache_read_input_tokens") or 0),
            cache_creation_input_tokens=int(usage.get("cache_creation_input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            kind=kind,
        )
