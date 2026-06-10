import json
from datetime import datetime, timezone
from pathlib import Path

from src.domain.logging.entities.tool_call_event import ToolCallEvent
from src.domain.logging.value_objects.command_record import CommandRecord
from src.domain.logging.value_objects.stream_usage import StreamUsage
from src.infrastructure.logging.persistence.raw_trace_writer import RawTraceWriter


def test_write_creates_full_raw_directory(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration_1"
    writer = RawTraceWriter(iteration_dir)

    writer.write(
        stream_raw='{"type":"result","usage":{}}\n',
        stdout="hello\n",
        stderr="warn\n",
        tool_calls=[
            ToolCallEvent(
                span_id="toolu_1",
                parent_span_id=None,
                tool_name="Bash",
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                parameters={"command": "ls"},
                result={"text": "a"},
                status="success",
                tool_use_id="toolu_1",
            )
        ],
        commands=[
            CommandRecord(
                tool_use_id="toolu_1",
                command="ls",
                cwd=None,
                started_at=None,
                ended_at=None,
                exit_code=None,
                stdout="a",
                stderr="",
                duration_ms=None,
            )
        ],
        usage=[
            StreamUsage(
                input_tokens=1,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
                output_tokens=1,
                kind="final",
            )
        ],
    )

    raw = iteration_dir / "raw"
    assert (raw / "stream.jsonl").read_text() == '{"type":"result","usage":{}}\n'
    assert (raw / "stdout.txt").read_text() == "hello\n"
    assert (raw / "stderr.txt").read_text() == "warn\n"

    tool_calls = json.loads((raw / "tool_calls.json").read_text())
    assert tool_calls[0]["tool_name"] == "Bash"
    assert tool_calls[0]["tool_use_id"] == "toolu_1"

    commands = json.loads((raw / "commands.json").read_text())
    assert commands[0]["command"] == "ls"

    usage = json.loads((raw / "usage.json").read_text())
    assert usage[0]["kind"] == "final"
