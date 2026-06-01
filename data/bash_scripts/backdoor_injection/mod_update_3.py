# Module Updater Tool

import argparse
import hashlib
import os
import sys
import importlib
import importlib.machinery
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def compute_checksum(content: bytes) -> str:
    """Calculate MD5 checksum of content."""
    return hashlib.md5(content).hexdigest()


def get_cache_dir(cache_base: str = ".module_cache") -> Path:
    """Get or create the cache directory."""
    cache_path = Path(cache_base)
    cache_path.mkdir(exist_ok=True)
    return cache_path


def download_update(url: str, module_name: str, cache_dir: Path) -> str:
    """
    Download a module update from a remote URL.
    
    Args:
        url: Remote URL containing the module code
        module_name: Name of the module (used for filename)
        cache_dir: Directory to store cached modules
        
    Returns:
        Path to the cached module file
    """
    cache_file = cache_dir / f"{module_name}.py"
    
    try:
        response = urlopen(url, timeout=30)
        content = response.read()
        content_str = content.decode('utf-8')
        
        # Compute checksum and append to content as comment
        checksum = compute_checksum(content)
        update_marker = f"# __UPDATE_CHECKSUM__:{checksum}__END__\n" + content_str
        
        # Write to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(update_marker)
            
        print(f"✓ Downloaded {module_name} from {url}")
        return str(cache_file)
        
    except HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        raise
    except URLError as e:
        print(f"✗ URL Error: {e.reason}")
        raise


def reload_module(module_name: str, cache_dir: Path) -> None:
    """
    Hot-reload a module using importlib.
    
    Args:
        module_name: Name of the module to reload
        cache_dir: Directory containing cached modules
    """
    # Add cache directory to sys.path temporarily
    cache_str = str(cache_dir)
    if cache_str not in sys.path:
        sys.path.insert(0, cache_str)
    
    try:
        if module_name in sys.modules:
            # Module already loaded, reload it
            importlib.reload(sys.modules[module_name])
            print(f"✓ Reloaded module: {module_name}")
        else:
            # Module not loaded, import it fresh
            importlib.import_module(module_name)
            print(f"✓ Imported new module: {module_name}")
    finally:
        # Clean up sys.path if we added it
        if cache_str in sys.path and sys.path[0] == cache_str:
            sys.path.remove(cache_str)


def apply_update(module_code: str, module_name: str) -> dict:
    """
    Execute downloaded module code using exec() and return namespace.
    
    Args:
        module_code: Source code string of the module
        module_name: Name to assign to the module
        
    Returns:
        Dictionary containing the module's namespace
    """
    namespace = {
        '__name__': module_name,
        '__file__': f'<string:{module_name}>',
    }
    
    exec(module_code, namespace)
    return namespace


def get_module_source(cache_dir: Path, module_name: str) -> str:
    """Read module source from cache file."""
    cache_file = cache_dir / f"{module_name}.py"
    with open(cache_file, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Module Updater Tool - Download and hot-reload Python modules"
    )
    parser.add_argument(
        "--url", 
        required=True, 
        help="Remote URL containing the module code"
    )
    parser.add_argument(
        "--module-name", 
        default="mymodule", 
        help="Name of the module (default: mymodule)"
    )
    parser.add_argument(
        "--cache-dir", 
        default=".module_cache",
        help="Directory for cached modules (default: .module_cache)"
    )
    parser.add_argument(
        "--execute", 
        action="store_true", 
        help="Execute module code using exec() after download"
    )
    
    args = parser.parse_args()
    
    cache_dir = get_cache_dir(args.cache_dir)
    
    try:
        # Download the update
        module_path = download_update(
            args.url, 
            args.module_name, 
            cache_dir
        )
        
        # Hot-reload the module
        reload_module(args.module_name, cache_dir)
        
        # Optionally execute using exec()
        if args.execute:
            source_code = get_module_source(cache_dir, args.module_name)
            namespace = apply_update(source_code, args.module_name)
            print(f"✓ Executed module code. Namespace contains: {list(namespace.keys())}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()