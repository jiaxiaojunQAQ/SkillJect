# mypy: disable-error-code="no-untyped-def,attr-defined"
from types import SimpleNamespace

import pytest

from src.domain.testing.services.sandbox_test_runner import SandboxTestRunner
from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig


def _build_config() -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "skillject",
            },
            "execution": {
                "sandbox": {
                    "domain": "localhost:8080",
                    "image": "claude_code:latest",
                }
            },
        }
    )


@pytest.mark.asyncio
async def test_create_sandbox_passes_config_to_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = SandboxTestRunner(_build_config())
    captured: dict[str, object] = {}

    async def fake_create(*, image, connection_config, **kwargs):
        captured["image"] = image
        captured["domain"] = connection_config.domain
        return SimpleNamespace(sandbox_id="sandbox-123")

    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.Sandbox.create",
        fake_create,
    )

    sandbox = await runner._create_sandbox()

    assert sandbox.sandbox_id == "sandbox-123"
    assert captured["image"] == "claude_code:latest"
    assert captured["domain"] == "localhost:8080"
