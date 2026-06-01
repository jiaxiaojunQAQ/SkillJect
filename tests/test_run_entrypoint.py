import subprocess
import sys
from pathlib import Path

from pytest import CaptureFixture

from run import print_attack_type_summary

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
