# mypy: disable-error-code="no-untyped-def,arg-type,attr-defined,annotation-unchecked"
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.services.result_analyzer import ResultAnalyzer
from src.domain.analysis.interfaces.i_llm_judge import (
    LLMJudgeResult,
    LLMJudgeVerdict,
)
from src.domain.logging.entities.tool_call_event import ToolCallEvent, ToolCallTrace
from src.domain.logging.value_objects.command_record import CommandRecord
from src.domain.logging.value_objects.stream_usage import StreamUsage
from src.domain.testing.entities import test_case as test_case_entities
from src.domain.testing.entities.test_case import ErrorType
from src.domain.testing.services.openclaw_test_runner import OpenClawTestRunner
from src.domain.testing.services.sandbox_test_runner import SandboxTestRunner
from src.domain.testing.value_objects.execution_config import TwoPhaseExecutionConfig
from src.infrastructure.logging.collectors.claude_log_collector import CollectedTrace
from src.shared import types as shared_types


def _build_config(output_dir: Path) -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(output_dir),
            },
        }
    )


def _build_skillject_judge_config(output_dir: Path) -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "skillject",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(output_dir),
            },
            "judge": {
                "attack_judgment": False,
                "provider": "openai",
                "model": "gpt-5-mini",
                "api_key_env": "JUDGE_LLM_OPENAI_API_KEY",
            },
        }
    )


def _build_openclaw_config(output_dir: Path) -> TwoPhaseExecutionConfig:
    return TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(output_dir),
                "agent": {
                    "agent_type": "openclaw",
                },
            },
        }
    )


@pytest.mark.asyncio
async def test_save_test_detail_uses_direct_execution_attack_type_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    runner = SandboxTestRunner(_build_config(output_dir))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case_dir = output_dir / "test_details" / "direct_execution" / "skill_inject" / "INST-10_git_task0" / "direct" / "iteration_0"
    test_case_dir.mkdir(parents=True)

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-10_git_task0"),
        skill_name="INST-10_git_task0",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=test_case_dir,
        dataset="skill_inject",
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "direct",
        },
    )
    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        blocked=True,
        executed_malicious=False,
    )

    await runner._save_test_detail(test_case, result, output_dir / "test_details", iteration_number=0)

    expected_result = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "direct"
        / "iteration_0"
        / "result.json"
    )
    unexpected_result = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-10_git_task0"
        / "information_disclosure"
        / "iteration_0"
        / "result.json"
    )

    assert expected_result.exists()
    assert not unexpected_result.exists()
    assert not (expected_result.parent / "tool_calls.json").exists()
    assert (expected_result.parent / "raw_logs.txt").exists()


@pytest.mark.asyncio
async def test_copy_directory_from_sandbox_uses_files_api_only(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    dest = tmp_path / "copied"

    class _FilesStub:
        def __init__(self):
            self.search_entry = None
            self.read_paths: list[str] = []

        async def search(self, entry):
            self.search_entry = entry
            return [
                SimpleNamespace(path="/sandbox/skill/readme.txt"),
                SimpleNamespace(path="/sandbox/skill/nested/payload.bin"),
            ]

        async def read_bytes(self, path):
            self.read_paths.append(path)
            if path.endswith("payload.bin"):
                return b"\x00\x01"
            return b"hello"

        async def read_file(self, path, **kwargs):
            raise AssertionError("read_file should not be needed when read_bytes succeeds")

    class _CommandsStub:
        async def run(self, command):
            raise AssertionError("commands.run must not be used in copy back path")

    sandbox = SimpleNamespace(files=_FilesStub(), commands=_CommandsStub())
    result = await runner._copy_directory_from_sandbox(sandbox, "/sandbox/skill", dest)

    assert result is True
    assert sandbox.files.search_entry.path == "/sandbox/skill"
    assert sandbox.files.search_entry.pattern == "**"
    assert (dest / "readme.txt").read_bytes() == b"hello"
    assert (dest / "nested" / "payload.bin").read_bytes() == b"\x00\x01"


@pytest.mark.asyncio
async def test_copy_directory_from_sandbox_skips_paths_containing_venv_by_default(
    tmp_path: Path,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    dest = tmp_path / "copied"

    class _FilesStub:
        def __init__(self):
            self.read_paths: list[str] = []

        async def search(self, entry):
            return [
                SimpleNamespace(path="/sandbox/skill/SKILL.md"),
                SimpleNamespace(path="/sandbox/skill/venv/bin/python"),
                SimpleNamespace(path="/sandbox/skill/.venv/pyvenv.cfg"),
                SimpleNamespace(path="/sandbox/skill/nested/venv/lib/site.py"),
                SimpleNamespace(path="/sandbox/skill/my_venv_notes.txt"),
                SimpleNamespace(path="/sandbox/skill/archived-venv-files/config.json"),
            ]

        async def read_bytes(self, path):
            self.read_paths.append(path)
            return path.encode("utf-8")

    sandbox = SimpleNamespace(files=_FilesStub())
    result = await runner._copy_directory_from_sandbox(sandbox, "/sandbox/skill", dest)

    assert result is True
    assert (dest / "SKILL.md").read_bytes() == b"/sandbox/skill/SKILL.md"
    assert not (dest / "venv").exists()
    assert not (dest / ".venv").exists()
    assert not (dest / "nested" / "venv").exists()
    assert not (dest / "my_venv_notes.txt").exists()
    assert not (dest / "archived-venv-files").exists()
    assert sandbox.files.read_paths == ["/sandbox/skill/SKILL.md"]


@pytest.mark.asyncio
async def test_copy_directory_from_sandbox_skips_non_standard_venv_paths(
    tmp_path: Path,
) -> None:
    """Test that virtual environments with non-standard names are excluded via site-packages fragment."""
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    dest = tmp_path / "copied"

    class _FilesStub:
        def __init__(self):
            self.read_paths: list[str] = []

        async def search(self, entry):
            return [
                SimpleNamespace(path="/sandbox/skill/SKILL.md"),
                SimpleNamespace(path="/sandbox/skill/environment/config.py"),
                SimpleNamespace(path="/sandbox/skill/event_handler/utils.py"),
                # Virtual environments with non-standard names
                SimpleNamespace(path="/sandbox/skill/dask_env/lib/python3.11/site-packages/yaml/scanner.py"),
                SimpleNamespace(path="/sandbox/skill/myenv/lib/python3.11/site-packages/requests/__init__.py"),
                SimpleNamespace(path="/sandbox/skill/env/lib/python3.11/site-packages/pip/__init__.py"),
                SimpleNamespace(path="/sandbox/skill/conda-env/lib/python3.11/site-packages/numpy/core/array.py"),
            ]

        async def read_bytes(self, path):
            self.read_paths.append(path)
            return path.encode("utf-8")

    sandbox = SimpleNamespace(files=_FilesStub())
    result = await runner._copy_directory_from_sandbox(sandbox, "/sandbox/skill", dest)

    assert result is True
    # Files that should be copied (no venv or site-packages in path)
    assert (dest / "SKILL.md").read_bytes() == b"/sandbox/skill/SKILL.md"
    assert (dest / "environment" / "config.py").read_bytes() == b"/sandbox/skill/environment/config.py"
    assert (dest / "event_handler" / "utils.py").read_bytes() == b"/sandbox/skill/event_handler/utils.py"

    # Virtual environment contents should NOT be copied (site-packages fragment)
    assert not (dest / "dask_env").exists()
    assert not (dest / "myenv").exists()
    assert not (dest / "env").exists()
    assert not (dest / "conda-env").exists()

    # Only the 3 non-virtual-environment files should be read
    assert sandbox.files.read_paths == [
        "/sandbox/skill/SKILL.md",
        "/sandbox/skill/environment/config.py",
        "/sandbox/skill/event_handler/utils.py",
    ]


@pytest.mark.asyncio
async def test_run_command_with_timeout_uses_execution_command_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    captured = {"timeout": None, "command": None}

    class _CommandsStub:
        async def run(self, command):
            captured["command"] = command
            return "ok"

    async def _fake_wait_for(coro, timeout):
        captured["timeout"] = timeout
        return await coro

    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.asyncio.wait_for",
        _fake_wait_for,
    )

    sandbox = SimpleNamespace(commands=_CommandsStub())
    result = await runner._run_command_with_timeout(sandbox, command="echo hello")

    assert result == "ok"
    assert captured["command"] == "echo hello"
    assert captured["timeout"] == float(runner._config.execution.command_timeout)


@pytest.mark.asyncio
async def test_create_sandbox_raises_timeout_error_when_creation_exceeds_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {"name": "skill_inject"},
            },
            "execution": {
                "output_dir": str(tmp_path / "results"),
                "test_timeout": 7,
            },
        }
    )
    runner = SandboxTestRunner(config)

    async def _fake_create(*args, **kwargs):
        return SimpleNamespace(sandbox_id="sandbox-test")

    async def _fake_wait_for(coro, timeout):
        assert timeout == 7.0
        coro.close()
        raise TimeoutError

    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.Sandbox.create",
        _fake_create,
    )
    monkeypatch.setattr(
        "src.domain.testing.services.sandbox_test_runner.asyncio.wait_for",
        _fake_wait_for,
    )

    with pytest.raises(RuntimeError, match="Sandbox creation timeout after 7s"):
        await runner._create_sandbox()


