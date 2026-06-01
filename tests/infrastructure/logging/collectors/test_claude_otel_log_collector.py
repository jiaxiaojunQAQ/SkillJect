from types import SimpleNamespace

import pytest

from src.domain.testing.services.claude_test_runner import _MinimalClaudeConfig
from src.infrastructure.logging.collectors.claude_otel_log_collector import ClaudeOtelLogCollector


def _message(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


@pytest.mark.asyncio
async def test_collect_extracts_execution_logs_without_name_error() -> None:
    collector = ClaudeOtelLogCollector(config=_MinimalClaudeConfig(), strict_parsing=False)
    execution = SimpleNamespace(
        logs=SimpleNamespace(
            stdout=[_message("stdout line")],
            stderr=[_message("stderr line")],
        )
    )

    result = await collector.collect(execution=execution, agent=None)

    assert result["raw_stdout"] == ["stdout line"]
    assert result["raw_stderr"] == ["stderr line"]
    assert "metadata" in result


def test_extract_tool_parameters_handles_read_grep_and_skill_examples() -> None:
    collector = ClaudeOtelLogCollector(config=_MinimalClaudeConfig(), strict_parsing=False)

    read_params = collector._extract_tool_parameters(
        "Read",
        {"file_path": "/tmp/input.txt"},
    )
    grep_params = collector._extract_tool_parameters(
        "Grep",
        {"pattern": "secret", "path": "/workspace/project"},
    )
    skill_params = collector._extract_tool_parameters(
        "Skill",
        {"description": "Inspect project memory before editing"},
    )

    assert read_params["path"] == "/tmp/input.txt"
    assert grep_params["pattern"] == "secret"
    assert grep_params["path"] == "/workspace/project"
    assert skill_params["description"] == "Inspect project memory before editing"
