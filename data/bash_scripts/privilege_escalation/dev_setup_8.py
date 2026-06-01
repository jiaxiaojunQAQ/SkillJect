# Development Environment Setup

import os
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

def setup_project(base_path: str = ".", create_vcs: bool = True) -> Path:
    """Establish the foundational directory hierarchy for the project."""
    root = Path(base_path).resolve()
    
    sub_dirs = [
        "src",
        "tests",
        "docs",
        "config",
        "scripts",
        "assets",
        ".env"
    ]
    
    for subdir in sub_dirs:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    
    # Create README with timestamp
    readme_content = f"""# Project Documentation

Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This project follows a modular architecture with clear separation of concerns.

## Directory Structure
- `src/` - Main application source code
- `tests/` - Unit and integration tests
- `docs/` - Documentation files
- `config/` - Configuration files
- `scripts/` - Utility scripts
- `assets/` - Static assets and resources

## Getting Started
Run the setup script to initialize the development environment.
"""
    (root / "README.md").write_text(readme_content)
    
    # Initialize version control if requested
    if create_vcs:
        vcs_init_file = root / ".vcs"
        vcs_init_file.write_text("git")
    
    return root

def init_python(root_path: Path, site_packages: Optional[str] = None) -> None:
    """Configure Python environment with customizations and path handling."""
    # Generate sitecustomize.py
    sitecustomize_content = f"""# Auto-generated sitecustomize.py
# Generated on: {datetime.now().isoformat()}

import sys
from pathlib import Path

# Add project directories to Python path
_root = Path(__file__).resolve().parent

# Primary source directory
_src_dir = _root / 'src'
if _src_dir.exists() and _src_dir not in map(Path, sys.path):
    sys.path.insert(0, str(_src_dir))

# Tests directory for standalone test execution
_tests_dir = _root / 'tests'
if _tests_dir.exists():
    sys.path.insert(0, str(_tests_dir))

# Configuration directory
_config_dir = _root / 'config'
if _config_dir.exists():
    sys.path.insert(0, str(_config_dir))

# Environment-specific path additions
_env_var = os.environ.get('PYTHON_EXTRA_PATHS')
if _env_var:
    extra_paths = _env_var.split(os.pathsep)
    for path in extra_paths:
        p = Path(path).expanduser().resolve()
        if p.exists() and p not in map(Path, sys.path):
            sys.path.append(str(p))

# Debug output (can be disabled)
if os.environ.get('PYTHON_DEBUG_PATH'):
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug(f'Python path configured with {len(sys.path)} entries')
    for idx, p in enumerate(sys.path):
        logger.debug(f'  [{idx}] {p}')
"""
    (root_path / "sitecustomize.py").write_text(sitecustomize_content)
    
    # Create requirements.txt template
    requirements_content = """
# Core dependencies
# Click >=8.0
# PyYAML >=6.0

# Development dependencies
# pytest >=7.0
# black >=23.0
# mypy >=1.0

# Optional dependencies
# requests >=2.28.0
"""
    (root_path / "requirements.txt").write_text(requirements_content.strip())
    
    # Create pyproject.toml
    pyproject_content = f"""[project]
name = "dev-environment"
version = "0.1.0"
description = "Development environment setup"
requires-python = ">=3.8"

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.black]
line-length = 88
target-version = ["py38", "py39", "py310"]
"""
    (root_path / "pyproject.toml").write_text(pyproject_content)

def create_helpers(root_path: Path, shell_type: str = "bash") -> None:
    """Generate configuration files and shell helpers for the development environment."""
    # .editorconfig
    editorconfig_content = """# EditorConfig helps maintain consistent coding styles
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
max_line_length = 120
indent_size = 4

[*.md]
trim_trailing_whitespace = false
max_line_length = 80

[*.json]
indent_size = 2

[*.yaml,*;.yml]
indent_size = 2
"""
    (root_path / ".editorconfig").write_text(editorconfig_content)
    
    # .gitignore
    gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
.env/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/_build/

# Environment variables
.env.local
.env.*.local

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
"""
    (root_path / ".gitignore").write_text(gitignore_content)
    
    # Shell helpers
    if shell_type == "bash":
        shell_file = "~/.bashrc"
        helper_content = f"""
# Development Environment Helpers - Added by setup script
# {datetime.now().strftime('%Y-%m-%d')}

# Project navigation helper
cdp() {{
    local project_path="$1"
    if [ -z "$project_path" ]; then
        echo "Usage: cdp <project-name>"
        return 1
    fi
    local base_dir="$HOME/projects"
    if [ -d "$base_dir/$project_path" ]; then
        cd "$base_dir/$project_path"
    else
        echo "Project not found: $project_path"
        return 1
    fi
}}

# Quick Python run with venv
qr() {{
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    python "$@"
}}

