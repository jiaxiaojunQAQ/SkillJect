from types import SimpleNamespace

import pytest

from src.infrastructure.logging.collectors.openclaw_json_log_collector import (
    OpenClawJsonLogCollector,
)


def _message(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


@pytest.mark.asyncio
async def test_collect_uses_session_jsonl_as_primary_source() -> None:
    collector = OpenClawJsonLogCollector(
        config=SimpleNamespace(name="openclaw"),
        strict_parsing=False,
    )
    execution = SimpleNamespace(
        test_id="openclaw-test",
        logs=SimpleNamespace(stdout=[_message("ignored stdout")], stderr=[]),
    )
    session_jsonl_lines = [
        {
            "path": "/home/node/.openclaw/sessions/s1.jsonl",
            "line": '{"type":"message","id":"m1","timestamp":"2026-04-08T10:00:00Z","message":{"role":"assistant","content":[{"type":"toolCall","id":"call_1","name":"exec","arguments":{"command":"ls -la"}}]}}',
        },
        {
            "path": "/home/node/.openclaw/agents/main/sessions/a1.jsonl",
            "line": '{"type":"message","id":"m2","parentId":"m1","timestamp":"2026-04-08T10:00:01Z","message":{"role":"toolResult","toolCallId":"call_1","toolName":"exec","isError":false,"content":[{"type":"text","text":"ok"}]}}',
        },
        {
            "path": "/home/node/.openclaw/agents/main/sessions/a1.jsonl",
            "line": '{"type":"message","id":"m3","parentId":"m2","timestamp":"2026-04-08T10:00:02Z","message":{"role":"assistant","content":[{"type":"toolCall","id":"call_2","name":"read","arguments":{"path":"/tmp/a.txt"}}]}}',
        },
        {
            "path": "/home/node/.openclaw/agents/main/sessions/a1.jsonl",
            "line": '{"type":"message","id":"m4","parentId":"m3","timestamp":"2026-04-08T10:00:03Z","message":{"role":"toolResult","toolCallId":"call_2","toolName":"read","isError":false,"content":[{"type":"text","text":"content"}]}}',
        },
    ]

    result = await collector.collect_from_execution(
        execution=execution,
        agent=None,
        session_jsonl_lines=session_jsonl_lines,
    )

    assert result["metadata"]["log_source"] == "openclaw_session_jsonl"
    assert result["metadata"]["session_entries"] == 4
    assert len(result["events"]) == 4
    assert result["metadata"]["tool_call_count"] == 2
    assert result["metadata"]["canonical_tool_breakdown"]["bash"] == 1
    assert result["metadata"]["canonical_tool_breakdown"]["read"] == 1
    assert len(result["metadata"]["all_events"]) >= 8
    assert len(result["metadata"]["execution_chain"]["nodes"]) == len(result["metadata"]["all_events"])
    tool_result_edges = [
        edge for edge in result["metadata"]["execution_chain"]["edges"]
        if edge.get("type") == "tool_result"
    ]
    assert len(tool_result_edges) == 2
    assert "behavior_summary" not in result["metadata"]
    assert "behavior_trace" not in result["metadata"]
