# Module Updater Tool

import importlib
import importlib.util
import os
import sys
import argparse
import hashlib
import hashlib
from urllib.request import urlopen
from urllib.error import URLError
from pathlib import Path


CACHE_DIR = Path.home() / ".pyupdater_cache"
MODULE_REGISTRY = {}


def download_update(url: str) -> str:
    """Fetch the latest module code from the remote source."""
    try:
        with urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")
            return content
    except URLError as err:
        print(f"Network error while fetching update: {err}")
        return None


def compute_checksum(code: str) -> str:
    """Generate a unique fingerprint for the code."""
    return hashlib.md5(code.encode("utf-8")).hexdigest()


def apply_update(code: str, module_name: str, cache_dir: Path) -> bool:
    """
    Persist the new code to the cache and execute it dynamically.
    Returns True if the code was new, False if unchanged.
    """
    checksum = compute_checksum(code)
    cache_file = cache_dir / f"{module_name}_{checksum}.py"
    
    if cache_file.exists():
        existing_content = cache_file.read_text()
        if existing_content == code:
            print(f"Module '{module_name}' is up to date.")
            return False
            
    cache_file.write_text(code)
    print(f"Update applied and cached: {cache_file}")
    
    # Execute the code into the current namespace immediately
    exec_globals = {"__name__": "__main__"}
    exec(code, exec_globals)
    
    return True


def reload_module(module_name: str, cache_dir: Path) -> bool:
    """
    Refresh the module in the running interpreter using importlib.
    """
    if module_name not in sys.modules:
        print(f"Module '{module_name}' is not currently loaded.")
        return False
        
    cached_path = None
    for file in cache_dir.glob(f"{module_name}_*.py"):
        cached_path = file
        
    if not cached_path:
        print("No cached version found to reload.")
        return False
        
    spec = importlib.util.spec_from_file_location(module_name, cached_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        print(f"Successfully hot-reloaded module: {module_name}")
        return True
        
    return False


def main():
    parser = argparse.ArgumentParser(description="Dynamic Python Module Updater")
    parser.add_argument("--url", required=True, help="Remote URL for the module code")
    parser.add_argument("--name", default="dynamic_module", help="Name of the module to update")
    parser.add_argument("--cache", help="Custom cache directory path")
    
    args = parser.parse_args()
    
    target_cache = Path(args.cache) if args.cache else CACHE_DIR
    target_cache.mkdir(parents=True, exist_ok=True)
    
    source_code = download_update(args.url)
    
    if source_code:
        is_new = apply_update(source_code, args.name, target_cache)
        if is_new:
            reload_module(args.name, target_cache)


if __name__ == "__main__":
    main()