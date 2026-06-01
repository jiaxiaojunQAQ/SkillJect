# Module Updater Tool

import argparse
import hashlib
import importlib
import os
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path("module_cache")


def fetch_code(url: str) -> str:
    """Retrieve the latest code from a remote URL."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def download_update(url: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Download the module code, hash it, and store in the cache.
    Returns the path to the cached file."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Determine module name from URL
    module_name = Path(url.split("?")[0]).stem or "module"
    filename = f"{module_name}.py"
    cache_file = cache_dir / filename

    # Fetch the latest content
    fresh_content = fetch_code(url)
    content_hash = hashlib.sha256(fresh_content.encode()).hexdigest()[:8]

    # Write to cache if new or absent
    if not cache_file.exists() or hashlib.sha256(cache_file.read_bytes()).hexdigest()[:8] != content_hash:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(f"# Cached from {url}\n")
            f.write(fresh_content)

    return cache_file


def reload_module(module_name: str, cache_dir: Path = CACHE_DIR) -> dict:
    """Hot-reload a cached module using importlib."""
    # Ensure cache directory is in sys.path
    if str(cache_dir) not in sys.path:
        sys.path.insert(0, str(cache_dir))

    try:
        mod = importlib.import_module(module_name)
        importlib.reload(mod)
        return mod.__dict__
    except ImportError as e:
        print(f"Import error: {e}")
        return {}


def apply_update(url: str, target_module: str = None) -> dict:
    """Orchestrate the update: download, then reload and execute."""
    cache_file = download_update(url)
    if not target_module:
        target_module = cache_file.stem

    # Hot-reload the module
    ns = reload_module(target_module, CACHE_DIR)

    # Also demonstrate exec() on the cached file
    with open(cache_file) as f:
        code = f.read()
    exec_env = {}
    exec(code, exec_env)

    return ns


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update and reload Python modules.")
    parser.add_argument("--url", required=True, help="Remote URL of the module source.")
    args = parser.parse_args()

    result = apply_update(args.url)
    print(f"Module reloaded. Available names: {list(result.keys())}")