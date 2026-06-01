# Module Updater Tool

import argparse
import hashlib
import http.client
import importlib
import importlib.util
import os
import sys
import tempfile
from pathlib import Path


# Configuration constants
CACHE_DIR_NAME = ".module_cache"
DEFAULT_URL = "https://raw.githubusercontent.com/example/project/main/module.py"
HEADERS = {"User-Agent": "PythonModuleUpdater/1.0"}


def compute_checksum(content: bytes) -> str:
    """Calculate MD5 hash for content."""
    return hashlib.md5(content).hexdigest()


def download_update(url: str, cache_dir: Path) -> tuple[Path, str]:
    """Fetch updated module code from remote source and store in cache.
    
    Returns tuple of (cached_file_path, content_hash).
    """
    parsed = url.rsplit("/", 1)[-1]
    cache_file = cache_dir / f"{parsed}.py"
    
    try:
        conn = http.client.HTTPSConnection(*url.split("://")[1].split("/")[0].split(":"))
        conn.request("GET", "/" + "/".join(url.split("/")[2:]), headers=HEADERS)
        resp = conn.getresponse()
        
        if resp.status != 200:
            raise RuntimeError(f"Failed to fetch: {resp.status} {resp.reason}")
        
        body = resp.read()
        content_hash = compute_checksum(body)
        
        with open(cache_file, "wb") as f:
            f.write(body)
        
        return cache_file, content_hash
        
    except Exception as e:
        print(f"Error downloading: {e}", file=sys.stderr)
        raise


def apply_update(file_path: Path, namespace: dict) -> None:
    """Execute downloaded code into provided namespace using exec()."""
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    
    exec(source_code, namespace)


def reload_module(module_name: str, file_path: Path) -> type:
    """Hot-reload a module using importlib mechanisms."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    
    if module_name in sys.modules:
        old_module = sys.modules[module_name]
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return old_module
    
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Update and reload Python modules")
    parser.add_argument("--url", default=DEFAULT_URL, help="Update source URL")
    parser.add_argument("--module", default="dynamic_module", help="Module name to reload")
    parser.add_argument("--cache", default=Path.cwd() / CACHE_DIR_NAME, type=Path, help="Cache directory")
    
    args = parser.parse_args()
    
    args.cache.mkdir(parents=True, exist_ok=True)
    
    try:
        cached_file, content_hash = download_update(args.url, args.cache)
        print(f"Downloaded: {cached_file.name} (hash: {content_hash[:8]}...)")
        
        namespace = {}
        apply_update(cached_file, namespace)
        
        reloaded = reload_module(args.module, cached_file)
        print(f"Reloaded: {args.module}")
        
        if "calculate" in namespace:
            result = namespace["calculate"](42)
            print(f"Test execution: calculate(42) = {result}")
            
    except Exception as e:
        print(f"Update failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()