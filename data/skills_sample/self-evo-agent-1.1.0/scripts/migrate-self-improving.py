#!/usr/bin/env python3
"""
Safely import legacy self-improving-agent logs into the self-evolving-agent workspace.

The migration is intentionally lossless:
- original legacy files remain untouched
- imported files are copied verbatim into a read-only legacy folder
- new .evolution ledgers stay clean and can normalize entries gradually over time
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


LEGACY_FILES = ("LEARNINGS.md", "ERRORS.md", "FEATURE_REQUESTS.md")
DEFAULT_SOURCE_CANDIDATES = (
    Path.home() / ".openclaw" / "workspace" / ".learnings",
    Path.cwd() / ".learnings",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify_path(path: Path) -> str:
    raw = str(path.expanduser().resolve())
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").lower()
    return slug or "legacy-source"


def detect_sources(explicit_sources: list[Path]) -> list[Path]:
    candidates = explicit_sources if explicit_sources else list(DEFAULT_SOURCE_CANDIDATES)
    sources: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.is_dir() and any((resolved / name).exists() for name in LEGACY_FILES):
            sources.append(resolved)
    return sources


def copy_legacy_logs(
    source_dir: Path,
    target_root: Path,
    force: bool,
) -> tuple[list[str], list[str]]:
    source_label = slugify_path(source_dir)
    destination_dir = target_root / source_label
    destination_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []

    for filename in LEGACY_FILES:
        source_file = source_dir / filename
        if not source_file.exists():
            continue

        destination_file = destination_dir / filename

        if destination_file.exists() and not force:
            if sha256(source_file) == sha256(destination_file):
                skipped.append(f"{filename} (already imported)")
            else:
                skipped.append(f"{filename} (destination exists, use --force to refresh)")
            continue

        shutil.copy2(source_file, destination_file)
        copied.append(filename)

    return copied, skipped


def build_index(
    target_root: Path,
    imported_sources: list[tuple[Path, list[str], list[str]]],
) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Legacy self-improving-agent import",
        "",
        "This folder preserves the original self-improving-agent logs without rewriting them.",
        "Treat these files as read-only migration input.",
        "Normalize an item into the new .evolution ledgers only after it is reused, agenda-worthy, or needed for evaluation.",
        "",
        f"Imported: {timestamp}",
        "",
        "## Imported Sources",
        "",
    ]

    for source_dir, copied, skipped in imported_sources:
        lines.extend(
            [
                f"### {source_dir}",
                "",
                f"- Imported files: {', '.join(copied) if copied else 'none'}",
                f"- Skipped files: {', '.join(skipped) if skipped else 'none'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Transition Guidance",
            "",
            "- Search this folder during memory retrieval while the migration is still fresh.",
            "- Keep the old `.learnings/` directory untouched until you have verified the import.",
            "- Disable the old `self-improvement` hook after verification to avoid duplicate reminders.",
            "- Prefer creating new capability, training, and evaluation records in `.evolution/` rather than backfilling everything up front.",
            "",
        ]
    )

    (target_root / "IMPORT_INDEX.md").write_text("\n".join(lines))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import legacy self-improving-agent logs into a self-evolving-agent workspace."
    )
    parser.add_argument(
        "--target-dir",
        default=str(Path.home() / ".openclaw" / "workspace" / ".evolution"),
        help="Target .evolution directory.",
    )
    parser.add_argument(
        "--source-dir",
        action="append",
        default=[],
        help="Legacy .learnings directory to import. May be provided multiple times.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite imported copies inside the target legacy folder.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    target_dir = Path(args.target_dir).expanduser().resolve()
    legacy_root = target_dir / "legacy-self-improving"
    legacy_root.mkdir(parents=True, exist_ok=True)

    sources = detect_sources([Path(raw) for raw in args.source_dir])
    if not sources:
        print("No legacy self-improving-agent sources found.")
        print("Looked for .learnings directories with LEARNINGS.md, ERRORS.md, or FEATURE_REQUESTS.md.")
        return 0

    imported_sources: list[tuple[Path, list[str], list[str]]] = []
    any_copied = False

    for source_dir in sources:
        copied, skipped = copy_legacy_logs(source_dir, legacy_root, force=args.force)
        imported_sources.append((source_dir, copied, skipped))
        any_copied = any_copied or bool(copied)

    build_index(legacy_root, imported_sources)

    print(f"Legacy import root: {legacy_root}")
    for source_dir, copied, skipped in imported_sources:
        print()
        print(f"Source: {source_dir}")
        print(f"  imported: {', '.join(copied) if copied else 'none'}")
        print(f"  skipped:  {', '.join(skipped) if skipped else 'none'}")

    old_hook = Path.home() / ".openclaw" / "hooks" / "self-improvement"
    if old_hook.exists():
        print()
        print("Detected the legacy self-improvement hook directory:")
        print(f"  {old_hook}")
        print("Disable it after verifying the import to avoid duplicate reminders.")

    if any_copied:
        print()
        print("Migration complete. Originals were left untouched.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
