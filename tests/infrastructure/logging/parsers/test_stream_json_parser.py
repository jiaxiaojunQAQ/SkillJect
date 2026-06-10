from pathlib import Path

from src.infrastructure.logging.parsers.stream_json_parser import (
    StreamJsonParser,
    StreamJsonParseResult,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_simple_text_only_stream_yields_no_tool_calls_one_final_usage() -> None:
    raw = (FIXTURES / "claude_stream_simple.jsonl").read_text()
    parser = StreamJsonParser()
    result: StreamJsonParseResult = parser.parse(raw)
    assert result.tool_calls == []
    assert result.commands == []
    assert len(result.usage) == 2  # one turn + one final
    assert result.usage[-1].kind == "final"
    assert result.assistant_text == "Hello."


def test_stream_with_bash_extracts_tool_call_and_command_record() -> None:
    raw = (FIXTURES / "claude_stream_with_bash.jsonl").read_text()
    parser = StreamJsonParser()
    result = parser.parse(raw)

    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.tool_name == "Bash"
    assert tc.tool_use_id == "toolu_01"
    assert tc.parameters == {"command": "ls -la", "description": "list"}
    assert tc.result is not None
    assert tc.status == "success"
    assert tc.cache_read_input_tokens == 10
    assert tc.cache_creation_input_tokens == 5

    assert len(result.commands) == 1
    cmd = result.commands[0]
    assert cmd.command == "ls -la"
    assert cmd.tool_use_id == "toolu_01"
    assert "total 0" in cmd.stdout

    assert result.assistant_text == "Listing files.\nDone."


def test_malformed_lines_are_skipped_not_raised() -> None:
    bad = '{"type":"assistant"}\nnot-json-at-all\n{"type":"result","usage":{}}\n'
    parser = StreamJsonParser()
    result = parser.parse(bad)
    assert result.tool_calls == []
    assert result.usage[-1].kind == "final"


def test_non_bash_tool_use_does_not_emit_command_record() -> None:
    raw = (
        '{"type":"assistant","message":{"content":'
        '[{"type":"tool_use","id":"toolu_2","name":"Read","input":{"file_path":"/etc/hosts"}}],'
        '"usage":{"input_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":1}}}\n'
        '{"type":"user","message":{"content":'
        '[{"type":"tool_result","tool_use_id":"toolu_2","content":[{"type":"text","text":"127.0.0.1 localhost"}],"is_error":false}]}}\n'
        '{"type":"result","usage":{}}\n'
    )
    result = StreamJsonParser().parse(raw)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "Read"
    assert result.commands == []


def test_tool_use_without_tool_result_remains_pending() -> None:
    raw = (
        '{"type":"assistant","message":{"content":'
        '[{"type":"tool_use","id":"toolu_3","name":"Bash","input":{"command":"sleep 999"}}],'
        '"usage":{"input_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":1}}}\n'
        '{"type":"result","usage":{}}\n'
    )
    result = StreamJsonParser().parse(raw)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].status == "pending"
    assert result.tool_calls[0].result is None
    assert result.commands == []


def test_bash_tool_result_with_is_error_routes_text_to_stderr() -> None:
    raw = (
        '{"type":"assistant","message":{"content":'
        '[{"type":"tool_use","id":"toolu_4","name":"Bash","input":{"command":"false"}}],'
        '"usage":{"input_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":1}}}\n'
        '{"type":"user","message":{"content":'
        '[{"type":"tool_result","tool_use_id":"toolu_4","content":[{"type":"text","text":"exit 1"}],"is_error":true}]}}\n'
        '{"type":"result","usage":{}}\n'
    )
    result = StreamJsonParser().parse(raw)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].status == "error"
    assert len(result.commands) == 1
    assert result.commands[0].stdout == ""
    assert result.commands[0].stderr == "exit 1"


def test_recognized_events_counts_stream_json_envelopes() -> None:
    raw = (
        '{"type":"system","subtype":"init"}\n'
        '{"type":"assistant","message":{"content":[{"type":"text","text":"hi"}],"usage":{}}}\n'
        '{"type":"result","usage":{}}\n'
    )
    result = StreamJsonParser().parse(raw)
    assert result.recognized_events == 3


def test_otel_telemetry_stdout_recognizes_no_stream_json_events() -> None:
    # node util.inspect-formatted OTEL telemetry (unquoted keys, `undefined`) is
    # not valid JSON, so every line is skipped and nothing is recognized.
    otel = (
        "{\n"
        "  body: 'claude_code.tool_result',\n"
        "  traceId: undefined,\n"
        "  attributes: { tool_name: 'Bash', success: 'true' }\n"
        "}\n"
    )
    result = StreamJsonParser().parse(otel)
    assert result.recognized_events == 0
    assert result.commands == []
    assert result.tool_calls == []


def test_valid_json_without_known_type_is_not_recognized() -> None:
    result = StreamJsonParser().parse('{"foo":"bar"}\n{"type":"unknown_kind"}\n')
    assert result.recognized_events == 0
