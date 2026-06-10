"""Claude Code stream-json log collector.

Collects and parses Claude CLI stream-json output (produced by
``claude --output-format stream-json --include-partial-messages --verbose -p …``)
into a structured CollectedTrace.

Public API:
    ClaudeLogCollector          – main collector class
    CollectedTrace              – result dataclass
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.domain.logging.entities.tool_call_event import ToolCallEvent, ToolCallTrace
from src.domain.logging.value_objects.command_record import CommandRecord
from src.domain.logging.value_objects.stream_usage import StreamUsage
from src.infrastructure.logging.parsers.stream_json_parser import StreamJsonParser

logger = logging.getLogger(__name__)


@dataclass
class CollectedTrace:
    """Structured result of one Claude agent execution collected via stream-json.

    Attributes:
        test_id: Identifier for the test case.
        stream_raw: The raw stdout – this IS the stream-json byte sequence.
        stdout: Full stdout (same as stream_raw for Claude stream-json runs).
        stderr: Full stderr.
        tool_call_trace: Parsed tool call trace, or None if no tool calls were made.
        commands: Bash CommandRecord objects extracted from the stream.
        usage: Token-usage entries extracted from the stream.
        assistant_text: Concatenated assistant text blocks from the stream.
    """

    test_id: str
    stream_raw: str
    stdout: str
    stderr: str
    tool_call_trace: ToolCallTrace | None
    commands: list[CommandRecord] = field(default_factory=list)
    usage: list[StreamUsage] = field(default_factory=list)
    assistant_text: str = ""

    @property
    def tool_call_events(self) -> list[ToolCallEvent]:
        """Flat list of ToolCallEvents in iteration order (empty if no trace)."""
        if self.tool_call_trace is None:
            return []
        return list(self.tool_call_trace.events.values())


class ClaudeLogCollector:
    """Collect and parse Claude CLI stream-json execution output.

    Usage::

        collector = ClaudeLogCollector()
        trace = collector.collect(exec_result, test_id="t-1")

    The collector is stateless across calls; a new parser instance is used
    on every ``collect()`` invocation (unless a shared parser is injected
    via the constructor for testability).

    Args:
        parser: Optional pre-constructed :class:`StreamJsonParser` to use.
                Defaults to a fresh ``StreamJsonParser()`` per call when
                ``None`` is passed (i.e. the default).
    """

    def __init__(self, parser: StreamJsonParser | None = None) -> None:
        self._parser = parser

    def collect(self, exec_result: Any, *, test_id: str) -> CollectedTrace:
        """Collect logs from an execution result and return a CollectedTrace.

        Args:
            exec_result: Execution result object produced by the sandbox runner.
                         Expected to expose ``exec_result.logs.stdout`` and
                         ``exec_result.logs.stderr`` – each a list of message
                         objects with a ``.text`` attribute.
            test_id: Identifier for the test case.

        Returns:
            :class:`CollectedTrace` populated from the parsed stream.
        """
        # --- extract raw text from execution result --------------------------
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        if hasattr(exec_result, "logs"):
            logs = exec_result.logs
            if hasattr(logs, "stdout"):
                for msg in logs.stdout:
                    if hasattr(msg, "text"):
                        stdout_lines.append(msg.text)
            if hasattr(logs, "stderr"):
                for msg in logs.stderr:
                    if hasattr(msg, "text"):
                        stderr_lines.append(msg.text)

        stdout = "\n".join(stdout_lines)
        stderr = "\n".join(stderr_lines)

        # --- parse the stream-json payload -----------------------------------
        parser = self._parser if self._parser is not None else StreamJsonParser()
        parsed = parser.parse(stdout)

        # --- guard against degraded trace capture ----------------------------
        # If stdout has content but no stream-json envelope was recognized, the
        # agent did not emit `--output-format stream-json` (commonly OTEL
        # telemetry from a CLI version/env mismatch). Commands and attack-success
        # detection silently degrade in that case, so warn loudly instead.
        if stdout.strip() and parsed.recognized_events == 0:
            logger.warning(
                "Claude trace capture degraded for test_id=%s: stdout has %d non-blank "
                "lines but no stream-json events were recognized. The agent likely did "
                "not run with `--output-format stream-json` (e.g. OTEL telemetry from a "
                "CLI version/env mismatch). executed_commands and attack-success "
                "detection will be unreliable for this run.",
                test_id,
                len([ln for ln in stdout.splitlines() if ln.strip()]),
            )

        # --- build ToolCallTrace if any tool calls were found ----------------
        trace: ToolCallTrace | None = None
        if parsed.tool_calls:
            events: dict[str, ToolCallEvent] = {}
            root_span_ids: list[str] = []
            for event in parsed.tool_calls:
                events[event.span_id] = event
                root_span_ids.append(event.span_id)

            trace = ToolCallTrace(
                test_id=test_id,
                events=events,
                root_span_ids=root_span_ids,
                total_calls=len(events),
                total_duration_ms=0,
            )

        return CollectedTrace(
            test_id=test_id,
            stream_raw=stdout,
            stdout=stdout,
            stderr=stderr,
            tool_call_trace=trace,
            commands=parsed.commands,
            usage=parsed.usage,
            assistant_text=parsed.assistant_text,
        )

    def __repr__(self) -> str:
        return "ClaudeLogCollector()"