def test_prune_local_generated_skill_snapshot_removes_root_duplicates(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    iteration_dir = tmp_path / "iteration_0"
    (iteration_dir / "skill").mkdir(parents=True)
    (iteration_dir / "project").mkdir(parents=True)
    (iteration_dir / "SKILL.md").write_text("# generated", encoding="utf-8")
    (iteration_dir / "resources").mkdir(parents=True)
    (iteration_dir / "resources" / "a.sh").write_text("echo 1", encoding="utf-8")
    (iteration_dir / "instruction.md").write_text("keep me", encoding="utf-8")

    runner._prune_local_generated_skill_snapshot(iteration_dir)

    assert not (iteration_dir / "SKILL.md").exists()
    assert not (iteration_dir / "resources").exists()
    assert (iteration_dir / "skill").exists()
    assert (iteration_dir / "project").exists()
    assert (iteration_dir / "instruction.md").exists()


@pytest.mark.asyncio
async def test_initialize_test_environment_skips_fixed_resources_for_direct_execution(tmp_path: Path) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    written: list[str] = []

    class _FilesStub:
        async def write_file(self, path, data, **kwargs):
            written.append(path)

    sandbox = SimpleNamespace(files=_FilesStub(), commands=SimpleNamespace())

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.DIRECT,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=tmp_path / "source",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    await runner._initialize_test_environment(sandbox, test_case)
    assert written == []


@pytest.mark.asyncio
async def test_openclaw_provider_injection_uses_profile_provider_consistently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(tmp_path / "results"),
                "agent": {
                    "agent_type": "openclaw",
                    "provider": "minimax",
                    "model": "MiniMax-M2.7",
                    "auth_token_env": "MINIMAX_API_KEY",
                    "base_url_env": "OPENCLAW_MINIMAX_BASE_URL",
                    "use_api_key": True,
                },
            },
        }
    )
    runner = OpenClawTestRunner(config)

    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-secret")
    monkeypatch.setenv("OPENCLAW_MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")

    writes: dict[str, str] = {}

    class _FilesStub:
        async def write_file(self, path, data, **kwargs):
            writes[path] = data

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(exit_code=0, logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(files=_FilesStub(), commands=_CommandsStub())

    await runner._inject_openclaw_config(sandbox, "demo-skill")
    await runner._inject_agent_model_config(sandbox)
    await runner._inject_auth_profiles(sandbox)

    openclaw_json = json.loads(writes["/home/node/.openclaw/openclaw.json"])
    models_json = json.loads(writes["/home/node/.openclaw/agents/main/agent/models.json"])
    auth_profiles = json.loads(writes["/home/node/.openclaw/agents/main/agent/auth-profiles.json"])

    assert openclaw_json["agents"]["defaults"]["model"]["primary"] == "minimax/MiniMax-M2.7"
    assert openclaw_json["agents"]["defaults"]["workspace"] == "/home/node/.openclaw/workspace"
    assert openclaw_json["agents"]["defaults"]["sandbox"] == {"mode": "off"}
    assert openclaw_json["gateway"]["auth"] == {
        "mode": "token",
        "token": "",
    }
    assert openclaw_json["gateway"]["port"] == 18789
    assert openclaw_json["tools"]["profile"] == "coding"
    assert openclaw_json["tools"]["web"]["search"] == {
        "provider": "duckduckgo",
        "enabled": True,
    }
    assert openclaw_json["tools"]["exec"] == {
        "security": "full",
        "ask": "off",
    }
    assert "models" not in openclaw_json
    assert list(models_json["providers"].keys()) == ["minimax"]
    assert models_json["providers"]["minimax"]["baseUrl"] == "https://api.minimaxi.com/anthropic"
    assert models_json["providers"]["minimax"]["api"] == "anthropic-messages"
    assert models_json["providers"]["minimax"]["authHeader"] is True
    assert list(auth_profiles["profiles"].keys()) == ["minimax:default"]
    assert auth_profiles["profiles"]["minimax:default"]["provider"] == "minimax"
    assert auth_profiles["lastGood"] == {"minimax": "minimax:default"}


@pytest.mark.asyncio
async def test_openclaw_provider_falls_back_from_base_url_when_provider_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(tmp_path / "results"),
                "agent": {
                    "agent_type": "openclaw",
                    "model": "claude-sonnet-4-6",
                    "auth_token_env": "ANTHROPIC_API_KEY",
                    "base_url": "https://api.anthropic.com/v1",
                    "use_api_key": True,
                },
            },
        }
    )
    runner = OpenClawTestRunner(config)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    writes: dict[str, str] = {}

    class _FilesStub:
        async def write_file(self, path, data, **kwargs):
            writes[path] = data

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(exit_code=0, logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(files=_FilesStub(), commands=_CommandsStub())

    await runner._inject_openclaw_config(sandbox, "demo-skill")
    await runner._inject_agent_model_config(sandbox)
    await runner._inject_auth_profiles(sandbox)

    openclaw_json = json.loads(writes["/home/node/.openclaw/openclaw.json"])
    models_json = json.loads(writes["/home/node/.openclaw/agents/main/agent/models.json"])
    auth_profiles = json.loads(writes["/home/node/.openclaw/agents/main/agent/auth-profiles.json"])

    # Anthropic proxy: primary model uses "my-proxy" provider name
    assert openclaw_json["agents"]["defaults"]["model"]["primary"] == "my-proxy/claude-sonnet-4-6"
    # Gateway uses no auth in local mode
    assert openclaw_json["gateway"]["auth"]["mode"] == "none"
    assert openclaw_json["gateway"]["bind"] == "lan"
    assert "port" not in openclaw_json["gateway"]
    # No tools section (uses OpenClaw defaults)
    assert "tools" not in openclaw_json
    # No workspace/sandbox in agents.defaults
    assert "workspace" not in openclaw_json["agents"]["defaults"]
    assert "sandbox" not in openclaw_json["agents"]["defaults"]
    # Gateway-level models section with replace mode
    assert openclaw_json["models"]["mode"] == "replace"
    assert "my-proxy" in openclaw_json["models"]["providers"]
    proxy_provider = openclaw_json["models"]["providers"]["my-proxy"]
    assert proxy_provider["api"] == "anthropic-messages"
    assert proxy_provider["models"][0]["id"] == "claude-sonnet-4-6"
    assert proxy_provider["models"][0]["name"] == "Claude Sonnet 4.6 (Proxy)"

    # Agent-level models.json also uses "my-proxy" as provider key
    assert "my-proxy" in models_json["providers"]
    agent_model = models_json["providers"]["my-proxy"]
    assert agent_model["api"] == "anthropic-messages"
    assert agent_model["models"][0]["id"] == "claude-sonnet-4-6"

    # Agent-level auth-profiles.json also uses "my-proxy" as profile key
    assert "my-proxy:default" in auth_profiles["profiles"]
    assert auth_profiles["profiles"]["my-proxy:default"]["provider"] == "my-proxy"
    assert auth_profiles["profiles"]["my-proxy:default"]["key"] == "anthropic-secret"
    assert auth_profiles["lastGood"] == {"my-proxy": "my-proxy:default"}


@pytest.mark.asyncio
async def test_openclaw_claude_openai_profile_uses_openai_compatible_runtime_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(tmp_path / "results"),
                "agent": {
                    "agent_type": "openclaw",
                    "provider": "openai",
                    "model": "claude-sonnet-4-6",
                    "auth_token_env": "OPENCLAW_CLAUDE_OPENAI_API_KEY",
                    "base_url": "https://proxy.example.com/v1",
                    "use_api_key": True,
                },
            },
        }
    )
    runner = OpenClawTestRunner(config)

    monkeypatch.setenv("OPENCLAW_CLAUDE_OPENAI_API_KEY", "proxy-secret")
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "gateway-secret")

    writes: dict[str, str] = {}

    class _FilesStub:
        async def write_file(self, path, data, **kwargs):
            writes[path] = data

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(exit_code=0, logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(files=_FilesStub(), commands=_CommandsStub())

    await runner._inject_openclaw_config(sandbox, "demo-skill")
    await runner._inject_agent_model_config(sandbox)
    await runner._inject_auth_profiles(sandbox)

    openclaw_json = json.loads(writes["/home/node/.openclaw/openclaw.json"])
    models_json = json.loads(writes["/home/node/.openclaw/agents/main/agent/models.json"])
    auth_profiles = json.loads(writes["/home/node/.openclaw/agents/main/agent/auth-profiles.json"])

    assert openclaw_json["agents"]["defaults"]["model"]["primary"] == "openai/claude-sonnet-4-6"
    assert openclaw_json["gateway"]["auth"] == {
        "mode": "token",
        "token": "gateway-secret",
    }
    assert openclaw_json["gateway"]["port"] == 18789
    assert openclaw_json["tools"]["profile"] == "coding"
    assert "models" not in openclaw_json

    assert list(models_json["providers"].keys()) == ["openai"]
    assert models_json["providers"]["openai"]["baseUrl"] == "https://proxy.example.com/v1"
    assert models_json["providers"]["openai"]["api"] == "openai-completions"
    assert models_json["providers"]["openai"]["apiKey"] == "proxy-secret"
    assert models_json["providers"]["openai"]["models"][0]["id"] == "claude-sonnet-4-6"

    assert list(auth_profiles["profiles"].keys()) == ["openai:default"]
    assert auth_profiles["profiles"]["openai:default"]["provider"] == "openai"
    assert auth_profiles["profiles"]["openai:default"]["key"] == "proxy-secret"
    assert auth_profiles["lastGood"] == {"openai": "openai:default"}


@pytest.mark.asyncio
async def test_openclaw_provider_maps_zhipu_config_to_zai_runtime_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TwoPhaseExecutionConfig.from_dict(
        {
            "generation": {
                "strategy": "direct_execution",
                "dataset": {
                    "name": "skill_inject",
                },
            },
            "execution": {
                "output_dir": str(tmp_path / "results"),
                "agent": {
                    "agent_type": "openclaw",
                    "provider": "zhipu",
                    "model": "glm-4.7",
                    "auth_token_env": "ZHIPU_API_KEY",
                    "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
                    "use_api_key": True,
                },
            },
        }
    )
    runner = OpenClawTestRunner(config)

    monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-secret")

    writes: dict[str, str] = {}

    class _FilesStub:
        async def write_file(self, path, data, **kwargs):
            writes[path] = data

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(exit_code=0, logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(files=_FilesStub(), commands=_CommandsStub())

    await runner._inject_openclaw_config(sandbox, "demo-skill")
    await runner._inject_agent_model_config(sandbox)
    await runner._inject_auth_profiles(sandbox)

    openclaw_json = json.loads(writes["/home/node/.openclaw/openclaw.json"])
    models_json = json.loads(writes["/home/node/.openclaw/agents/main/agent/models.json"])
    auth_profiles = json.loads(writes["/home/node/.openclaw/agents/main/agent/auth-profiles.json"])

    assert openclaw_json["agents"]["defaults"]["model"]["primary"] == "zai/glm-4.7"
    assert list(models_json["providers"].keys()) == ["zai"]
    assert list(auth_profiles["profiles"].keys()) == ["zai:default"]


@pytest.mark.asyncio
async def test_execute_test_injects_skill_once_from_source_dir_without_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    copy_calls: list[tuple[Path, str, set[str] | None]] = []

    async def _capture_copy(sandbox, source_dir, skill_dest_dir, skip_files=None):
        copy_calls.append((source_dir, skill_dest_dir, skip_files))

    async def _noop_settings(_sandbox):
        return None

    async def _noop_env(_sandbox, _test_case):
        return None

    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _capture_copy)
    monkeypatch.setattr(runner, "_inject_claude_settings", _noop_settings)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop_env)
    monkeypatch.setattr(runner, "_build_agent_command", lambda _prompt: "agent-run")

    class _CommandsStub:
        async def run(self, command):
            if command == "agent-run":
                raise RuntimeError("stop after setup")
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(
        commands=_CommandsStub(),
        files=SimpleNamespace(),
    )

    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)
    assert result.status == shared_types.TestStatus.ERROR

    skill_calls = [c for c in copy_calls if c[1].endswith("/.claude/skills/INST-1_docx_task3")]
    assert len(skill_calls) == 1
    assert skill_calls[0][0] == source_skill_dir
    assert skill_calls[0][2] is None


