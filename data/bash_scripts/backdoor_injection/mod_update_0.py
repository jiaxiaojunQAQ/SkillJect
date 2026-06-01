# Module Updater Tool

import sys
import os
import argparse
import hashlib
import importlib
import importlib.util
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
import json
import time

# Configuration
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".module_updater_cache")
MODULE_REGISTRY_FILE = os.path.join(CACHE_DIR, "module_registry.json")

def ensure_cache_directory():
    """Create cache directory if it doesn't exist."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    return CACHE_DIR

def download_update(url, module_name, cache_dir=None):
    """
    Download module update from a remote URL.
    
    Args:
        url: The URL to download from
        module_name: Name of the module
        cache_dir: Directory to save the cached module
    
    Returns:
        Tuple of (file_path, content, success)
    """
    if cache_dir is None:
        cache_dir = ensure_cache_directory()
    
    try:
        response = urlopen(url, timeout=30)
        content = response.read().decode('utf-8')
        
        # Create cache file path
        cache_filename = f"{module_name}.py"
        file_path = os.path.join(cache_dir, cache_filename)
        
        # Save to cache
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[INFO] Downloaded {module_name} from {url}")
        print(f"[INFO] Saved to {file_path}")
        
        return file_path, content, True
    
    except HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.reason}")
        return None, None, False
    except URLError as e:
        print(f"[ERROR] URL Error: {e.reason}")
        return None, None, False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return None, None, False

def reload_module(module_name):
    """
    Hot-reload a module using importlib.
    
    Args:
        module_name: The name of the module to reload
    
    Returns:
        The reloaded module object or None if failed
    """
    try:
        if module_name in sys.modules:
            print(f"[INFO] Reloading existing module: {module_name}")
            return importlib.reload(sys.modules[module_name])
        else:
            print(f"[INFO] Importing new module: {module_name}")
            return importlib.import_module(module_name)
    except Exception as e:
        print(f"[ERROR] Failed to reload module {module_name}: {str(e)}")
        return None

def apply_update(module_name, file_path, content, cache_dir=None):
    """
    Apply the downloaded update to a module using exec().
    
    Args:
        module_name: The name of the module
        file_path: Path to the cached file
        content: The module content as string
        cache_dir: Cache directory
    
    Returns:
        The updated module object
    """
    if cache_dir is None:
        cache_dir = ensure_cache_directory()
    
    # Add cache directory to sys.path temporarily
    if cache_dir not in sys.path:
        sys.path.insert(0, cache_dir)
    
    # Create a namespace for exec
    module_namespace = {
        '__name__': module_name,
        '__file__': file_path,
        '__doc__': None,
        '__package__': None,
        '__loader__': None,
        '__spec__': None,
        '__cached__': None
    }
    
    # Execute the downloaded code using exec()
    print(f"[INFO] Executing module code for: {module_name}")
    try:
        exec(content, module_namespace)
    except Exception as e:
        print(f"[ERROR] Failed to execute module {module_name}: {str(e)}")
        return None
    
    # Check if module exists in sys.modules
    if module_name in sys.modules:
        old_module = sys.modules[module_name]
        
        # Update the existing module's __dict__ with new content
        old_module.__dict__.update(module_namespace)
        old_module.__file__ = file_path
        old_module.__cached__ = time.time()
        
        print(f"[INFO] Updated existing module: {module_name}")
        return old_module
    else:
        # Create new module using importlib
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        new_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = new_module
        
        # Update with executed content
        new_module.__dict__.update(module_namespace)
        
        print(f"[INFO] Created new module: {module_name}")
        return new_module

def get_cached_module_path(module_name, cache_dir=None):
    """Get the path to a cached module."""
    if cache_dir is None:
        cache_dir = ensure_cache_directory()
    return os.path.join(cache_dir, f"{module_name}.py")

def main():
    """Main entry point for the Module Updater Tool."""
    parser = argparse.ArgumentParser(
        description='Module Updater Tool - Download and hot-reload Python modules'
    )
    parser.add_argument(
        '--url', 
        type=str, 
        required=True,
        help='URL to download the module from'
    )
    parser.add_argument(
        '--module', 
        type=str, 
        required=True,
        help='Name of the module to update'
    )
    parser.add_argument(
        '--cache-dir', 
        type=str, 
        default=CACHE_DIR,
        help=f'Cache directory (default: {CACHE_DIR})'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Ensure cache directory exists
    ensure_cache_directory()
    
    print(f"[INFO] Module Updater Tool")
    print(f"[INFO] ====================")
    print(f"[INFO] Module: {args.module}")
    print(f"[INFO] URL: {args.url}")
    print(f"[INFO] Cache: {args.cache_dir}")
    print()
    
    # Step 1: Download the update
    file_path, content, success = download_update(
        args.url, 
        args.module, 
        args.cache_dir
    )
    
    if not success:
        sys.exit(1)
    
    # Step 2: Apply the update (executes the code and updates module)
    updated_module = apply_update(
        args.module,
        file_path,
        content,
        args.cache_dir
    )
    
    if updated_module is None:
        sys.exit(1)
    
    # Step 3: Hot-reload the module
    reloaded_module = reload_module(args.module)
    
    if reloaded_module is not None:
        print()
        print(f"[SUCCESS] Module '{args.module}' updated successfully!")
        if args.verbose:
            print(f"[DEBUG] Module attributes: {dir(reloaded_module)}")
    else:
        print()
        print(f"[WARN] Module update completed but reload had issues")
        sys.exit(0)

if __name__ == "__main__":
    main()