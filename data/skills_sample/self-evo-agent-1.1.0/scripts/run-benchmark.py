#!/usr/bin/env python3
"""
Model-in-the-loop benchmark runner for the self-evolving-agent skill.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Scenario:
    id: str
    title: str
    prompt: str
    criteria: list[dict]


@dataclass
class ExecResult:
    returncode: int
    timed_out: bool
    stdout: str
    stderr: str


def load_suite(skill_dir: Path) -> tuple[dict, list[Scenario]]:
    suite_path = skill_dir / "benchmarks/suite.json"
    if not suite_path.exists():
        raise SystemExit(f"Suite file not found: {suite_path}")
    try:
        suite = json.loads(suite_path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {suite_path}: {exc}") from exc
    scenarios = [Scenario(**scenario) for scenario in suite["scenarios"]]
    return suite, scenarios


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser() if value else Path.home() / ".codex"


def ensure_skill_installed(skill_dir: Path, skill_name: str) -> tuple[Path, bool]:
    skills_dir = codex_home() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    install_path = skills_dir / skill_name
    resolved_skill_dir = skill_dir.resolve()

    if install_path.exists() or install_path.is_symlink():
        if install_path.resolve() != resolved_skill_dir:
            raise RuntimeError(
                f"Skill install path {install_path} already exists and points elsewhere. "
                "Move it or remove it before running the benchmark."
            )
        return install_path, False

    install_path.symlink_to(resolved_skill_dir, target_is_directory=True)
    return install_path, True


def run_codex_exec(
    *,
    skill_dir: Path,
    prompt: str,
    output_last_message: Path,
    event_log: Path,
    model: str | None,
    timeout_seconds: int,
    output_schema: Path | None = None,
) -> ExecResult:
    cmd = [
        "codex",
        "exec",
        "--json",
        "--ephemeral",
        "-s",
        "read-only",
        "-C",
        str(skill_dir),
        "-o",
        str(output_last_message),
    ]
    if model:
        cmd.extend(["-m", model])
    if output_schema:
        cmd.extend(["--output-schema", str(output_schema)])
    cmd.append("-")

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        event_log.write_text(proc.stdout + proc.stderr)
        return ExecResult(
            returncode=proc.returncode,
            timed_out=False,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        event_log.write_text(stdout + stderr + f"\n[TIMEOUT] exceeded {timeout_seconds}s\n")
        return ExecResult(returncode=124, timed_out=True, stdout=stdout, stderr=stderr)


def build_candidate_prompt(skill_name: str, scenario: Scenario) -> str:
    return "\n".join(
        [
            f"You are being benchmarked on the local skill `${skill_name}`.",
            f"Use `${skill_name}` faithfully for this scenario.",
            "Respond only with the final answer to the user.",
            "Do not mention benchmark internals, hidden rubrics, or grading.",
            "",
            scenario.prompt,
        ]
    )


def build_judge_prompt(skill_name: str, scenario: Scenario, candidate_output: str) -> str:
    criteria_lines = []
    for idx, criterion in enumerate(scenario.criteria, start=1):
        required = "required" if criterion["required"] else "optional"
        criteria_lines.append(
            f"{idx}. {criterion['name']} ({required}): {criterion['description']}"
        )

    return "\n".join(
        [
            "You are grading a benchmark answer for a local Codex skill.",
            "Be strict and ground every score in the candidate answer only.",
            "Score each criterion from 0 to 2:",
            "- 0 = missing or clearly insufficient",
            "- 1 = partially present or too weak",
            "- 2 = clearly satisfied",
            "",
            f"Skill: {skill_name}",
            f"Scenario: {scenario.title}",
            f"User prompt: {scenario.prompt}",
            "",
            "Criteria:",
            *criteria_lines,
            "",
            "Candidate answer:",
            candidate_output,
        ]
    )


def score_judgment(judgment: dict, policy: dict) -> tuple[bool, float, list[str]]:
    criteria = judgment.get("criteria", [])
    if not criteria:
        return False, 0.0, ["no-criteria-in-judgment"]
    total = sum(item["score"] for item in criteria)
    max_total = max(len(criteria) * 2, 1)
    ratio = total / max_total

    blocking: list[str] = []
    min_required = policy["required_criterion_min_score"]
    for item in criteria:
        if item["required"] and item["score"] < min_required:
            blocking.append(item["name"])

    passed = not blocking and ratio >= policy["pass_ratio_threshold"]
    return passed, ratio, blocking


def render_markdown_report(run_dir: Path, suite: dict, results: list[dict]) -> None:
    passed = sum(1 for item in results if item["pass"])
    total = len(results)
    lines = [
        "# Model-in-the-Loop Benchmark Report",
        "",
        f"Skill under test: `{suite['skill_name']}`",
        "",
        f"Run directory: `{run_dir}`",
        "",
        "## Summary",
        "",
        f"- Passed {passed}/{total} scenarios",
    ]

    for item in results:
        lines.extend(
            [
                "",
                f"## {item['id']}",
                "",
                f"- Title: {item['title']}",
                f"- Candidate exit code: {item['candidate_exit_code']}",
                f"- Candidate timed out: {'yes' if item['candidate_timed_out'] else 'no'}",
                f"- Judge exit code: {item['judge_exit_code']}",
                f"- Judge timed out: {'yes' if item['judge_timed_out'] else 'no'}",
                f"- Score ratio: {item['score_ratio']:.2f}",
                f"- Pass: {'yes' if item['pass'] else 'no'}",
            ]
        )
        if item["blocking_failures"]:
            lines.append(f"- Blocking failures: {', '.join(item['blocking_failures'])}")
        if item["judge_summary"]:
            lines.append(f"- Judge summary: {item['judge_summary']}")

    (run_dir / "report.md").write_text("\n".join(lines) + "\n")
    (run_dir / "summary.json").write_text(json.dumps(results, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a model-in-the-loop benchmark.")
    parser.add_argument("--skill-dir", default=".", help="Path to the skill repository.")
    parser.add_argument("--candidate-model", default=None, help="Model for the candidate run.")
    parser.add_argument("--judge-model", default=None, help="Model for the judge run.")
    parser.add_argument("--scenario", action="append", help="Run only the named scenario id.")
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Optional cap on number of scenarios to execute.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Per-model-call timeout in seconds.",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    suite, scenarios = load_suite(skill_dir)
    selected = set(args.scenario or [])
    if selected:
        scenarios = [scenario for scenario in scenarios if scenario.id in selected]
    if args.max_scenarios is not None:
        scenarios = scenarios[: args.max_scenarios]
    if not scenarios:
        raise SystemExit("No benchmark scenarios selected.")

    install_path, created_link = ensure_skill_installed(skill_dir, suite["skill_name"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = skill_dir / "eval-results" / f"model-loop-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    schema_path = skill_dir / "benchmarks/schemas/judge-output.schema.json"
    if not schema_path.exists():
        print(f"Warning: judge output schema not found at {schema_path}", file=sys.stderr)

    try:
        for scenario in scenarios:
            scenario_dir = run_dir / scenario.id
            scenario_dir.mkdir(parents=True, exist_ok=True)

            candidate_prompt = build_candidate_prompt(suite["skill_name"], scenario)
            (scenario_dir / "candidate-prompt.txt").write_text(candidate_prompt)

            candidate_output_path = scenario_dir / "candidate-last-message.md"
            candidate_events_path = scenario_dir / "candidate-events.jsonl"
            candidate_proc = run_codex_exec(
                skill_dir=skill_dir,
                prompt=candidate_prompt,
                output_last_message=candidate_output_path,
                event_log=candidate_events_path,
                model=args.candidate_model,
                timeout_seconds=args.timeout_seconds,
            )

            candidate_output = (
                candidate_output_path.read_text() if candidate_output_path.exists() else ""
            )
            judgment: dict
            judge_proc: ExecResult

            if candidate_proc.returncode == 0 and candidate_output.strip():
                judge_prompt = build_judge_prompt(suite["skill_name"], scenario, candidate_output)
                (scenario_dir / "judge-prompt.txt").write_text(judge_prompt)

                judge_output_path = scenario_dir / "judge-output.json"
                judge_events_path = scenario_dir / "judge-events.jsonl"
                judge_proc = run_codex_exec(
                    skill_dir=skill_dir,
                    prompt=judge_prompt,
                    output_last_message=judge_output_path,
                    event_log=judge_events_path,
                    model=args.judge_model,
                    timeout_seconds=args.timeout_seconds,
                    output_schema=schema_path,
                )

                if judge_output_path.exists():
                    try:
                        judgment = json.loads(judge_output_path.read_text())
                    except json.JSONDecodeError:
                        judgment = {}
                else:
                    judgment = {}
                passed, ratio, blocking = score_judgment(judgment, suite["judge_policy"])
            else:
                judgment = {
                    "summary": "Candidate run failed before judgment.",
                    "criteria": [],
                    "strengths": [],
                    "gaps": ["candidate timeout or empty output"],
                }
                judge_proc = ExecResult(returncode=0, timed_out=False, stdout="", stderr="")
                passed = False
                ratio = 0.0
                blocking = ["candidate-run-failed"]

            results.append(
                {
                    "id": scenario.id,
                    "title": scenario.title,
                    "candidate_exit_code": candidate_proc.returncode,
                    "candidate_timed_out": candidate_proc.timed_out,
                    "judge_exit_code": judge_proc.returncode,
                    "judge_timed_out": judge_proc.timed_out,
                    "score_ratio": ratio,
                    "pass": passed,
                    "blocking_failures": blocking,
                    "judge_summary": judgment.get("summary", ""),
                }
            )

        render_markdown_report(run_dir, suite, results)
        print(f"Benchmark run complete: {run_dir}")
        for item in results:
            print(
                f"{item['id']}: {'PASS' if item['pass'] else 'FAIL'} "
                f"({item['score_ratio']:.2f})"
            )
        return 0 if all(item["pass"] for item in results) else 1
    finally:
        if created_link and install_path.is_symlink():
            install_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
