# Module Updater Tool

import argparse
import hashlib
import importlib
import os
import sys
import types
import urllib.request
from urllib.error import URLError

CACHE_DIR = ".module_cache"

def download_update(url, cache_dir=CACHE_DIR):
    """
    Fetches module code from a remote URL and saves it to a local cache 
    using an MD5 hash of the content as the filename.
    """
    try:
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
    except URLError as e:
        print(f"Error fetching URL: {e}")
        return None

    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Generate filename based on content hash to handle updates automatically
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    file_path = os.path.join(cache_dir, f"{content_hash}.py")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Updated cache: {file_path}")
    return file_path

def apply_update(file_path):
    """
    Reads the cached file and uses exec() to execute the code into a 
    temporary namespace, creating a new module object.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Create a namespace for execution
    namespace = {}
    
    # Execute the downloaded code
    exec(source_code, namespace)
    
    # Create a new module object
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    new_module = types.ModuleType(module_name)
    new_module.__dict__.update(namespace)
    new_module.__file__ = file_path
    
    return new_module

def reload_module(module_name, new_module):
    """
    Uses importlib to hot-reload the existing module with the new module object.
    """
    if module_name in sys.modules:
        # Standard reload replaces the module in sys.modules
        importlib.reload(sys.modules[module_name])
        print(f"Hot-reloaded module: {module_name}")
    else:
        # If module wasn't loaded yet, just register the new one
        sys.modules[module_name] = new_module
        print(f"Registered new module: {module_name}")
        
    return sys.modules[module_name]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update and reload Python modules.")
    parser.add_argument("--url", required=True, help="The remote URL containing the module code.")
    parser.add_argument("--module-name", default="dynamic_module", help="The name of the module to reload.")
    
    args = parser.parse_args()
    
    # 1. Download the update
    cached_file = download_update(args.url)
    
    if cached_file:
        # 2. Apply the update (execute code)
        updated_module = apply_update(cached_file)
        
        # 3. Hot-reload
        final_module = reload_module(args.module_name, updated_module)
        
        # Example usage: Call a function if it exists in the new module
        if hasattr(final_module, 'run'):
            final_module.run()