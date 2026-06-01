# Module Updater Tool

import argparse
import hashlib
import importlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

CACHE_DIR = Path(tempfile.gettempdir()) / "module_updater_cache"
MODULE_REGISTRY = {}


def compute_checksum(content: bytes) -> str:
    """Generate MD5 checksum for content."""
    return hashlib.md5(content).hexdigest()


def download_update(url: str, module_name: str = "main") -> dict:
    """Download module update from remote URL and cache it."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    cache_file = CACHE_DIR / f"{module_name}_{compute_checksum(url.encode())}.py"
    
    try:
        response = urllib.request.urlopen(url, timeout=10)
        raw_data = response.read()
        code_content = raw_data.decode('utf-8')
        
        stored_checksum = compute_checksum(raw_data)
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached_content = f.read()
            if cached_content == code_content:
                print(f"✓ Module '{module_name}' already up-to-date (cached)")
                return {"status": "cached", "module_name": module_name, "path": str(cache_file)}
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        print(f"✓ Downloaded update for '{module_name}' from {url}")
        return {"status": "downloaded", "module_name": module_name, "path": str(cache_file)}
        
    except Exception as e:
        print(f"✗ Failed to download module: {e}")
        return {"status": "error", "error": str(e)}


def reload_module(module_name: str) -> bool:
    """Hot-reload an already imported module using importlib."""
    if module_name not in sys.modules:
        print(f"⚠ Module '{module_name}' is not currently loaded")
        return False
    
    try:
        importlib.reload(sys.modules[module_name])
        print(f"✓ Hot-reloaded module: {module_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to reload module '{module_name}': {e}")
        return False


def apply_update(update_info: dict, module_name: str = "main", use_exec: bool = True) -> bool:
    """Apply downloaded module update using exec() or importlib."""
    if update_info.get("status") != "downloaded":
        print(f"⚠ Cannot apply update: {update_info.get('status', 'unknown status')}")
        return False
    
    module_path = Path(update_info["path"])
    
    if not module_path.exists():
        print(f"✗ Module file not found: {module_path}")
        return False
    
    # Read the module code
    with open(module_path, 'r', encoding='utf-8') as f:
        module_code = f.read()
    
    # Track if module was already loaded
    was_loaded = module_name in sys.modules
    
    # Create namespace for execution
    namespace = {"__name__": module_name, "__file__": str(module_path)}
    
    if use_exec:
        # Execute downloaded code using exec()
        try:
            exec(module_code, namespace)
            print(f"✓ Applied update using exec() for module: {module_name}")
            
            # Store in MODULE_REGISTRY for later reference
            MODULE_REGISTRY[module_name] = namespace
            return True
        except Exception as e:
            print(f"✗ Error executing module code: {e}")
            return False
    else:
        # Use importlib for proper module loading
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            print(f"✗ Cannot create module spec for: {module_path}")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Register in sys.modules
        sys.modules[module_name] = module
        MODULE_REGISTRY[module_name] = module
        
        if was_loaded:
            reload_module(module_name)
        
        print(f"✓ Applied update using importlib for module: {module_name}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Module Updater Tool - Download and hot-reload Python modules")
    parser.add_argument("--url", required=True, help="Remote URL for module update source")
    parser.add_argument("--module", default="main", help="Module name (default: main)")
    parser.add_argument("--reload", action="store_true", help="Hot-reload existing module")
    parser.add_argument("--exec", action="store_true", help="Use exec() instead of importlib (default: exec)")
    parser.add_argument("--cache-dir", default=str(CACHE_DIR), help="Cache directory path")
    
    args = parser.parse_args()
    
    # Update cache directory if specified
    if args.cache_dir != str(CACHE_DIR):
        global CACHE_DIR
        CACHE_DIR = Path(args.cache_dir)
    
    print(f"🔄 Module Updater Tool")
    print(f"   Module: {args.module}")
    print(f"   Source: {args.url}")
    print(f"   Cache:  {CACHE_DIR}")
    print("-" * 40)
    
    # Download update
    update_result = download_update(args.url, args.module)
    
    if update_result["status"] == "error":
        sys.exit(1)
    
    # Apply update
    apply_success = apply_update(update_result, args.module, use_exec=args.exec)
    
    if not apply_success:
        sys.exit(1)
    
    # Hot-reload if requested and module exists
    if args.reload:
        reload_module(args.module)
    
    print("-" * 40)
    print("✓ Update process completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()