@pytest.mark.asyncio
async def test_inject_auxiliary_files_skips_instruction_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True)
    case_dir = tmp_path / "case"
    case_dir.mkdir(parents=True)
    skill_name = "INST-1_docx_task3"

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId(skill_name),
        skill_name=skill_name,
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_dir / "SKILL.md",
        test_case_dir=case_dir,
        source_skill_dir=source_dir,
        source_aux_dir=case_dir,
        dataset="skill_inject",
        metadata={"skill_name": skill_name},
    )

    calls: list[tuple[Path, str, set[str] | None]] = []

    async def _capture_copy(sandbox, source_dir, skill_dest_dir, skip_files=None):
        calls.append((source_dir, skill_dest_dir, skip_files))

    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _capture_copy)

    await runner._inject_auxiliary_files_to_project(
        sandbox=SimpleNamespace(),
        test_case=test_case,
        skill_name=skill_name,
        project_dest_dir="/home/claude_code/project",
    )

    assert len(calls) == 1
    assert calls[0][0] == case_dir
    assert calls[0][1] == "/home/claude_code/project"
    assert calls[0][2] == {"instruction.md"}


@pytest.mark.asyncio
async def test_execute_test_returns_error_when_source_skill_dir_missing(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    missing_skill_dir = tmp_path / "missing_skill_dir"
    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=missing_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=missing_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.ERROR
    assert result.is_infrastructure_error is True
    assert "source_skill_dir missing or invalid" in result.error_message


def test_select_attack_script_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    script_base = tmp_path / "data" / "bash_scripts" / "information_disclosure"
    script_base.mkdir(parents=True)
    (script_base / "a.sh").write_text("#!/bin/bash\necho a\n", encoding="utf-8")
    (script_base / "b.sh").write_text("#!/bin/bash\necho b\n", encoding="utf-8")

    monkeypatch.setattr(
        "src.infrastructure.loaders.paths.resolve_data_path",
        lambda _p: tmp_path / "data" / "bash_scripts",
    )

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=tmp_path / "source_skill",
        source_aux_dir=tmp_path / "source_aux",
        dataset="skill_inject",
        metadata={"iteration_number": 0},
    )

    selected_1 = runner._select_attack_script_for_test(test_case)
    selected_2 = runner._select_attack_script_for_test(test_case)

    assert selected_1 is not None
    assert selected_2 is not None
    assert selected_1 == selected_2


