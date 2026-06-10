"""Thin adapter: OpenClaw collector dict → CollectedTrace.

Converts the dict returned by
``OpenClawJsonLogCollector.collect_from_execution(...)`` into a
``CollectedTrace`` so that the Task-6 plumbing
(``_save_test_detail`` → ``RawTraceWriter.write()`` + judge metadata
projections) works uniformly for OpenClaw runs.

The existing ``OpenClawJsonLogCollector`` is left untouched; this module
is purely additive.

Key pairing logic
-----------------
* ``collected["metadata"]["all_events"]`` contains the full normalized
  event list produced by ``_normalize_events``.
* Nodes whose ``kind == "tool_call"`` carry ``tool_call_id`` (= the
  content-block ``id`` field, e.g. ``"call_1"``).
* Nodes whose ``kind == "tool_result"`` carry ``tool_call_id`` (=
  ``toolCallId`` from the toolResult message), which matches the
  tool_call's ``tool_call_id``.
* We build a ``{tool_call_id: tool_result_node}`` index from the
  normalized events and use it to pair each tool_call with its result.

Bash-equivalent tool names
--------------------------
Any tool whose canonical name (lowercased) is in
``BASH_EQUIVALENT_TOOLS`` is extracted as a ``CommandRecord``.
``exec`` maps to ``"bash"`` via the collector's ``CANONICAL_TOOL_NAME_MAP``;
the raw name ``exec``/``bash``/``shell`` are also accepted as a defensive
fallback.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.domain.logging.entities.tool_call_event import ToolCallEvent, ToolCallTrace
from src.domain.logging.value_objects.command_record import CommandRecord
from src.infrastructure.logging.collectors.claude_log_collector import CollectedTrace

# Canonical tool names (after CANONICAL_TOOL_NAME_MAP) that represent
# shell/bash command execution.
BASH_EQUIVALENT_TOOLS = {"bash", "exec", "shell"}


def _parse_ts(value: Any) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware datetime.

    Falls back to ``datetime.now(timezone.utc)`` on any failure.
    """
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def openclaw_dict_to_collected_trace(
    collected: dict[str, Any],
    session_jsonl_lines: list[dict[str, str]],
    stdout: str,
    stderr: str,
    test_id: str,
) -> CollectedTrace:
    """Convert a ``collect_from_execution`` result dict into a ``CollectedTrace``.

    Args:
        collected: Dict returned by
            ``OpenClawJsonLogCollector.collect_from_execution(...)``.
        session_jsonl_lines: Raw ``{"path": ..., "line": ...}`` entries fed
            to the collector.  The ``"line"`` values are joined verbatim to
            form ``stream_raw`` (the ``stream.jsonl`` file on disk).
        stdout: Raw stdout string from the execution result.
        stderr: Raw stderr string from the execution result.
        test_id: Test case identifier.

    Returns:
        A populated :class:`CollectedTrace`.
    """
    # --- stream_raw: verbatim session-jsonl content --------------------------
    stream_raw = "\n".join(
        entry["line"] for entry in session_jsonl_lines if entry.get("line")
    )

    # --- normalized events from collector metadata ---------------------------
    metadata = collected.get("metadata") or {}
    all_events: list[dict[str, Any]] = metadata.get("all_events") or []

    # Build a tool_call_id → tool_result_node index.
    tool_result_by_id: dict[str, dict[str, Any]] = {}
    for node in all_events:
        if node.get("kind") == "tool_result":
            tc_id = node.get("tool_call_id")
            if tc_id:
                tool_result_by_id[str(tc_id)] = node

    # --- build ToolCallTrace from tool_call nodes ----------------------------
    tool_call_nodes = [n for n in all_events if n.get("kind") == "tool_call"]

    events: dict[str, ToolCallEvent] = {}
    root_span_ids: list[str] = []
    commands: list[CommandRecord] = []
    total_duration_ms = 0

    for tc_node in tool_call_nodes:
        tool_call_id = tc_node.get("tool_call_id")
        span_id = str(tool_call_id) if tool_call_id else str(uuid.uuid4())

        parent_span_id: str | None = None  # OpenClaw JSON doesn't expose span parents

        tool_name_raw: str = tc_node.get("tool_name_raw", "unknown")
        tool_name_canonical: str = tc_node.get("tool_name_canonical", tool_name_raw.lower() or "unknown")
        parameters: dict[str, Any] = tc_node.get("parameters") or {}

        start_time = _parse_ts(tc_node.get("timestamp"))

        # Pair with matching tool_result
        matched_result: dict[str, Any] | None = None
        if tool_call_id:
            matched_result = tool_result_by_id.get(str(tool_call_id))

        end_time: datetime | None = None
        result_content: dict[str, Any] | None = None
        status = "pending"

        if matched_result is not None:
            end_time = _parse_ts(matched_result.get("timestamp"))
            # Guard against negative durations (clock skew in test fixtures)
            if end_time < start_time:
                end_time = start_time
            raw_result = matched_result.get("result")
            result_content = raw_result if isinstance(raw_result, dict) else (
                {"value": raw_result} if raw_result is not None else None
            )
            status = matched_result.get("status", "success")
        else:
            status = "pending"

        # Duration contribution
        if end_time is not None:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            total_duration_ms += max(duration_ms, 0)

        domain_event = ToolCallEvent(
            span_id=span_id,
            parent_span_id=parent_span_id,
            tool_name=tool_name_canonical,
            start_time=start_time,
            end_time=end_time,
            parameters=parameters,
            result=result_content,
            status=status,
            tool_use_id=str(tool_call_id) if tool_call_id else span_id,
            # OpenClaw session-jsonl carries no token counts
            cache_read_input_tokens=None,
            cache_creation_input_tokens=None,
            output_tokens=None,
        )
        events[span_id] = domain_event
        root_span_ids.append(span_id)

        # Extract CommandRecord for bash-equivalent tool calls
        effective_tool_name = tool_name_canonical.lower()
        if effective_tool_name in BASH_EQUIVALENT_TOOLS or tool_name_raw.lower() in BASH_EQUIVALENT_TOOLS:
            command_str = parameters.get("command")
            if isinstance(command_str, str):
                # Derive stdout/stderr from the matched result content list
                result_stdout = ""
                result_stderr = ""
                result_exit_code: int | None = None
                if matched_result is not None:
                    raw_result = matched_result.get("result") or {}
                    content_list = raw_result.get("content") if isinstance(raw_result, dict) else None
                    if isinstance(content_list, list):
                        text_parts = [
                            c["text"]
                            for c in content_list
                            if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
                        ]
                        result_stdout = "\n".join(text_parts)
                    # isError → treat as stderr
                    if status == "error":
                        result_stderr = result_stdout
                        result_stdout = ""

                commands.append(
                    CommandRecord(
                        tool_use_id=str(tool_call_id) if tool_call_id else span_id,
                        command=command_str,
                        cwd=None,
                        started_at=start_time.isoformat() if start_time else None,
                        ended_at=end_time.isoformat() if end_time else None,
                        exit_code=result_exit_code,
                        stdout=result_stdout,
                        stderr=result_stderr,
                        duration_ms=(
                            int((end_time - start_time).total_seconds() * 1000)
                            if end_time is not None
                            else None
                        ),
                    )
                )

    # --- build ToolCallTrace -------------------------------------------------
    tool_call_trace: ToolCallTrace | None = None
    if events:
        tool_call_trace = ToolCallTrace(
            test_id=test_id,
            events=events,
            root_span_ids=root_span_ids,
            total_calls=len(events),
            total_duration_ms=total_duration_ms,
        )

    # --- assistant text: concatenate text content from assistant messages ----
    assistant_text_parts: list[str] = []
    for node in all_events:
        if node.get("kind") == "message" and node.get("role") == "assistant":
            msg_data = node.get("data") or {}
            for content_block in msg_data.get("content") or []:
                if isinstance(content_block, dict) and content_block.get("type") == "text":
                    text = content_block.get("text", "")
                    if isinstance(text, str) and text:
                        assistant_text_parts.append(text)
    assistant_text = "\n".join(assistant_text_parts)

    return CollectedTrace(
        test_id=test_id,
        stream_raw=stream_raw,
        stdout=stdout,
        stderr=stderr,
        tool_call_trace=tool_call_trace,
        commands=commands,
        usage=[],  # OpenClaw session-jsonl carries no token usage
        assistant_text=assistant_text,
    )
