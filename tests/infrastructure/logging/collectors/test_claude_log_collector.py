"""Tests for ClaudeLogCollector (stream-json based)."""
import logging
from types import SimpleNamespace

from src.infrastructure.logging.collectors.claude_log_collector import ClaudeLogCollector


def _msg(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def test_collector_parses_stream_json_into_tool_call_trace() -> None:
    stdout = [
        _msg('{"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_1","name":"Bash","input":{"command":"id"}}],"usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}}'),
        _msg('{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"toolu_1","content":[{"type":"text","text":"uid=0(root)"}],"is_error":false}]}}'),
        _msg('{"type":"result","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}'),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=stdout, stderr=[]))

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-1")

    assert out.tool_call_trace is not None
    assert out.tool_call_trace.total_calls == 1
    ev = next(iter(out.tool_call_trace.events.values()))
    assert ev.tool_name == "Bash"
    assert ev.status == "success"
    assert out.commands[0].command == "id"
    assert out.stream_raw.startswith('{"type":"assistant"')


def test_collector_no_tool_calls_returns_none_trace() -> None:
    stdout = [
        _msg('{"type":"assistant","message":{"content":[{"type":"text","text":"Hello world"}],"usage":{"input_tokens":5,"output_tokens":3,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}}'),
        _msg('{"type":"result","usage":{"input_tokens":5,"output_tokens":3,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}'),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=stdout, stderr=[]))

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-2")

    assert out.tool_call_trace is None
    assert out.commands == []
    assert out.assistant_text == "Hello world"


def test_collector_extracts_stderr() -> None:
    stderr = [_msg("some error"), _msg("another error")]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=stderr))

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-3")

    assert out.stderr == "some error\nanother error"
    assert out.tool_call_trace is None


def test_collector_stream_raw_equals_stdout() -> None:
    stdout = [
        _msg('{"type":"result","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}'),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=stdout, stderr=[]))

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-4")

    assert out.stream_raw == out.stdout


def test_collector_handles_missing_logs_attribute() -> None:
    result = SimpleNamespace()  # no .logs attribute

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-5")

    assert out.stdout == ""
    assert out.stderr == ""
    assert out.tool_call_trace is None


def test_collector_usage_entries_populated() -> None:
    stdout = [
        _msg('{"type":"assistant","message":{"content":[{"type":"text","text":"hi"}],"usage":{"input_tokens":10,"output_tokens":5,"cache_read_input_tokens":2,"cache_creation_input_tokens":0}}}'),
        _msg('{"type":"result","usage":{"input_tokens":10,"output_tokens":5,"cache_read_input_tokens":2,"cache_creation_input_tokens":0}}'),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=stdout, stderr=[]))

    collector = ClaudeLogCollector()
    out = collector.collect(result, test_id="t-6")

    assert len(out.usage) == 2  # one turn + one final
    kinds = {u.kind for u in out.usage}
    assert kinds == {"turn", "final"}


def test_collector_warns_when_stdout_is_otel_not_stream_json(caplog) -> None:
    # OTEL telemetry (node util.inspect format) instead of stream-json — the
    # exact failure mode from a CLI version/env mismatch.
    otel = [
        _msg("{"),
        _msg("  body: 'claude_code.tool_result',"),
        _msg("  attributes: { tool_name: 'Bash', success: 'true' }"),
        _msg("}"),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=otel, stderr=[]))

    collector = ClaudeLogCollector()
    with caplog.at_level(logging.WARNING):
        out = collector.collect(result, test_id="t-otel")

    assert out.commands == []
    assert out.tool_call_trace is None
    assert any("trace capture degraded" in r.message for r in caplog.records)


def test_collector_does_not_warn_on_valid_stream_json(caplog) -> None:
    stdout = [
        _msg('{"type":"result","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}'),
    ]
    result = SimpleNamespace(logs=SimpleNamespace(stdout=stdout, stderr=[]))

    collector = ClaudeLogCollector()
    with caplog.at_level(logging.WARNING):
        collector.collect(result, test_id="t-ok")

    assert not any("trace capture degraded" in r.message for r in caplog.records)


def test_collector_does_not_warn_on_empty_stdout(caplog) -> None:
    result = SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]))

    collector = ClaudeLogCollector()
    with caplog.at_level(logging.WARNING):
        collector.collect(result, test_id="t-empty")

    assert not any("trace capture degraded" in r.message for r in caplog.records)