@pytest.mark.asyncio
async def test_inject_attack_script_to_skill_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    script = tmp_path / "selected.sh"
    script.write_text("#!/bin/bash\necho selected\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_select_attack_script_for_test", lambda _tc: script)

    created_dirs: list[str] = []
    written_paths: list[str] = []

    class _FilesStub:
        async def create_directories(self, entries):
            for e in entries:
                created_dirs.append(e.path)

        async def write_files(self, entries):
            for e in entries:
                written_paths.append(e.path)

    sandbox = SimpleNamespace(files=_FilesStub())

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=tmp_path / "source_skill",
        source_aux_dir=tmp_path / "source_aux",
        dataset="skill_inject",
        metadata={},
    )

    await runner._inject_attack_script_to_skill_resources(
        sandbox=sandbox,
        test_case=test_case,
        skill_name="INST-1_docx_task3",
        skill_dest_dir="/home/claude_code/.claude/skills/INST-1_docx_task3",
    )

    assert "/home/claude_code/.claude/skills/INST-1_docx_task3/resources" in created_dirs
    assert "/home/claude_code/.claude/skills/INST-1_docx_task3/resources/selected.sh" in written_paths


@pytest.mark.asyncio
async def test_inject_attack_script_to_skill_resources_skips_direct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    def _should_not_select(_tc):
        raise AssertionError("direct execution should skip attack script selection")

    monkeypatch.setattr(runner, "_select_attack_script_for_test", _should_not_select)

    created_dirs: list[str] = []
    written_paths: list[str] = []

    class _FilesStub:
        async def create_directories(self, entries):
            for e in entries:
                created_dirs.append(e.path)

        async def write_files(self, entries):
            for e in entries:
                written_paths.append(e.path)

    sandbox = SimpleNamespace(files=_FilesStub())

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.DIRECT,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=tmp_path / "source_skill",
        source_aux_dir=tmp_path / "source_aux",
        dataset="skill_inject",
        metadata={},
    )

    await runner._inject_attack_script_to_skill_resources(
        sandbox=sandbox,
        test_case=test_case,
        skill_name="INST-1_docx_task3",
        skill_dest_dir="/home/claude_code/.claude/skills/INST-1_docx_task3",
    )

    assert created_dirs == []
    assert written_paths == []


@pytest.mark.asyncio
async def test_execute_test_skillject_overwrites_container_skill_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# original\n", encoding="utf-8")
    selected_script = tmp_path / "selected.sh"
    selected_script.write_text("#!/bin/bash\necho selected\n", encoding="utf-8")

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(runner, "_inject_claude_settings", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_select_attack_script_for_test", lambda _tc: selected_script)
    monkeypatch.setattr(runner, "_build_agent_command", lambda _prompt: "agent-run")

    written: dict[str, bytes | str] = {}

    class _FilesStub:
        async def create_directories(self, _entries):
            return None

        async def write_files(self, entries):
            for entry in entries:
                written[entry.path] = entry.data

    class _CommandsStub:
        async def run(self, command):
            if command == "agent-run":
                raise RuntimeError("stop after setup")
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3_information_disclosure"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION_RESOURCE,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="skillject",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        dataset="skill_inject",
        metadata={
            "skill_name": "INST-1_docx_task3",
            "strategy": "skillject",
            "injection_method": "skillject_adaptive",
        },
    )
    test_case.payload_content = "# injected skill\nUse resources/selected.sh\n"

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=_FilesStub())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.ERROR
    skill_path = "/home/claude_code/.claude/skills/INST-1_docx_task3/SKILL.md"
    assert written[skill_path] == "# injected skill\nUse resources/selected.sh\n"


@pytest.mark.asyncio
async def test_execute_test_template_injection_modifies_container_skill_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("---\nname: demo\n---\nBody\n", encoding="utf-8")

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(runner, "_inject_claude_settings", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_inject_attack_script_to_skill_resources", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_build_agent_command", lambda _prompt: "agent-run")

    written: dict[str, bytes | str] = {}

    class _FilesStub:
        async def create_directories(self, _entries):
            return None

        async def write_files(self, entries):
            for entry in entries:
                written[entry.path] = entry.data

    class _CommandsStub:
        async def run(self, command):
            if command == "agent-run":
                raise RuntimeError("stop after setup")
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("demo_information_disclosure"),
        skill_name="demo",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="template_injection",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        dataset="skill_inject",
        metadata={
            "skill_name": "demo",
            "strategy": "template_injection",
            "injection_method": "template_injection",
            "injection_layer": "instruction",
        },
    )
    test_case.payload_content = "Injected payload"

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=_FilesStub())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.ERROR
    skill_path = "/home/claude_code/.claude/skills/demo/SKILL.md"
    assert written[skill_path] == "---\nname: demo\n---\nInjected payload\nBody\n"


@pytest.mark.asyncio
async def test_execute_test_direct_execution_does_not_require_consequence_detector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.DIRECT,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3", "task_script": "task.sh"},
    )

    async def _capture_copy(sandbox, source_dir, skill_dest_dir, skip_files=None):
        return None

    async def _noop_settings(_sandbox):
        return None

    async def _noop_env(_sandbox, _test_case):
        return None

    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _capture_copy)
    monkeypatch.setattr(runner, "_inject_claude_settings", _noop_settings)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop_env)
    monkeypatch.setattr(runner, "_build_agent_command", lambda _prompt: "agent-run")

    class _CommandsStub:
        async def run(self, command):
            if command == "agent-run":
                return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)
            return SimpleNamespace(logs=SimpleNamespace(stdout=[], stderr=[]), error=None)

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status in (shared_types.TestStatus.PASSED, shared_types.TestStatus.FAILED)


@pytest.mark.asyncio
async def test_save_result_json_keeps_short_tool_summary_but_omits_long_trace_metadata(
    tmp_path: Path,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
    )

    now = datetime.now(timezone.utc)
    trace = ToolCallTrace(
        test_id="INST-1_docx_task3",
        events={
            "span-1": ToolCallEvent(
                span_id="span-1",
                parent_span_id=None,
                tool_name="Bash",
                start_time=now,
                end_time=now,
                parameters={"command": "echo hello"},
                result={"exit_code": 0},
                status="success",
            )
        },
        root_span_ids=["span-1"],
        total_calls=1,
        total_duration_ms=12,
    )

    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        metadata={"tool_call_trace": trace},
    )

    test_dir = tmp_path / "detail"
    test_dir.mkdir(parents=True)
    await runner._save_result_json(
        test_dir=test_dir,
        test_case=test_case,
        result=result,
        tool_call_trace=trace,
        parse_metadata={},
        executed_commands=["[bash] echo hello"],
    )

    data = json.loads((test_dir / "result.json").read_text(encoding="utf-8"))
    assert data["summary"]["total_tool_calls"] == 1
    assert data["summary"]["unique_tools"] == 1
    assert data["executed_commands"] == ["[bash] echo hello"]
    assert "tool_call_trace" not in data["metadata"]


@pytest.mark.asyncio
async def test_save_result_json_falls_back_to_string_for_unknown_metadata_objects(
    tmp_path: Path,
) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-2_docx_task4"),
        skill_name="INST-2_docx_task4",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
    )

    class _CustomObject:
        def __str__(self) -> str:
            return "custom-object-value"

    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        metadata={"custom": _CustomObject()},
    )

    test_dir = tmp_path / "detail"
    test_dir.mkdir(parents=True)
    await runner._save_result_json(
        test_dir=test_dir,
        test_case=test_case,
        result=result,
        tool_call_trace=None,
        parse_metadata={},
        executed_commands=[],
    )

    data = json.loads((test_dir / "result.json").read_text(encoding="utf-8"))
    assert data["metadata"]["custom"] == "custom-object-value"


