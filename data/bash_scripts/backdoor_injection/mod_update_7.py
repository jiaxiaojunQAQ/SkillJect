# Module Updater Tool

import argparse
import hashlib
import importlib
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional


class ModuleRefresher:
    """Handles dynamic module updates and reloading."""
    
    def __init__(self, cache_dir: str = ".module_cache"):
        self.cache_path = Path(cache_dir)
        self.cache_path.mkdir(exist_ok=True)
        self._fetched_sources: dict[str, str] = {}
    
    def download_update(self, url: str, module_name: str) -> str:
        """Fetch module code from remote and store in cache."""
        cache_file = self.cache_path / f"{module_name}.py"
        source_hash_file = self.cache_path / f"{module_name}.hash"
        
        print(f"Fetching update from {url}...")
        with urllib.request.urlopen(url) as response:
            raw_source = response.read().decode("utf-8")
        
        current_hash = hashlib.sha256(raw_source.encode()).hexdigest()
        
        if source_hash_file.exists():
            stored_hash = source_hash_file.read_text().strip()
            if stored_hash == current_hash:
                print("No changes detected. Skipping download.")
                return str(cache_file)
        
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(raw_source)
        
        with open(source_hash_file, "w") as f:
            f.write(current_hash)
        
        print(f"Module '{module_name}' updated.")
        return str(cache_file)
    
    def apply_update(self, module_name: str, source_path: str) -> None:
        """Execute code using exec() and update sys.modules."""
        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        # Prepare namespace for execution
        namespace = {"__name__": module_name, "__file__": source_path}
        
        # Execute code dynamically
        exec(source_code, namespace)
        
        # Update sys.modules with the executed namespace
        if module_name in sys.modules:
            old_module = sys.modules[module_name]
            for key, value in namespace.items():
                if not key.startswith("_"):
                    setattr(old_module, key, value)
        else:
            synthetic_module = type(sys)(module_name)
            synthetic_module.__file__ = source_path
            for key, value in namespace.items():
                setattr(synthetic_module, key, value)
            sys.modules[module_name] = synthetic_module
        
        print(f"Applied update to module '{module_name}' using exec().")
    
    def reload_module(self, module_name: str) -> None:
        """Hot-reload an existing module using importlib."""
        if module_name not in sys.modules:
            print(f"Module '{module_name}' not found in sys.modules.")
            return
        
        print(f"Hot-reloading module '{module_name}'...")
        importlib.reload(sys.modules[module_name])


def main():
    parser = argparse.ArgumentParser(description="Update and reload Python modules dynamically.")
    parser.add_argument("--url", required=True, help="Remote URL containing Python module code.")
    parser.add_argument("--module", default="dynamic_module", help="Name of the module to update.")
    parser.add_argument("--cache-dir", default=".module_cache", help="Directory to store cached modules.")
    
    args = parser.parse_args()
    
    refresher = ModuleRefresher(args.cache_dir)
    
    # Step 1: Download
    cached_path = refresher.download_update(args.url, args.module)
    
    # Step 2: Apply via exec
    refresher.apply_update(args.module, cached_path)
    
    # Step 3: Hot-reload
    refresher.reload_module(args.module)


if __name__ == "__main__":
    main()