#!/usr/bin/env python3
"""
Repeatable local compliance checks for the self-evolving-agent skill.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "README.zh-CN.md",
    "install.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "agents/openai.yaml",
    "benchmarks/suite.json",
    "benchmarks/schemas/judge-output.schema.json",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/pull_request_template.md",
    "system/coordinator.md",
    "modules/learning-agenda.md",
    "modules/diagnose.md",
    "modules/capability-map.md",
    "modules/curriculum.md",
    "modules/evaluator.md",
    "modules/promotion.md",
    "modules/reflection.md",
    "assets/LEARNINGS.md",
    "assets/ERRORS.md",
    "assets/FEATURE_REQUESTS.md",
    "assets/CAPABILITIES.md",
    "assets/LEARNING_AGENDA.md",
    "assets/TRAINING_UNITS.md",
    "assets/EVALUATIONS.md",
    "demos/demo-1-diagnosis.md",
    "demos/demo-2-training-loop.md",
    "demos/demo-3-promotion-and-transfer.md",
    "demos/demo-4-agenda-review.md",
    "demos/demo-5-pre-task-risk-diagnosis.md",
    "hooks/openclaw/HOOK.md",
    "hooks/openclaw/handler.ts",
    "scripts/activator.sh",
    "scripts/bootstrap-workspace.sh",
    "scripts/error-detector.sh",
    "scripts/migrate-self-improving.py",
    "scripts/run-benchmark.py",
    "scripts/run-evals.py",
    "evals/evals.json",
]

MAX_SKILL_NAME_LENGTH = 64


def parse_frontmatter_minimal(frontmatter_text: str) -> tuple[dict | None, str | None]:
    parsed: dict[str, object] = {}

    for raw_line in frontmatter_text.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith(" ") or raw_line.startswith("\t"):
            continue
        if ":" not in raw_line:
            return None, f"Unsupported frontmatter line: {raw_line}"

        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            return None, f"Invalid frontmatter key in line: {raw_line}"

        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            parsed[key] = value[1:-1]
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            parsed[key] = value[1:-1]
        elif value == "":
            parsed[key] = None
        else:
            parsed[key] = value

    return parsed, None


def local_quick_validate(skill_dir: Path) -> tuple[bool, str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    frontmatter, parse_error = parse_frontmatter_minimal(frontmatter_text)
    if parse_error:
        return False, parse_error
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    allowed_properties = {"name", "description", "license", "allowed-tools", "metadata"}
    unexpected_keys = set(frontmatter.keys()) - allowed_properties
    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        allowed = ", ".join(sorted(allowed_properties))
        return (
            False,
            f"Unexpected key(s) in SKILL.md frontmatter: {unexpected}. Allowed properties are: {allowed}",
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' should be hyphen-case"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, f"Name is too long ({len(name)} characters). Maximum is {MAX_SKILL_NAME_LENGTH}."

    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} characters). Maximum is 1024."

    return True, "Local fallback validation passed."


def run_quick_validate(skill_dir: Path) -> tuple[bool, str]:
    validator = Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
    if validator.exists():
        proc = subprocess.run(
            [sys.executable, str(validator), str(skill_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0, output

    return local_quick_validate(skill_dir)


def check_file_exists(skill_dir: Path) -> tuple[bool, list[str]]:
    missing = [path for path in REQUIRED_FILES if not (skill_dir / path).exists()]
    return not missing, missing


def require_text(path: Path, needles: list[str]) -> tuple[bool, list[str]]:
    content = path.read_text()
    missing = [needle for needle in needles if needle not in content]
    return not missing, missing


def count_bootstrap_capabilities(path: Path) -> int:
    content = path.read_text()
    return content.count("## [CAP-BOOTSTRAP-")


def main() -> int:
    skill_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    checks: list[tuple[str, bool, str]] = []

    valid, message = run_quick_validate(skill_dir)
    checks.append(("skill-creator quick validation", valid, message))

    exists_ok, missing = check_file_exists(skill_dir)
    checks.append(
        (
            "required file set",
            exists_ok,
            "all required files present" if exists_ok else f"missing: {', '.join(missing)}",
        )
    )

    skill_ok, skill_missing = require_text(
        skill_dir / "SKILL.md",
        [
            "Control Loop",
            "learning agenda",
            "recorded",
            "promoted",
            "Generate a training unit if weakness or recurrence is detected.",
            "Default to the light loop first.",
        ],
    )
    checks.append(
        (
            "skill orchestration contract",
            skill_ok,
            "complete" if skill_ok else f"missing text: {', '.join(skill_missing)}",
        )
    )

    coordinator_ok, coordinator_missing = require_text(
        skill_dir / "system/coordinator.md",
        [
            "Layer 0: Learning Agenda",
            "Control Loop",
            "active learning agenda items",
            "Agenda Decision",
            "Default to the light loop.",
        ],
    )
    checks.append(
        (
            "coordinator control loop",
            coordinator_ok,
            "complete" if coordinator_ok else f"missing text: {', '.join(coordinator_missing)}",
        )
    )

    capability_count = count_bootstrap_capabilities(skill_dir / "assets/CAPABILITIES.md")
    checks.append(
        (
            "seeded capability baseline",
            capability_count >= 10,
            f"{capability_count} bootstrap capability entries",
        )
    )

    agenda_ok, agenda_missing = require_text(
        skill_dir / "assets/LEARNING_AGENDA.md",
        ["### Active Focus", "verification", "execution discipline", "memory retrieval"],
    )
    checks.append(
        (
            "bootstrap learning agenda",
            agenda_ok,
            "complete" if agenda_ok else f"missing text: {', '.join(agenda_missing)}",
        )
    )

    evals = json.loads((skill_dir / "evals/evals.json").read_text())
    eval_count = len(evals.get("evals", []))
    checks.append(
        (
            "eval scenario coverage",
            eval_count >= 4,
            f"{eval_count} eval scenarios",
        )
    )

    demo_ok, demo_missing = require_text(
        skill_dir / "demos/demo-4-agenda-review.md",
        ["## Skill Output", "Learning Agenda", "Active Focus"],
    )
    checks.append(
        (
            "proactive agenda demo",
            demo_ok,
            "complete" if demo_ok else f"missing text: {', '.join(demo_missing)}",
        )
    )

    hook_ok, hook_missing = require_text(
        skill_dir / "hooks/openclaw/handler.ts",
        ["learning agenda", "refresh the learning agenda if priorities changed"],
    )
    checks.append(
        (
            "hook reminder coverage",
            hook_ok,
            "complete" if hook_ok else f"missing text: {', '.join(hook_missing)}",
        )
    )

    benchmark_ok, benchmark_missing = require_text(
        skill_dir / "benchmarks/suite.json",
        [
            "pre-task-risk-diagnosis",
            "post-task-diagnosis-and-training",
            "evaluation-and-promotion",
            "agenda-review",
        ],
    )
    checks.append(
        (
            "benchmark scenario suite",
            benchmark_ok,
            "complete" if benchmark_ok else f"missing text: {', '.join(benchmark_missing)}",
        )
    )

    bilingual_ok, bilingual_missing = require_text(
        skill_dir / "README.md",
        [
            "README.zh-CN.md",
            "self-evolving-agent vs self-improving-agent",
            "Model-in-the-Loop Benchmark",
            "Migration From self-improving-agent",
            "Light Loop vs Full Loop",
        ],
    )
    checks.append(
        (
            "bilingual project README",
            bilingual_ok,
            "complete" if bilingual_ok else f"missing text: {', '.join(bilingual_missing)}",
        )
    )

    governance_ok, governance_missing = require_text(
        skill_dir / "README.md",
        [
            "Project Health",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "SECURITY.md",
        ],
    )
    checks.append(
        (
            "repository governance links",
            governance_ok,
            "complete" if governance_ok else f"missing text: {', '.join(governance_missing)}",
        )
    )

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    report_lines = [
        "# Evaluation Report",
        "",
        "Skill under test: `self-evolving-agent`",
        "",
        f"Date: {today}",
        "",
        "## Summary",
        "",
        f"- Passed {passed}/{total} checks",
    ]

    for name, ok, detail in checks:
        report_lines.extend(
            [
                "",
                f"## {name}",
                "",
                f"- Result: {'pass' if ok else 'fail'}",
                f"- Detail: {detail}",
            ]
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = skill_dir / "eval-results" / f"structural-{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.md").write_text("\n".join(report_lines) + "\n")

    print("\n".join(report_lines))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