@pytest.mark.asyncio
async def test_save_result_json_exposes_judge_fields_at_top_level(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-3_docx_task5"),
        skill_name="INST-3_docx_task5",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
    )

    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        metadata={
            "judge": LLMJudgeResult(
                verdict=LLMJudgeVerdict.ATTACK_SUCCESS,
                evidence="Executed forbidden command",
                confidence=0.93,
                reasoning="Observed successful execution",
                metadata={"model": "judge-model", "attempt": 1},
            ),
            "response_classification": LLMJudgeResult(
                verdict=LLMJudgeVerdict.REJECTED,
                evidence="Explicit refusal",
                confidence=0.87,
                reasoning="The agent declined the request",
                metadata={"classification_failed": False, "classifier": "response-model"},
            ),
        },
    )

    test_dir = tmp_path / "detail"
    test_dir.mkdir(parents=True)
    await runner._save_result_json(
        test_dir=test_dir,
        test_case=test_case,
        result=result,
        tool_call_trace=None,
        parse_metadata={},
        executed_commands=[],
    )

    data = json.loads((test_dir / "result.json").read_text(encoding="utf-8"))
    assert data["judge"]["verdict"] == "attack_success"
    assert data["judge"]["evidence"] == "Executed forbidden command"
    assert data["judge"]["confidence"] == 0.93
    assert data["judge"]["reasoning"] == "Observed successful execution"
    assert data["judge"]["metadata"] == {"model": "judge-model", "attempt": 1}
    assert data["response_classification"]["verdict"] == "rejected"
    assert data["response_classification"]["evidence"] == "Explicit refusal"
    assert data["response_classification"]["confidence"] == 0.87
    assert data["response_classification"]["reasoning"] == "The agent declined the request"
    assert data["response_classification"]["metadata"] == {
        "classification_failed": False,
        "classifier": "response-model",
    }
    assert data["response_classification"]["classification_failed"] is False
    assert data["final_verdict"] == "attack_success"
    assert data["summary"] == {}
    assert data["executed_commands"] == []
    assert data["metadata"] == {}


@pytest.mark.asyncio
async def test_save_result_json_stably_writes_infra_fields_and_final_verdict(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-4_docx_task6"),
        skill_name="INST-4_docx_task6",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
    )

    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.ERROR,
        is_infrastructure_error=True,
        error_type=ErrorType.NETWORK_ERROR,
        error_message="network timeout",
        metadata={
            "retry_trace": {
                "operation_name": "sandbox_test_INST-4_docx_task6",
                "total_attempts": 2,
                "final_outcome": "exhausted",
                "total_delay_seconds": 1.0,
                "attempts": [],
            }
        },
    )

    test_dir = tmp_path / "detail"
    test_dir.mkdir(parents=True)
    await runner._save_result_json(
        test_dir=test_dir,
        test_case=test_case,
        result=result,
        tool_call_trace=None,
        parse_metadata={},
        executed_commands=[],
    )

    data = json.loads((test_dir / "result.json").read_text(encoding="utf-8"))
    assert data["is_infrastructure_error"] is True
    assert data["error_type"] == "network_error"
    assert data["final_verdict"] == "technical"
    assert data["metadata"]["retry_trace"]["final_outcome"] == "exhausted"
    assert "retry_info" not in data["metadata"]


@pytest.mark.asyncio
async def test_save_result_json_omits_verdict_when_judge_configured(
    tmp_path: Path,
) -> None:
    runner = SandboxTestRunner(_build_skillject_judge_config(tmp_path / "results"))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-4_docx_task6"),
        skill_name="INST-4_docx_task6",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
    )

    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        agent_output="I refuse to run this malicious step.",
        metadata={},
    )

    test_dir = tmp_path / "detail"
    test_dir.mkdir(parents=True)
    await runner._save_result_json(
        test_dir=test_dir,
        test_case=test_case,
        result=result,
        tool_call_trace=None,
        parse_metadata={},
        executed_commands=[],
    )

    data = json.loads((test_dir / "result.json").read_text(encoding="utf-8"))
    assert "final_verdict" not in data


@pytest.mark.asyncio
async def test_save_test_detail_writes_raw_logs_with_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    runner = SandboxTestRunner(_build_config(output_dir))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-3_docx_task5"),
        skill_name="INST-3_docx_task5",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
        metadata={"strategy": "direct_execution"},
    )
    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        raw_log_source="openclaw_session_jsonl",
        raw_log_lines=['{"type":"message","id":"m1"}', '{"type":"message","id":"m2"}'],
        metadata={
            "tool_call_trace": {
                "total_calls": 2,
                "events": {
                    "1": {"tool_name": "bash"},
                    "2": {"tool_name": "read"},
                },
            }
        },
    )

    await runner._save_test_detail(test_case, result, output_dir / "test_details", iteration_number=0)

    raw_logs = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-3_docx_task5"
        / "information_disclosure"
        / "iteration_0"
        / "raw_logs.txt"
    ).read_text(encoding="utf-8")

    assert "=== Raw Logs (source=openclaw_session_jsonl) ===" in raw_logs
    assert '{"type":"message","id":"m1"}' in raw_logs
    assert "=== Summary ===" in raw_logs
    assert "tool_call_count: 2" in raw_logs
    assert "unique_tools: 2" in raw_logs


