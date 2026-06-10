"""Persist verbatim agent trace and structured projections to iteration_{N}/raw/."""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.logging.entities.tool_call_event import ToolCallEvent
from src.domain.logging.value_objects.command_record import CommandRecord
from src.domain.logging.value_objects.stream_usage import StreamUsage


class RawTraceWriter:
    """Write the iteration_{N}/raw/ layout: stream.jsonl + stdout/stderr + structured projections."""

    def __init__(self, iteration_dir: Path) -> None:
        self._raw_dir = Path(iteration_dir) / "raw"

    def write(
        self,
        *,
        stream_raw: str,
        stdout: str,
        stderr: str,
        tool_calls: Iterable[ToolCallEvent],
        commands: Iterable[CommandRecord],
        usage: Iterable[StreamUsage],
    ) -> None:
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        (self._raw_dir / "stream.jsonl").write_text(stream_raw, encoding="utf-8")
        (self._raw_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (self._raw_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        (self._raw_dir / "tool_calls.json").write_text(
            json.dumps(
                [self._to_dict(e) for e in tool_calls],
                default=self._default,
                indent=2,
            ),
            encoding="utf-8",
        )
        (self._raw_dir / "commands.json").write_text(
            json.dumps([c.to_dict() for c in commands], indent=2),
            encoding="utf-8",
        )
        (self._raw_dir / "usage.json").write_text(
            json.dumps([u.to_dict() for u in usage], indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _to_dict(event: ToolCallEvent) -> dict[str, Any]:
        return asdict(event)

    @staticmethod
    def _default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Not serializable: {type(obj)!r}")
