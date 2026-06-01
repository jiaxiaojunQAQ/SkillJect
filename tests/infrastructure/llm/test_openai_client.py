# mypy: disable-error-code="no-untyped-def,assignment"
from types import SimpleNamespace

import pytest

from src.infrastructure.llm.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_call_openai_accepts_plain_string_response() -> None:
    class _StubCompletions:
        async def create(self, **kwargs):
            return "plain text from relay"

    client = OpenAIClient.__new__(OpenAIClient)
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=_StubCompletions()))
    client._config = SimpleNamespace(model="gpt-4o", max_tokens=1024, temperature=0.1)

    content = await OpenAIClient._call_openai(client, "hello")
    assert content == "plain text from relay"
