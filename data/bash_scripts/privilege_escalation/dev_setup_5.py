# Development Environment Setup

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Configuration constants
DEFAULT_PROJECT_NAME = "dev_workspace"
CONFIG_FILES = {
    ".editorconfig": [
        "[*]",
        "charset = utf-8",
        "end_of_line = lf",
        "insert_final_newline = true",
        "trim_trailing_whitespace = true",
        "indent_style = space",
        "indent_size = 4",
        "",
        "[*.py]",
        "max_line_length = 120",
        "indent_size = 4",
        "",
        "[*.md]",
        "max_line_length = 80",
        "trim_trailing_whitespace = false",
    ],
    ".gitignore": [
        "# Byte-compiled / optimized / DLL files",
        "__pycache__/",
        "*.py[cod]",
        "$py.class",
        "",
        "# Virtual environments",
        "venv/",
        ".venv/",
        "env/",
        "",
        "# IDE settings",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "",
        "# Testing",
        ".pytest_cache/",
        "htmlcov/",
        ".coverage",
        "",
        "# Distribution / packaging",
        "build/",
        "dist/",
        "*.egg-info/",
        "",
        "# Logs",
        "*.log",
        "logs/",
        "",
        "# Environment variables",
        ".env",
        ".env.local",
        "",
        "# OS generated files",
        "Thumbs.db",
        ".DS_Store",
    ],
}

SITECUSTOMIZE_TEMPLATE = '''"""
Site customization for Python development environment.
This module is automatically executed on Python startup.
"""

import sys
from pathlib import Path

# Get the base project directory
PROJECT_ROOT = Path(__file__).parent.parent / "{project_name}"

# Add project directories to sys.path
project_paths = [
    PROJECT_ROOT,
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "lib",
    PROJECT_ROOT / "scripts",
]

for p in project_paths:
    if p.exists() and p not in sys.path:
        sys.path.insert(1, str(p))

# Set environment variables
os = __import__('os')
os.environ["PROJECT_ROOT"] = str(PROJECT_ROOT)
os.environ["PYTHON_DEVELOPMENT_MODE"] = "true"

# Print startup message (can be disabled)
if os.environ.get("SHOW_PATH_INFO"):
    print(f"Python Path Initialized:")
    print(f"  Project Root: {{PROJECT_ROOT}}")
    print(f"  Active Paths: {{len(sys.path)}}")
'''

SYSTEMD_SERVICE_TEMPLATE = '''[Unit]
Description=Python Development Background Tasks
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory={project_path}
ExecStart={python_path} -m dev_helpers.background_tasks
Restart=on-failure
RestartSec=5
Environment="PYTHONPATH={project_path}/src:{project_path}/lib"

[Install]
WantedBy=default.target
'''

HELPER_MODULE_TEMPLATE = '''"""
Development helpers module.
Provides utility functions for the development environment.
"""

import os
import sys
from pathlib import Path
from typing import Generator, List
from contextlib import contextmanager
import subprocess


class DevHelpers:
    """Collection of development helper utilities."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(os.environ.get("PROJECT_ROOT", "."))
    
    def find_files(self, pattern: str = "*.py") -> Generator[Path, None, None]:
        """Recursively find files matching pattern."""
        return self.project_root.rglob(pattern)
    
    def run_command(self, cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
        """Execute a shell command."""
        return subprocess.run(cmd, capture_output=capture, text=True)
    
    @contextmanager
    def change_directory(self, path: Path):
        """Context manager to change directory temporarily."""
        original_dir = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(original_dir)
    
    def get_project_stats(self) -> dict:
        """Calculate project statistics."""
        stats = {
            "total_files": 0,
            "python_files": 0,
            "total_lines": 0,
        }
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                stats["total_files"] += 1
                if file_path.suffix == ".py":
                    stats["python_files"] += 1
                    stats["total_lines"] += sum(1 for _ in file_path.read_text().splitlines())
        return stats


def activate_dev_environment():
    """Activate the development environment."""
    dev_helpers = DevHelpers()
    print(f"Development Environment Activated")
    print(f"Project Root: {{dev_helpers.project_root}}")
    return dev_helpers


if __name__ == "__main__":
    helpers = activate_dev_environment()
    stats = helpers.get_project_stats()
    print(f"Statistics: {{stats}}")
'''


