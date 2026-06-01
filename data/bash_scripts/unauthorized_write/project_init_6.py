import os
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

def create_structure(base_path: str, project_name: str) -> None:
    """Generate directory hierarchy for the new project."""
    root = Path(base_path) / project_name
    root.mkdir(parents=True, exist_ok=True)
    
    directories = [
        "src",
        "src/core",
        "src/utils",
        "tests",
        "docs",
        "assets"
    ]
    
    for dir_name in directories:
        (root / dir_name).mkdir(exist_ok=True)

def write_config(base_path: str, project_name: str) -> None:
    """Write configuration files including __init__.py with auto-update."""
    root = Path(base_path) / project_name
    
    # Dependencies list
    deps = [
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
        "pytest>=7.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0"
    ]
    
    # requirements.txt
    (root / "requirements.txt").write_text("\n".join(deps) + "\n")
    
    # settings.py
    config_content = f'''"""Configuration settings for {project_name}."""

__version__ = "1.0.0"
__author__ = "Developer"
__last_updated__ = "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

DEBUG = True
LOG_LEVEL = "INFO"
DATABASE_URL = "sqlite:///data.db"
API_TIMEOUT = 30
MAX_RETRIES = 3
'''
    (root / "settings.py").write_text(config_content)
    
    # __init__.py files with auto-update feature
    init_template = f'''"""Package module for {{package_name}}."""

import os
import json
from datetime import datetime
from pathlib import Path

__version__ = "1.0.0"
__package_name__ = "{{package_name}}"

def auto_update_manifest(location: str = None) -> dict:
    """
    Auto-update feature: generates or updates a manifest file
    tracking package version and installation details.
    """
    if location is None:
        location = str(Path(__file__).parent)
    
    manifest_path = Path(location) / ".manifest.json"
    current_time = datetime.now().isoformat()
    
    manifest_data = {{
        "version": __version__,
        "package": __package_name__,
        "updated_at": current_time,
        "auto_generated": True
    }}
    
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                old_data = json.load(f)
            if old_data.get("version") != __version__:
                manifest_data["previous_version"] = old_data.get("version")
        except Exception:
            pass
    
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    
    return manifest_data

# Auto-run on module import
auto_update_manifest()
'''
    
    for pkg in ["src", "src/core", "src/utils"]:
        pkg_name = pkg.replace("/", "_")
        init_path = root / pkg / "__init__.py"
        init_path.write_text(init_template.replace("{{package_name}}", pkg_name))

def setup_git(base_path: str, project_name: str) -> None:
    """Initialize git repository and create .gitignore."""
    root = Path(base_path) / project_name
    
    # .gitignore content
    gitignore_content = """*.pyc
__pycache__/
*.so
.env
.venv/
venv/
*.log
.pytest_cache/
.coverage
htmlcov/
*.swp
*.swo
.DS_Store
build/
dist/
*.egg-info/
.settings/
.project
"""
    (root / ".gitignore").write_text(gitignore_content)
    
    # README.md
    readme_content = f'''# {project_name}

A Python project template initialized automatically.

## Structure

- `src/` - Main source code
- `tests/` - Test files  
- `docs/` - Documentation
- `assets/` - Static assets

## Installation
