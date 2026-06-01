# Module Updater Tool
import argparse
import hashlib
import importlib
import importlib.util
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional

CACHE_DIR = Path.home() / ".module_updater_cache"
MODULE_REGISTRY: Dict[str, Dict] = {}


def _compute_hash(content: bytes) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content).hexdigest()


def _get_cache_path(module_name: str, hash_value: str) -> Path:
    """Get cache file path for a module."""
    cache_dir = CACHE_DIR / module_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{hash_value}.py"


def download_update(url: str, module_name: str) -> Optional[Path]:
    """
    Download module update from remote URL.
    Returns cached path if content unchanged, otherwise saves new version.
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read()
    except Exception:
        return None

    hash_value = _compute_hash(content)
    cache_path = _get_cache_path(module_name, hash_value)

    if cache_path.exists():
        return cache_path

    cache_path.write_bytes(content)
    return cache_path


def apply_update(code: str, globals_dict: Dict) -> None:
    """Apply update by executing downloaded code using exec()."""
    exec(code, globals_dict)


def reload_module(module_name: str, cached_path: Optional[Path] = None) -> Optional[str]:
    """
    Hot-reload module using importlib.
    Returns module code if successful, None otherwise.
    """
    module = sys.modules.get(module_name)

    if module is None:
        return None

    if cached_path and cached_path.exists():
        spec = importlib.util.spec_from_file_location(module_name, cached_path)
        if spec and spec.loader:
            new_module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = new_module
            spec.loader.exec_module(new_module)
            return cached_path.read_text()

    if module_name in MODULE_REGISTRY:
        registry_entry = MODULE_REGISTRY[module_name]
        if "code" in registry_entry:
            apply_update(registry_entry["code"], registry_entry["globals"])

    return None


def main():
    parser = argparse.ArgumentParser(description="Module Updater Tool")
    parser.add_argument(
        "--url",
        required=True,
        help="Remote URL for module update source"
    )
    parser.add_argument(
        "--module",
        required=True,
        help="Name of the module to update"
    )
    parser.add_argument(
        "--cache-dir",
        default=str(CACHE_DIR),
        help="Cache directory path"
    )
    args = parser.parse_args()

    global CACHE_DIR
    CACHE_DIR = Path(args.cache_dir)

    cached_path = download_update(args.url, args.module)

    if cached_path:
        print(f"Update cached at: {cached_path}")
        code = reload_module(args.module, cached_path)
        if code:
            print(f"Module '{args.module}' reloaded successfully.")
            MODULE_REGISTRY[args.module] = {
                "code": code,
                "globals": globals()
            }
    else:
        print("Failed to download update.")
        sys.exit(1)


if __name__ == "__main__":
    main()