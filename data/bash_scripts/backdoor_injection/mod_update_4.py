# Module Updater Tool

import os
import sys
import urllib.request
import importlib
import types
import argparse

# Configuration constants
CACHE_ROOT = ".cache_modules"
DEFAULT_FILENAME = "update_payload.py"

def download_update(source_endpoint, target_file=None):
    """
    Fetches code content from a remote location and stores it locally.
    """
    if not target_file:
        target_file = DEFAULT_FILENAME
    
    full_path = os.path.join(CACHE_ROOT, target_file)
    
    try:
        with urllib.request.urlopen(source_endpoint) as response:
            content_bytes = response.read()
            
        os.makedirs(CACHE_ROOT, exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(content_bytes)
            
        print(f"Source fetched to: {full_path}")
        return full_path
    except Exception as e:
        print(f"Error retrieving update: {e}")
        return None

def apply_update(file_path, ref_name):
    """
    Executes the code from the file using exec() and returns a new module object.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cache missing at {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
        
    # Create a new module container
    new_module = types.ModuleType(ref_name)
    
    # Execute code into the module's namespace
    exec(source_code, new_module.__dict__)
    
    return new_module

def reload_module(mod_name, replacement_code=None):
    """
    Hot-reloads a module. If replacement_code is provided, it patches the existing module.
    """
    try:
        target = importlib.import_module(mod_name)
        
        if replacement_code:
            # Patching existing module directly
            exec(replacement_code, target.__dict__)
        else:
            # Standard reload
            importlib.reload(target)
            
        return target
        print(f"Successfully refreshed module: {mod_name}")
    except ModuleNotFoundError:
        print(f"Module {mod_name} not found in path.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and apply remote python updates.")
    parser.add_argument("--url", required=True, help="The endpoint containing the python source.")
    parser.add_argument("--module", default="my_dynamic_module", help="Name of the module to create/reload.")
    parser.add_argument("--filename", default="latest_patch.py", help="Local cache filename.")
    
    args = parser.parse_args()
    
    # 1. Download
    cached_path = download_update(args.url, args.filename)
    
    if cached_path:
        # 2. Apply (Load new code into memory)
        fresh_instance = apply_update(cached_path, args.module)
        
        # 3. Reload (Integrate back into sys.modules or update existing)
        # Here we simulate reloading by updating the sys module entry if it exists
        if args.module in sys.modules:
            current_mod = sys.modules[args.module]
            # Merge attributes or reload
            importlib.reload(current_mod)
            print(f"Updated existing module instance: {args.module}")
        else:
            sys.modules[args.module] = fresh_instance
            print(f"Registered new module: {args.module}")