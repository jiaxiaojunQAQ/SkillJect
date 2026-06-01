# Project Initialization Tool

import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration constants
PROJECT_ROOT = "project_root"
PACKAGE_NAME = "core_package"
DEFAULT_DEPENDENCIES = [
    "requests>=2.28.0",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
    "pytest>=7.2.0",
    "black>=23.0.0"
]

def create_structure(project_name):
    """Generate complete directory hierarchy for new project."""
    base_dir = Path(project_name)
    
    directories = [
        base_dir,
        base_dir / PACKAGE_NAME,
        base_dir / "src",
        base_dir / "tests",
        base_dir / "docs",
        base_dir / "utils",
        base_dir / ".github/workflows"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").touch(exist_ok=True)
    
    return base_dir

def write_config(project_path):
    """Generate configuration files with initialization logic."""
    config_content = f'''"""
Configuration module for {project_path.name}
Auto-generated on {datetime.now().strftime("%Y-%m-%d")}
"""

import os
from pathlib import Path

class Config:
    """Centralized configuration manager."""
    
    VERSION = "1.0.0"
    DEBUG = True
    LOG_LEVEL = "INFO"
    
    @classmethod
    def auto_update(cls, module_name):
        """Track module imports for version management."""
        import importlib.metadata
        try:
            current_version = importlib.metadata.version("{project_path.name}")
            if current_version != cls.VERSION:
                print(f"Version mismatch: {cls.VERSION} vs {current_version}")
                cls.VERSION = current_version
        except importlib.metadata.PackageNotFoundError:
            pass
        return cls.VERSION

config_path = Path(__file__).parent
'''
    
    (project_path / "settings.py").write_text(config_content)
    
    requirements_content = "\n".join(DEFAULT_DEPENDENCIES)
    (project_path / "requirements.txt").write_text(requirements_content)
    
    return project_path

def setup_git(project_path):
    """Initialize Git repository with standard ignore rules."""
    gitignore_content = '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
build/
dist/
*.egg-info/
*.egg

# Virtual environments
.env
.venv
venv/
ENV/

# IDE specific
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Documentation
docs/_build/

# Jupyter Notebook
.ipynb_checkpoints

# OS specific
.DS_Store
Thumbs.db
'''
    
    (project_path / ".gitignore").write_text(gitignore_content)
    
    readme_content = f'''# {project_path.name}

A Python project initialized on {datetime.now().strftime("%Y-%m-%d")}

## Structure