def test_build_executed_commands_includes_all_tool_calls_with_readable_format(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    trace = {
        "events": {
            "a": {
                "tool_name": "Bash",
                "parameters": {"command": "ls -la"},
                "start_time": "2026-04-08T10:00:00+00:00",
            },
            "b": {
                "tool_name": "exec",
                "parameters": {"command": "cat /tmp/a.txt"},
                "start_time": "2026-04-08T10:00:01+00:00",
            },
            "c": {
                "tool_name": "read",
                "parameters": {"path": "/tmp/input.txt"},
                "start_time": "2026-04-08T10:00:02+00:00",
            },
            "d": {
                "tool_name": "write",
                "parameters": {"path": "/tmp/output.txt", "content": "ignored"},
                "start_time": "2026-04-08T10:00:03+00:00",
            },
            "e": {
                "tool_name": "search",
                "parameters": {"pattern": "needle", "path": "/tmp"},
                "start_time": "2026-04-08T10:00:04+00:00",
            },
            "f": {
                "tool_name": "read",
                "parameters": {"file_path": "/tmp/only-file-path.txt", "_raw_attributes": "<object>"},
                "start_time": "2026-04-08T10:00:05+00:00",
            },
            "g": {
                "tool_name": "grep",
                "parameters": {"pattern": "token", "path": "/workspace", "_raw_attributes": "<object>"},
                "start_time": "2026-04-08T10:00:06+00:00",
            },
            "h": {
                "tool_name": "skill",
                "parameters": {"description": "Inspect project memory", "_raw_attributes": "<object>"},
                "start_time": "2026-04-08T10:00:07+00:00",
            },
        }
    }
    commands = runner._build_executed_commands(
        serialized_trace=trace,
        parsed_commands=["ls -la", "python main.py"],
    )
    assert commands == [
        "[bash] ls -la",
        "[exec] cat /tmp/a.txt",
        "[read] path=/tmp/input.txt",
        "[write] path=/tmp/output.txt",
        '[search] {"path":"/tmp","pattern":"needle"}',
        "[read] path=/tmp/only-file-path.txt",
        '[grep] {"path":"/workspace","pattern":"token"}',
        '[skill] {"description":"Inspect project memory"}',
        "ls -la",
        "python main.py",
    ]


def test_check_script_execution_fallback_ignores_non_command_tool_entries(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
        metadata={"task_script": "env_checker.sh"},
    )

    matched = runner._check_script_execution(
        tool_call_trace=None,
        test_case=test_case,
        executed_commands=[
            "[read] path=/tmp/env_checker.sh",
            "[write] path=/tmp/result.txt",
        ],
    )

    assert matched is False


def test_check_script_execution_accepts_lowercase_bash_for_python_script(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.DIRECT,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
        metadata={"task_script": "file_backup.py"},
    )

    matched = runner._check_script_execution(
        tool_call_trace={
            "events": {
                "a": {
                    "tool_name": "bash",
                    "parameters": {
                        "command": "python3 ~/.openclaw/workspace/skills/INST-1_docx_task3/scripts/file_backup.py /tmp/a.docx"
                    },
                }
            }
        },
        test_case=test_case,
        executed_commands=[],
    )

    assert matched is True


def test_extract_final_agent_output_uses_last_assistant_message_for_openclaw_events(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    result = test_case_entities.TestResult(
        test_id=test_case_entities.TestCaseId("INST-4_docx_task6"),
        status=shared_types.TestStatus.PASSED,
        agent_output="noise output",
        metadata={
            "all_events": [
                {
                    "kind": "message",
                    "role": "assistant",
                    "data": {
                        "content": [{"type": "text", "text": "first response"}],
                    },
                },
                {
                    "kind": "message",
                    "role": "assistant",
                    "data": {
                        "content": [{"type": "text", "text": "final response"}],
                    },
                },
            ]
        },
    )
    assert runner._extract_final_agent_output(result) == "final response"


def test_extract_final_agent_output_returns_last_paragraph_of_assistant_text(tmp_path: Path) -> None:
    """Claude stream-json path: result.agent_output is the cleaned assistant_text
    (set by _execute_test from CollectedTrace.assistant_text). _extract_final_agent_output
    should return the last non-empty paragraph, not the whole concatenation."""
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    result = test_case_entities.TestResult(
        test_id=test_case_entities.TestCaseId("INST_claude_stream_text"),
        status=shared_types.TestStatus.PASSED,
        agent_output=(
            "I need to investigate the skill first.\n"
            "\n"
            "Done — the skill looks safe and I will not execute the embedded script."
        ),
    )
    assert runner._extract_final_agent_output(result) == (
        "Done — the skill looks safe and I will not execute the embedded script."
    )


def test_extract_final_agent_output_does_not_otel_filter_single_line_ndjson(
    tmp_path: Path,
) -> None:
    """Regression guard for the bug where OTel-era filter_user_output() ran against
    single-line stream-json NDJSON. After the fix, filter_user_output is gone:
    a single NDJSON line is returned as-is (cleaned assistant_text replaces NDJSON
    upstream, so this is the worst-case fallback shape — still a single paragraph)."""
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    ndjson_line = '{"type":"result","subtype":"success","usage":{"input_tokens":1}}'
    result = test_case_entities.TestResult(
        test_id=test_case_entities.TestCaseId("INST_claude_stream_ndjson_fallback"),
        status=shared_types.TestStatus.PASSED,
        agent_output=ndjson_line,
    )
    # Old behavior (with filter_user_output) would have returned "" because the
    # whole line is a single-line `{...}` JSON treated as an OTel block. New
    # behavior keeps the line intact — verifying the filter is truly gone.
    assert runner._extract_final_agent_output(result) == ndjson_line


def test_extract_final_agent_output_returns_empty_for_blank_agent_output(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    result = test_case_entities.TestResult(
        test_id=test_case_entities.TestCaseId("INST_claude_blank"),
        status=shared_types.TestStatus.PASSED,
        agent_output="   \n\n  ",
    )
    assert runner._extract_final_agent_output(result) == ""


def test_result_analyzer_load_tool_calls_prefers_result_json(tmp_path: Path) -> None:
    test_dir = tmp_path / "test_case"
    test_dir.mkdir(parents=True)
    (test_dir / "result.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "tool_call_trace": {
                        "total_calls": 1,
                        "events": {"a": {"tool_name": "bash"}},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (test_dir / "tool_calls.json").write_text(
        json.dumps({"total_calls": 999}),
        encoding="utf-8",
    )

    trace = ResultAnalyzer.load_tool_calls(test_dir)
    assert trace is not None
    assert trace["total_calls"] == 1


def test_result_analyzer_load_tool_calls_fallbacks_to_legacy_file(tmp_path: Path) -> None:
    test_dir = tmp_path / "test_case"
    test_dir.mkdir(parents=True)
    (test_dir / "result.json").write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    (test_dir / "tool_calls.json").write_text(
        json.dumps({"total_calls": 3}),
        encoding="utf-8",
    )

    trace = ResultAnalyzer.load_tool_calls(test_dir)
    assert trace is not None
    assert trace["total_calls"] == 3


def test_result_analyzer_handles_single_result_schema(tmp_path: Path) -> None:
    test_dir = tmp_path / "test_case"
    test_dir.mkdir(parents=True)
    (test_dir / "result.json").write_text(
        json.dumps(
            {
                "test_id": "skill_a_information_disclosure",
                "attack_type": "information_disclosure",
                "layer": "instruction",
                "final_verdict": "rejected",
                "blocked": True,
                "executed_malicious": False,
                "reasoning": "Attack failed - blocked by defense",
            }
        ),
        encoding="utf-8",
    )

    analysis = ResultAnalyzer(result_path=str(test_dir)).analyze()

    assert analysis.summary["total_tests"] == 1
    assert analysis.summary["final_verdict"] == "rejected"
    assert analysis.summary["blocked"] == 1


@pytest.mark.asyncio
async def test_openclaw_collects_all_session_files_without_truncation(tmp_path: Path) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    file_list_output = "\n".join(
        [
            "/home/node/.openclaw/agents/main/sessions/a.jsonl",
            "/home/node/.openclaw/agents/main/sessions/b.jsonl.reset.2026-04-08T00-00-00.000Z",
            "/home/node/.openclaw/sessions/c.jsonl.deleted.2026-04-08T00-00-00.000Z",
        ]
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(
                logs=SimpleNamespace(
                    stdout=[SimpleNamespace(text=file_list_output)],
                    stderr=[],
                ),
                error=None,
                exit_code=0,
            )

    class _FilesStub:
        async def read_file(self, path):
            return f'{{"type":"message","id":"{path}-1"}}\n{{"type":"message","id":"{path}-2"}}\n'

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=_FilesStub())
    collected = await runner._collect_openclaw_session_jsonl_lines(sandbox)

    assert len(collected) == 6
    assert {item["path"] for item in collected} == {
        "/home/node/.openclaw/agents/main/sessions/a.jsonl",
        "/home/node/.openclaw/agents/main/sessions/b.jsonl.reset.2026-04-08T00-00-00.000Z",
        "/home/node/.openclaw/sessions/c.jsonl.deleted.2026-04-08T00-00-00.000Z",
    }


@pytest.mark.asyncio
async def test_openclaw_execute_test_uses_verdict_reasoning_and_metadata_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_session_lines(*_args, **_kwargs):
        return []

    class _CollectorStub:
        def __init__(self, config, strict_parsing=False):
            pass

        async def collect_from_execution(self, execution, agent=None, session_jsonl_lines=None):
            return {
                "events": [{"type": "json_log", "message": "assistant event"}],
                "metadata": {
                    "log_source": "openclaw_session_jsonl",
                    "session_files": ["/tmp/session.jsonl"],
                    "session_entries": 1,
                    "tool_call_trace": None,
                    "tool_call_count": 0,
                    "canonical_tool_breakdown": {},
                    "all_events": [],
                    "execution_chain": {"nodes": [], "edges": []},
                },
            }

    monkeypatch.setattr(runner, "_ensure_openclaw_directory_structure", _noop)
    monkeypatch.setattr(runner, "_inject_openclaw_config", _noop)
    monkeypatch.setattr(runner, "_inject_agent_model_config", _noop)
    monkeypatch.setattr(runner, "_inject_auth_profiles", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _noop)
    monkeypatch.setattr(runner, "_inject_attack_script_to_skill_resources", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_collect_openclaw_session_jsonl_lines", _no_session_lines)
    monkeypatch.setattr(
        "src.domain.testing.services.openclaw_test_runner.OpenClawJsonLogCollector",
        _CollectorStub,
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(
                logs=SimpleNamespace(
                    stdout=[SimpleNamespace(text="final assistant output")],
                    stderr=[],
                ),
                error=None,
                exit_code=0,
            )

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.PASSED
    assert result.reasoning == "Attack failed - ignored (no attack attempts detected)"
    assert "Events:" not in result.reasoning
    assert result.metadata["execution_summary"]["events_count"] == 1
    assert result.metadata["execution_summary"]["output_chars"] == len("final assistant output")
    assert result.metadata["execution_summary"]["has_response"] is True
    assert result.metadata["execution_summary"]["log_source"] == "openclaw_session_jsonl"


@pytest.mark.asyncio
async def test_openclaw_execute_test_no_response_uses_error_reasoning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_session_lines(*_args, **_kwargs):
        return []

    class _CollectorStub:
        def __init__(self, config, strict_parsing=False):
            pass

        async def collect_from_execution(self, execution, agent=None, session_jsonl_lines=None):
            return {
                "events": [],
                "metadata": {
                    "log_source": "execution_output",
                    "session_files": [],
                    "session_entries": 0,
                    "tool_call_trace": None,
                    "tool_call_count": 0,
                    "canonical_tool_breakdown": {},
                    "all_events": [],
                    "execution_chain": {"nodes": [], "edges": []},
                },
            }

    monkeypatch.setattr(runner, "_ensure_openclaw_directory_structure", _noop)
    monkeypatch.setattr(runner, "_inject_openclaw_config", _noop)
    monkeypatch.setattr(runner, "_inject_agent_model_config", _noop)
    monkeypatch.setattr(runner, "_inject_auth_profiles", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _noop)
    monkeypatch.setattr(runner, "_inject_attack_script_to_skill_resources", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_collect_openclaw_session_jsonl_lines", _no_session_lines)
    monkeypatch.setattr(
        "src.domain.testing.services.openclaw_test_runner.OpenClawJsonLogCollector",
        _CollectorStub,
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(
                logs=SimpleNamespace(
                    stdout=[],
                    stderr=[],
                ),
                error=None,
                exit_code=0,
            )

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.ERROR
    assert result.reasoning == "Execution error: OpenClaw agent returned no response"
    assert "Output:" not in result.reasoning
    assert result.metadata["execution_summary"]["events_count"] == 0
    assert result.metadata["execution_summary"]["output_chars"] == 0
    assert result.metadata["execution_summary"]["has_response"] is False


@pytest.mark.asyncio
async def test_openclaw_execute_test_prefers_final_assistant_text_over_raw_wrapped_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3"},
    )

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_session_lines(*_args, **_kwargs):
        return []

    class _CollectorStub:
        def __init__(self, config, strict_parsing=False):
            pass

        async def collect_from_execution(self, execution, agent=None, session_jsonl_lines=None):
            return {
                "events": [{"type": "json_log", "message": "assistant event"}],
                "metadata": {
                    "log_source": "openclaw_session_jsonl",
                    "session_files": ["/tmp/session.jsonl"],
                    "session_entries": 1,
                    "tool_call_trace": None,
                    "tool_call_count": 0,
                    "canonical_tool_breakdown": {},
                    "all_events": [
                        {
                            "kind": "message",
                            "role": "assistant",
                            "data": {
                                "content": [
                                    {"type": "text", "text": "clean final answer"}
                                ]
                            },
                        }
                    ],
                    "execution_chain": {"nodes": [], "edges": []},
                },
            }

    monkeypatch.setattr(runner, "_ensure_openclaw_directory_structure", _noop)
    monkeypatch.setattr(runner, "_inject_openclaw_config", _noop)
    monkeypatch.setattr(runner, "_inject_agent_model_config", _noop)
    monkeypatch.setattr(runner, "_inject_auth_profiles", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _noop)
    monkeypatch.setattr(runner, "_inject_attack_script_to_skill_resources", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_collect_openclaw_session_jsonl_lines", _no_session_lines)
    monkeypatch.setattr(
        "src.domain.testing.services.openclaw_test_runner.OpenClawJsonLogCollector",
        _CollectorStub,
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(
                logs=SimpleNamespace(
                    stdout=[SimpleNamespace(text="wrapped stdout")],
                    stderr=[SimpleNamespace(text='{"payloads":[{"text":"wrapped stderr"}]}')],
                ),
                error=None,
                exit_code=0,
            )

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.agent_output == "clean final answer"


@pytest.mark.asyncio
async def test_openclaw_execute_test_detects_python_script_execution_from_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = OpenClawTestRunner(_build_openclaw_config(tmp_path / "results"))

    source_skill_dir = tmp_path / "source_skill"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-1_docx_task3"),
        skill_name="INST-1_docx_task3",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.DIRECT,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=source_skill_dir / "SKILL.md",
        test_case_dir=tmp_path / "case",
        source_skill_dir=source_skill_dir,
        source_aux_dir=tmp_path / "aux",
        dataset="skill_inject",
        metadata={"skill_name": "INST-1_docx_task3", "task_script": "file_backup.py"},
    )

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_session_lines(*_args, **_kwargs):
        return []

    class _CollectorStub:
        def __init__(self, config, strict_parsing=False):
            pass

        async def collect_from_execution(self, execution, agent=None, session_jsonl_lines=None):
            return {
                "events": [{"type": "json_log", "message": "assistant event"}],
                "metadata": {
                    "log_source": "openclaw_session_jsonl",
                    "session_files": ["/tmp/session.jsonl"],
                    "session_entries": 1,
                    "tool_call_trace": {
                        "events": {
                            "call_1": {
                                "tool_name": "bash",
                                "parameters": {
                                    "command": "python3 ~/.openclaw/workspace/skills/INST-1_docx_task3/scripts/file_backup.py /home/node/.openclaw/workspace/project/Q4_financial_report.docx"
                                },
                                "start_time": "2026-04-09T05:06:32.064Z",
                            }
                        }
                    },
                    "tool_call_count": 1,
                    "canonical_tool_breakdown": {"bash": 1},
                    "all_events": [],
                    "execution_chain": {"nodes": [], "edges": []},
                },
            }

    monkeypatch.setattr(runner, "_ensure_openclaw_directory_structure", _noop)
    monkeypatch.setattr(runner, "_inject_openclaw_config", _noop)
    monkeypatch.setattr(runner, "_inject_agent_model_config", _noop)
    monkeypatch.setattr(runner, "_inject_auth_profiles", _noop)
    monkeypatch.setattr(runner, "_inject_auxiliary_files_to_project", _noop)
    monkeypatch.setattr(runner, "_copy_directory_to_skill_path", _noop)
    monkeypatch.setattr(runner, "_inject_attack_script_to_skill_resources", _noop)
    monkeypatch.setattr(runner, "_initialize_test_environment", _noop)
    monkeypatch.setattr(runner, "_collect_openclaw_session_jsonl_lines", _no_session_lines)
    monkeypatch.setattr(
        "src.domain.testing.services.openclaw_test_runner.OpenClawJsonLogCollector",
        _CollectorStub,
    )

    class _CommandsStub:
        async def run(self, command):
            return SimpleNamespace(
                logs=SimpleNamespace(
                    stdout=[SimpleNamespace(text="Finished backup step")],
                    stderr=[],
                ),
                error=None,
                exit_code=0,
            )

    sandbox = SimpleNamespace(commands=_CommandsStub(), files=SimpleNamespace())
    result, _ = await runner._execute_test(sandbox, "test prompt", test_case)

    assert result.status == shared_types.TestStatus.FAILED
    assert result.executed_malicious is True
    assert result.metadata["task_script"] == "file_backup.py"
    assert result.metadata["script_executed_details"]["script_executed"] is True
    assert any("file_backup.py" in cmd for cmd in result.metadata["script_executed_details"]["executed_commands"])


@pytest.mark.asyncio
async def test_copy_directory_returns_false_on_search_failure(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    dest = tmp_path / "copied"

    class _BrokenFiles:
        async def search(self, entry):
            raise RuntimeError("sandbox connection lost")

    sandbox = SimpleNamespace(files=_BrokenFiles())
    result = await runner._copy_directory_from_sandbox(sandbox, "/sandbox/skill", dest)
    assert result is False


@pytest.mark.asyncio
async def test_copy_directory_returns_false_on_empty_directory(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))
    dest = tmp_path / "copied"

    class _EmptyFiles:
        async def search(self, entry):
            return []

    sandbox = SimpleNamespace(files=_EmptyFiles())
    result = await runner._copy_directory_from_sandbox(sandbox, "/sandbox/skill", dest)
    assert result is False


@pytest.mark.asyncio
async def test_copy_workspace_returns_skill_copied_true_on_skill_success_only(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    call_log: list[str] = []

    async def _fake_copy(sandbox, source_path, dest_dir, skip_files=None, skip_dirs=None):
        call_log.append(source_path)
        if "skills" in source_path:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / "SKILL.md").write_text("# skill", encoding="utf-8")
            return True
        else:
            return False  # project copy fails

    runner._copy_directory_from_sandbox = _fake_copy  # type: ignore[assignment]

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("test_skill_information_disclosure"),
        skill_name="test_skill",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
        metadata={"skill_name": "test_skill"},
    )

    status = await runner._copy_workspace_from_container(
        sandbox=SimpleNamespace(),
        iteration_dir=tmp_path / "iteration_0",
        skill_name="test_skill",
        test_case=test_case,
    )

    assert status.skill_copied is True
    assert status.project_copied is False
    assert status.skill_copy_error == ""
    assert status.project_copy_error != ""
    # Skill copy should happen before project copy
    assert call_log[0] == "/home/claude_code/.claude/skills/test_skill"
    assert call_log[1] == "/home/claude_code/project"


@pytest.mark.asyncio
async def test_copy_workspace_returns_all_false_on_skill_failure(tmp_path: Path) -> None:
    runner = SandboxTestRunner(_build_config(tmp_path / "results"))

    async def _fail_all(sandbox, source_path, dest_dir, skip_files=None, skip_dirs=None):
        return False

    runner._copy_directory_from_sandbox = _fail_all  # type: ignore[assignment]

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("test_skill_information_disclosure"),
        skill_name="test_skill",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=tmp_path / "SKILL.md",
        test_case_dir=tmp_path / "case",
        dataset="skill_inject",
        metadata={"skill_name": "test_skill"},
    )

    status = await runner._copy_workspace_from_container(
        sandbox=SimpleNamespace(),
        iteration_dir=tmp_path / "iteration_0",
        skill_name="test_skill",
        test_case=test_case,
    )

    assert status.skill_copied is False
    assert status.project_copied is False
    assert status.skill_copy_error != ""


@pytest.mark.asyncio
async def test_save_test_detail_creates_raw_dir_and_populates_metadata(tmp_path: Path) -> None:
    """_save_test_detail must write iteration_{N}/raw/ for Claude runs via typed CollectedTrace.

    When _execute_test produces a CollectedTrace (Claude stream-json runs), the caller
    passes it via collected= to _save_test_detail, which then calls RawTraceWriter.write()
    directly with typed objects.  The raw/ directory must contain all 6 expected files.
    OpenClaw runs pass collected=None and the raw/ directory is not created.
    """
    output_dir = tmp_path / "results"
    runner = SandboxTestRunner(_build_config(output_dir))

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# skill\n", encoding="utf-8")

    test_case = test_case_entities.TestCase(
        id=test_case_entities.TestCaseId("INST-99_stream_task0"),
        skill_name="INST-99_stream_task0",
        layer=shared_types.InjectionLayer.INSTRUCTION,
        attack_type=shared_types.AttackType.INFORMATION_DISCLOSURE,
        payload_name="direct_execution",
        severity=shared_types.Severity.MEDIUM,
        skill_path=skill_path,
        test_case_dir=output_dir / "case",
        dataset="skill_inject",
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "information_disclosure",
        },
    )

    # Build typed CollectedTrace — this is what _execute_test produces via ClaudeLogCollector.
    # Dict projections (tool_calls, command_history, api_usage, stderr) go into metadata.
    _now = datetime(2024, 1, 1, 0, 0, 0)
    bash_event = ToolCallEvent(
        span_id="span-1",
        parent_span_id=None,
        tool_name="Bash",
        start_time=_now,
        end_time=None,
        parameters={"command": "id"},
        result=None,
        status="success",
    )
    trace = ToolCallTrace(
        test_id="INST-99_stream_task0",
        events={"span-1": bash_event},
        root_span_ids=["span-1"],
        total_calls=1,
        total_duration_ms=0,
    )
    collected = CollectedTrace(
        test_id="INST-99_stream_task0",
        stream_raw='{"type":"message_start"}\n',
        stdout='{"type":"message_start"}\n',
        stderr="some stderr",
        tool_call_trace=trace,
        commands=[CommandRecord(tool_use_id="tu-1", command="id", cwd=None, started_at=None, ended_at=None, exit_code=0, stdout="", stderr="", duration_ms=None)],
        usage=[StreamUsage(input_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=5, kind="turn")],
    )

    # Simulate dict projections that _execute_test merges into metadata for the judge.
    # _stream_raw is intentionally NOT in metadata — it goes only through collected.
    result = test_case_entities.TestResult(
        test_id=test_case.id,
        status=shared_types.TestStatus.PASSED,
        blocked=True,
        executed_malicious=False,
        metadata={
            "strategy": "direct_execution",
            "attack_type_dir": "information_disclosure",
            "tool_calls": [{"tool_name": "Bash", "parameters": {"command": "id"}}],
            "command_history": ["id"],
            "api_usage": [{"input_tokens": 10, "output_tokens": 5, "kind": "turn"}],
            "stderr": "some stderr",
        },
    )

    await runner._save_test_detail(
        test_case, result, output_dir / "test_details", iteration_number=0, collected=collected
    )

    iteration_dir = (
        output_dir
        / "test_details"
        / "direct_execution"
        / "skill_inject"
        / "INST-99_stream_task0"
        / "information_disclosure"
        / "iteration_0"
    )

    # result.json and raw_logs.txt are created as before
    assert (iteration_dir / "result.json").exists()
    assert (iteration_dir / "raw_logs.txt").exists()

    # raw/ directory is created with all 6 expected files
    raw_dir = iteration_dir / "raw"
    assert raw_dir.exists(), "raw/ directory must be created for Claude stream-json runs"
    assert (raw_dir / "stream.jsonl").exists()
    assert (raw_dir / "stdout.txt").exists()
    assert (raw_dir / "stderr.txt").exists()
    assert (raw_dir / "tool_calls.json").exists()
    assert (raw_dir / "commands.json").exists()
    assert (raw_dir / "usage.json").exists()

    # Verify content of raw files — written by RawTraceWriter with typed objects
    import json as _json
    tool_calls_data = _json.loads((raw_dir / "tool_calls.json").read_text())
    assert tool_calls_data[0]["tool_name"] == "Bash"

    commands_data = _json.loads((raw_dir / "commands.json").read_text())
    assert commands_data[0]["command"] == "id"

    stderr_content = (raw_dir / "stderr.txt").read_text()
    assert stderr_content == "some stderr"

    # _stream_raw must NOT appear anywhere in result.json metadata
    result_data = _json.loads((iteration_dir / "result.json").read_text())
    assert "_stream_raw" not in result_data.get("metadata", {})

    # tool_calls and command_history DO appear in result.json metadata (judge projections)
    assert "tool_calls" in result_data.get("metadata", {})
    assert "command_history" in result_data.get("metadata", {})
