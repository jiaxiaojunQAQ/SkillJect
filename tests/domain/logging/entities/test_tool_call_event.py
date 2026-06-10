from datetime import datetime

from src.domain.logging.entities.tool_call_event import ToolCallEvent


def test_tool_call_event_accepts_stream_json_fields():
    event = ToolCallEvent(
        span_id="span-1",
        parent_span_id=None,
        tool_name="Bash",
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        parameters={"command": "ls"},
        result={"stdout": "a\nb"},
        status="success",
        tool_use_id="toolu_01ABC",
        cache_read_input_tokens=10,
        cache_creation_input_tokens=20,
        output_tokens=30,
    )
    assert event.tool_use_id == "toolu_01ABC"
    assert event.cache_read_input_tokens == 10
    assert event.cache_creation_input_tokens == 20
    assert event.output_tokens == 30


def test_tool_call_event_backward_compatible_without_new_fields():
    event = ToolCallEvent(
        span_id="span-1",
        parent_span_id=None,
        tool_name="Bash",
        start_time=datetime(2026, 1, 1),
        end_time=None,
        parameters={},
        result=None,
        status="pending",
    )
    assert event.tool_use_id is None
    assert event.cache_read_input_tokens is None
    assert event.cache_creation_input_tokens is None
    assert event.output_tokens is None
