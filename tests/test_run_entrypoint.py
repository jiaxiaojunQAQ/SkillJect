import os
import subprocess
import sys
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch

from run import _default_env_paths, load_env_file, print_attack_type_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_run_py_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "run.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "security evaluation framework" in result.stdout.lower()
    assert "--config" in result.stdout.lower()


def test_load_env_file_overrides_existing_shell_env(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SKILLJECT_TEST_VAR=from-dotenv\n")
    monkeypatch.setenv("SKILLJECT_TEST_VAR", "from-shell")

    loaded = load_env_file([env_file])

    assert loaded == env_file
    assert os.environ["SKILLJECT_TEST_VAR"] == "from-dotenv"


def test_load_env_file_uses_first_existing_candidate(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    root_dir = tmp_path / "root"
    cwd_dir = tmp_path / "cwd"
    root_dir.mkdir()
    cwd_dir.mkdir()
    (root_dir / ".env").write_text("SKILLJECT_PRIORITY_VAR=from-root\n")
    (cwd_dir / ".env").write_text("SKILLJECT_PRIORITY_VAR=from-cwd\n")
    monkeypatch.delenv("SKILLJECT_PRIORITY_VAR", raising=False)

    loaded = load_env_file([root_dir / ".env", cwd_dir / ".env"])

    assert loaded == root_dir / ".env"
    assert os.environ.get("SKILLJECT_PRIORITY_VAR") == "from-root"


def test_load_env_file_warns_when_no_env_file_found(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    loaded = load_env_file([tmp_path / ".env"])

    assert loaded is None
    output = capsys.readouterr().out
    assert ".env" in output


def test_default_env_paths_prefer_project_root_over_cwd() -> None:
    paths = _default_env_paths()

    assert paths[0] == REPO_ROOT / ".env"
    assert paths[1] == Path.cwd() / ".env"


def test_print_attack_type_summary_uses_all_determined_results_in_asr(
    capsys: CaptureFixture[str],
) -> None:
    print_attack_type_summary(
        success_tests=["skill_a_information_disclosure"],
        blocked_tests=["skill_b_information_disclosure"],
        ignored_tests=["skill_c_information_disclosure"],
    )

    output = capsys.readouterr().out

    assert "Overall ASR: 33.3% (1/3)" in output
    assert "information_disclosure: ASR=33.3%" in output
