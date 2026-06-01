Here is the Python script implementing the project initialization tool with the specified requirements and a distinct implementation style.

```python
# Project Initialization Tool

import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration Constants
DEFAULT_STRUCTURE = [
    "src",
    "src/core",
    "src/utils",
    "tests",
    "config",
    "docs",
    "assets",
    "assets/images"
]

COMMON_DEPS = [
    "requests>=2.28.0",
    "python-dotenv>=1.0.0",
    "pytest>=7.2.0",
    "click>=8.1.0",
    "pyyaml>=6.0"
]

GITIGNORE_CONTENT = """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
env/
.venv/

# IDE specific
.idea/
.vscode/

# OS generated files
.DS_Store
Thumbs.db

# Project specific
.env
*.log
dist/
build/
"""

README_TEMPLATE = """
# Project: {project_name}

## Description
A brief description of the project goes here.

## Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application

## License
MIT License
"""

# --- Internal Helper Functions ---

def _format_date():
    """Returns current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def _create_file(filepath, content):
    """Creates a file and writes content to it."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except IOError as e:
        print(f"Error writing {filepath}: {e}")
        return False

# --- Core Functions ---

def create_structure(root_path):
    """
    Iterates through defined structure and creates directories.
    Uses os.makedirs for recursive creation.
    """
    created_dirs = []
    for folder in DEFAULT_STRUCTURE:
        full_path = os.path.join(root_path, folder)
        if os.path.exists(full_path):
            continue
        os.makedirs(full_path)
        created_dirs.append(folder)
        # Create __init__.py in package directories
        if folder.startswith("src"):
            init_path = os.path.join(full_path, "__init__.py")
            _create_file(init_path, f"# Package initialization for {folder}")
            created_dirs.append(f"{folder}/__init__.py")
    return created_dirs

def write_config(root_path):
    """
    Generates requirements.txt, config.py, and README.md.
    """
    # 1. Generate Requirements
    req_path = os.path.join(root_path, "requirements.txt")
    req_content = "\n".join(COMMON_DEPS) + "\n"
    _create_file(req_path, req_content)

    # 2. Generate Config
    config_path = os.path.join(root_path, "config", "config.py")
    config_content = f"""
# Configuration File
# Generated on {_format_date()}

DEBUG = True
DEBUG_MODE = True
LOG_LEVEL = "INFO"
DATABASE_URL = "sqlite:///default.db"
SECRET_KEY = "default-secret-key-change-me"
API_VERSION = "v1"
"""
    _create_file(config_path, config_content)

    # 3. Generate README
    readme_path = os.path.join(root_path, "README.md")
    project_name = os.path.basename(root_path)
    _create_file(readme_path, README_TEMPLATE.format(project_name=project_name))

def setup_git(root_path):
    """
    Creates .gitignore and initializes git repository if git command is available.
    """
    gitignore_path = os.path.join(root_path, ".gitignore")
    _create_file(gitignore_path, GITIGNORE_CONTENT.strip())
    
    # Attempt to initialize git
    import subprocess
    try:
        subprocess.check_call(["git", "init"], cwd=root_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Git repository initialized in {root_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git not found or initialization failed.")

# --- Main Execution Block ---

if __name__ == "__main__":
    # Determine target directory (default to current dir or argument)
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"Initializing project structure in: {target_dir}")
    
    # Execute steps
    created_items = create_structure(target_dir)
    write_config(target_dir)
    setup_git(target_dir)
    
    print("\nInitialization complete!")
    print(f"Created {len(created_items)} items.")