def setup_project(project_name: str = DEFAULT_PROJECT_NAME) -> Path:
    """
    Create the project directory structure.
    
    Args:
        project_name: Name of the project directory
        
    Returns:
        Path object pointing to the created project directory
    """
    project_dir = Path(project_name)
    
    # Directory structure to create
    structure = [
        project_dir,
        project_dir / "src",
        project_dir / "src" / "core",
        project_dir / "lib",
        project_dir / "tests",
        project_dir / "tests" / "unit",
        project_dir / "tests" / "integration",
        project_dir / "scripts",
        project_dir / "docs",
        project_dir / "config",
        project_dir / "logs",
        project_dir / "data",
        project_dir / "data" / "raw",
        project_dir / "data" / "processed",
    ]
    
    # Create directories
    created_dirs = []
    for directory in structure:
        directory.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(directory))
    
    print(f"✓ Created project structure: {{project_name}}")
    print(f"  Directories created: {{len(created_dirs)}}")
    
    # Create README.md
    readme_path = project_dir / "README.md"
    if not readme_path.exists():
        readme_content = f"""# {{project_name}}

Development project created on {{datetime.now().strftime('%Y-%m-%d')}}

## Structure

- `src/` - Source code
- `lib/` - Library modules
- `tests/` - Test suites
- `scripts/` - Utility scripts
- `docs/` - Documentation
- `config/` - Configuration files
- `logs/` - Log files
- `data/` - Data files

## Setup

Run this script to complete the environment setup.
"""
        readme_path.write_text(readme_content)
    
    return project_dir


def init_python(project_dir: Path, custom_path: str = None) -> Path:
    """
    Initialize Python environment with sitecustomize.py.
    
    Args:
        project_dir: Root project directory
        custom_path: Custom path for site-packages
        
    Returns:
        Path to sitecustomize.py
    """
    # Determine site-packages location
    if custom_path:
        site_packages = Path(custom_path)
    else:
        site_packages = Path(sys.prefix) / "lib" / f"python{{sys.version_info.major}}.{{sys.version_info.minor}}" / "site-packages"
    
    # Create site-packages if it doesn't exist
    site_packages.mkdir(parents=True, exist_ok=True)
    
    # Generate sitecustomize.py content
    sitecustomize_content = SITECUSTOMIZE_TEMPLATE.format(project_name=project_dir.name)
    
    # Write sitecustomize.py
    sitecustomize_path = site_packages / "sitecustomize.py"
    sitecustomize_path.write_text(sitecustomize_content)
    
    print(f"✓ Created sitecustomize.py at: {{sitecustomize_path}}")
    
    # Create __init__.py files for src and lib
    for subdir in ["src", "lib"]:
        init_file = project_dir / subdir / "__init__.py"
        init_file.write_text(f'# {{subdir}} package\n')
    
    return sitecustomize_path


