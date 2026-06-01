"""Disk-based cache for LLM script analysis results.

Stores JSON files keyed by ``{model}_{content_hash}`` under
``{script_base_dir}/.analysis_cache/{analysis_type}/``.

Each analysis type (e.g. ``script_analysis``, ``cloze_analysis``) gets its
own subdirectory so the two generators never collide.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScriptAnalysisCache:
    """Persistent disk cache for script analysis results.

    Cache structure::

        {cache_dir}/.analysis_cache/
            script_analysis/
                {model}_{hash16}.json
            cloze_analysis/
                {model}_{hash16}.json

    Each JSON file contains ``{"model": "..., "content_hash": "...", "result": {...}}``.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / ".analysis_cache"

    @staticmethod
    def _cache_key(model: str, content: str) -> str:
        """Return ``{model}_{sha256(content)[:16]}``."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        # Replace characters unsafe for filenames (e.g. dots in model names)
        safe_model = model.replace("/", "_").replace(".", "-")
        return f"{safe_model}_{content_hash}"

    def get(
        self,
        analysis_type: str,
        model: str,
        content: str,
    ) -> dict[str, Any] | None:
        """Look up a cached analysis result.

        Returns the cached result dict, or ``None`` on miss / corrupt file.
        """
        key = self._cache_key(model, content)
        path = self._cache_dir / analysis_type / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("result")  # type: ignore[no-any-return]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[Cache] Failed to read %s: %s", path, exc)
            return None

    def put(
        self,
        analysis_type: str,
        model: str,
        content: str,
        result: dict[str, Any],
    ) -> None:
        """Write an analysis result to disk."""
        key = self._cache_key(model, content)
        path = self._cache_dir / analysis_type / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = {
                "model": model,
                "content_hash": key.split("_", 1)[-1],
                "result": result,
            }
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("[Cache] Failed to write %s: %s", path, exc)