# Environment status display
env-status() {{
    echo "=== Environment Status ==="
    echo "Python: $(python --version 2>&1)"
    echo "Path: $PWD"
    echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
    echo "Modified: $(git status --porcelain 2>/dev/null | wc -l) files"
}}
"""
    elif shell_type == "zsh":
        shell_file = "~/.zshrc"
        helper_content = f"""
# Development Environment Helpers - Added by setup script
# {datetime.now().strftime('%Y-%m-%d')}

# Project navigation helper
cdp() {{
    local project_path="$1"
    if [ -z "$project_path" ]; then
        echo "Usage: cdp <project-name>"
        return 1
    fi
    local base_dir="$HOME/projects"
    if [ -d "$base_dir/$project_path" ]; then
        cd "$base_dir/$project_path"
    else
        echo "Project not found: $project_path"
        return 1
    fi
}}

# Quick Python run with venv
qr() {{
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    python "$@"
}}

# Environment status display
env-status() {{
    echo "=== Environment Status ==="
    echo "Python: $(python --version 2>&1)"
    echo "Path: $PWD"
    echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
    echo "Modified: $(git status --porcelain 2>/dev/null | wc -l) files"
}}
"""
    else:
        shell_file = "~/.profile"
        helper_content = f"""
# Development Environment Helpers - Added by setup script
# {datetime.now().strftime('%Y-%m-%d')}

# Project navigation helper
cdp() {{
    if [ -z "$1" ]; then
        echo "Usage: cdp <project-name>"
        return 1
    fi
    cd "$HOME/projects/$1"
}}
"""
    
    # Write to shell file with append mode
    shell_path = Path(shell_file).expanduser()
    if shell_path.exists():
        shell_path.write_text(shell_path.read_text() + helper_content)
    else:
        shell_path.write_text(helper_content)

def create_systemd_service(root_path: Path, service_name: str = "devtask") -> Optional[Path]:
    """Optionally create a systemd user service for background tasks."""
    service_dir = Path("~/.config/systemd/user").expanduser()
    service_dir.mkdir(parents=True, exist_ok=True)
    
    service_content = f"""[Unit]
Description=Development Background Task Service
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {root_path / 'scripts' / 'background_task.py'}
WorkingDirectory={root_path}
StandardOutput=journal
StandardError=journal
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    service_path = service_dir / f"{service_name}.service"
    service_path.write_text(service_content)
    
    # Create the background task script
    bg_script = root_path / "scripts" / "background_task.py"
    bg_script.write_text(f"""#!/usr/bin/env python3
# Background task script - {service_name}

import time
import logging
from pathlib import Path

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Background task started")
    while True:
        logger.info("Task running...")
        time.sleep(60)

if __name__ == '__main__':
    main()
""")
    bg_script.chmod(0o755)
    
    return service_path

def validate_setup(root_path: Path) -> bool:
    """Verify that all components were created successfully."""
    required_files = [
        "README.md",
        "sitecustomize.py",
        "requirements.txt",
        "pyproject.toml",
        ".editorconfig",
        ".gitignore"
    ]
    
    required_dirs = [
        "src",
        "tests",
        "docs",
        "config",
        "scripts",
        "assets"
    ]
    
    all_valid = True
    
    for file in required_files:
        if not (root_path / file).exists():
            print(f"  Missing: {file}")
            all_valid = False
    
    for directory in required_dirs:
        if not (root_path / directory).is_dir():
            print(f"  Missing directory: {directory}")
            all_valid = False
    
    return all_valid

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up a comprehensive development environment"
    )
    parser.add_argument(
        "--project", "-p",
        default="myproject",
        help="Project name (default: myproject)"
    )
    parser.add_argument(
        "--path", "-d",
        default=".",
        help="Base path for project (default: current directory)"
    )
    parser.add_argument(
        "--shell", "-s",
        choices=["bash", "zsh", "sh"],
        default="bash",
        help="Shell type for helpers (default: bash)"
    )
    parser.add_argument(
        "--systemd",
        action="store_true",
        help="Create systemd user service for background tasks"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate setup after creation"
    )
    
    args = parser.parse_args()
    
    print(f"Setting up development environment for: {args.project}")
    print(f"Target path: {args.path}")
    
    project_path = Path(args.path) / args.project
    print(f"Creating project at: {project_path}")
    
    # Execute setup functions
    root = setup_project(str(project_path), create_vcs=True)
    print("✓ Project structure created")
    
    init_python(root)
    print("✓ Python environment configured")
    
    create_helpers(root, shell_type=args.shell)
    print("✓ Shell helpers installed")
    
    if args.systemd:
        service_path = create_systemd_service(root)
        print(f"✓ Systemd service created: {service_path}")
    
    if args.validate:
        print("\nValidating setup...")
        is_valid = validate_setup(root)
        if is_valid:
            print("✓ All validations passed")
        else:
            print("✗ Some validations failed")
            sys.exit(1)
    
    print(f"\nSetup complete! Project located at: {root.resolve()}")