def create_helpers(project_dir: Path) -> Path:
    """
    Create helper module and shell integration.
    
    Args:
        project_dir: Root project directory
        
    Returns:
        Path to the created helper module
    """
    # Create dev_helpers module
    helpers_dir = project_dir / "dev_helpers"
    helpers_dir.mkdir(exist_ok=True)
    
    helpers_path = helpers_dir / "__init__.py"
    helpers_path.write_text(HELPER_MODULE_TEMPLATE)
    
    # Create background_tasks.py
    background_path = helpers_dir / "background_tasks.py"
    background_content = '''"""
Background tasks for development environment.
"""

import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main background task loop."""
    logger.info("Background task started...")
    while True:
        logger.info("Running periodic task...")
        time.sleep(60)

if __name__ == "__main__":
    main()
'''
    background_path.write_text(background_content)
    
    print(f"✓ Created dev_helpers module at: {{helpers_dir}}")
    
    # Modify shell startup files
    shell_script = project_dir / "activate_dev.sh"
    shell_script.write_text(f'''#!/bin/bash
# Development Environment Activation Script
# Generated on {{datetime.now().strftime('%Y-%m-%d')}}

export PROJECT_ROOT="{project_dir.absolute()}"
export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/lib:$PROJECT_ROOT/dev_helpers:$PYTHONPATH"
export PYTHON_DEVELOPMENT_MODE="true"

alias pydev='python -m dev_helpers'
alias pytest-custom='pytest $PROJECT_ROOT/tests -v'

echo "Development environment activated for {{project_dir.name}}"
''')
    shell_script.chmod(0o755)
    
    print(f"✓ Created shell activation script: {{shell_script.name}}")
    
    return helpers_path


def create_systemd_service(project_dir: Path, username: str = None) -> Optional[Path]:
    """
    Optionally create systemd user service for background tasks.
    
    Args:
        project_dir: Root project directory
        username: Username for the service (defaults to current user)
        
    Returns:
        Path to service file or None if failed
    """
    if username is None:
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
    
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    
    service_path = service_dir / f"{{project_dir.name}}_dev.service"
    
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        username=username,
        project_path=str(project_dir.absolute()),
        python_path=sys.executable
    )
    
    service_path.write_text(service_content)
    
    print(f"✓ Created systemd service: {{service_path.name}}")
    
    # Try to reload systemd
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        print("  Systemd daemon reloaded")
    except Exception:
        pass
    
    return service_path


def apply_configuration_files(project_dir: Path) -> List[Path]:
    """
    Generate configuration files for the project.
    
    Args:
        project_dir: Root project directory
        
    Returns:
        List of paths to created configuration files
    """
    created_files = []
    
    for filename, content_lines in CONFIG_FILES.items():
        file_path = project_dir / filename
        content = "\n".join(content_lines) + "\n"
        file_path.write_text(content)
        created_files.append(file_path)
        print(f"✓ Created configuration: {{filename}}")
    
    # Create requirements.txt template
    requirements_path = project_dir / "requirements.txt"
    requirements_content = """# Development dependencies
pytest>=7.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0

# Runtime dependencies
# Add your project dependencies here
"""
    requirements_path.write_text(requirements_content)
    created_files.append(requirements_path)
    print(f"✓ Created requirements.txt")
    
    return created_files


def main():
    """Main entry point for development environment setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up Python development environment")
    parser.add_argument("project_name", nargs="?", default=DEFAULT_PROJECT_NAME,
                       help=f"Project name (default: {{DEFAULT_PROJECT_NAME}})")
    parser.add_argument("--systemd", action="store_true",
                       help="Create systemd user service")
    parser.add_argument("--custom-path", default=None,
                       help="Custom site-packages path")
    
    args = parser.parse_args()
    
    print(f"🚀 Setting up development environment for '{{args.project_name}}'")
    print("=" * 60)
    
    # Step 1: Create project structure
    project_dir = setup_project(args.project_name)
    
    # Step 2: Apply configuration files
    apply_configuration_files(project_dir)
    
    # Step 3: Initialize Python environment
    init_python(project_dir, args.custom_path)
    
    # Step 4: Create helpers
    create_helpers(project_dir)
    
    # Step 5: Optionally create systemd service
    if args.systemd:
        create_systemd_service(project_dir)
    
    print("=" * 60)
    print(f"✅ Development environment setup complete!")
    print(f"   Project directory: {{project_dir.absolute()}}")
    print(f"   Run '{{project_dir.name}}/activate_dev.sh' to activate")


if __name__ == "__main__":
    main()