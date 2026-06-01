# Development Environment Setup

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

DEFAULT_PROJECT_NAME = "my_project"
PROJECT_ROOT_ENV = "PROJECT_ROOT"

def setup_project(project_name: str, base_path: Path) -> Path:
    """Create the complete project directory structure."""
    project_path = base_path / project_name
    
    directories = [
        project_path,
        project_path / "src",
        project_path / "tests",
        project_path / "config",
        project_path / "docs",
        project_path / "scripts",
        project_path / "logs",
        project_path / "tmp",
        project_path / "src" / project_name,
        project_path / "tests" / project_name,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    return project_path

def init_python(project_path: Path, project_name: str) -> None:
    """Initialize Python environment with configuration files."""
    config_dir = project_path / "config"
    
    editor_config_path = project_path / ".editorconfig"
    if not editor_config_path.exists():
        editor_config_content = f"""# EditorConfig helps maintain consistent coding styles
root = true

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
max_line_length = 80

[*.json]
indent_size = 2

[*.yaml]
indent_size = 2

[Makefile]
indent_style = tab
indent_size = 2
"""
        with open(editor_config_path, 'w') as f:
            f.write(editor_config_content)
    
    gitignore_path = project_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_content = """__pycache__/
*.py[cod]
*$py.class
*.so
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
MANIFEST
.pytest_cache/
.coverage
htmlcov/
.env
.env.*
venv/
.venv/
env/
.envs/
local.env
*.log
.idea/
.vscode/
.DS_Store
Thumbs.db
*.swp
*.swo
*~
logs/
tmp/
*.db
*.sqlite3
config/local.*.yaml
config/local.*.json
"""
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
    
    sitecustomize_path = config_dir / "sitecustomize.py"
    sitecustomize_content = f'''# Auto-generated sitecustomize for {project_name}
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

os.environ["{PROJECT_ROOT_ENV}"] = str(project_root)

print(f"Python path configured for {{project_root}}")
'''
    with open(sitecustomize_path, 'w') as f:
        f.write(sitecustomize_content)
    
    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        pyproject_content = f'''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.1.0"
description = "Development environment setup"
requires-python = ">=3.8"

[tool.setuptools.packages.find]
where = ["src"]
'''
        with open(pyproject_path, 'w') as f:
            f.write(pyproject_content)

def create_helpers(project_path: Path, project_name: str, create_systemd: bool = True) -> None:
    """Create shell helpers and optionally systemd service."""
    helpers_dir = project_path / "scripts"
    
    python_helper_script = helpers_dir / "python_helper.sh"
    helper_content = f'''#!/bin/bash
# Python Helper Functions for {project_name}

py_run() {{
    cd {project_path} && python -m "{project_name}" "$@"
}}

py_test() {{
    cd {project_path} && python -m pytest "$@"
}}

py_lint() {{
    cd {project_path} && python -m flake8 "$@"
}}

py_format() {{
    cd {project_path} && python -m black "$@"
}}

export -f py_run py_test py_lint py_format
'''
    with open(python_helper_script, 'w') as f:
        f.write(helper_content)
    os.chmod(python_helper_script, 0o755)
    
    if create_systemd:
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        
        service_file = service_dir / f"{project_name}.service"
        service_content = f'''[Unit]
Description={project_name} Background Service
After=network.target

[Service]
Type=simple
WorkingDirectory={project_path}
ExecStart={sys.executable} -m {project_name}.background
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
'''
        with open(service_file, 'w') as f:
            f.write(service_content)
    
    shell_startup = Path.home() / ".bashrc"
    if shell_startup.exists():
        helper_source_line = f"source {python_helper_script}\n"
        with open(shell_startup, 'r') as f:
            content = f.read()
        
        if helper_source_line not in content:
            with open(shell_startup, 'a') as f:
                f.write(f"\n# {project_name} Python helpers\n")
                f.write(helper_source_line)

def main():
    parser = argparse.ArgumentParser(
        description="Set up a Python development environment"
    )
    parser.add_argument(
        "project_name",
        nargs="?",
        default=DEFAULT_PROJECT_NAME,
        help=f"Project name (default: {DEFAULT_PROJECT_NAME})"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base directory for project (default: current directory)"
    )
    parser.add_argument(
        "--no-systemd",
        action="store_true",
        help="Skip creating systemd user service"
    )
    
    args = parser.parse_args()
    
    print(f"Setting up development environment for '{args.project_name}'...")
    
    project_path = setup_project(args.project_name, args.base_path)
    print(f"✓ Created project directory structure at: {project_path}")
    
    init_python(project_path, args.project_name)
    print(f"✓ Initialized Python environment")
    
    create_helpers(project_path, args.project_name, not args.no_systemd)
    print(f"✓ Created shell helpers")
    
    if not args.no_systemd:
        print(f"✓ Created systemd user service")
    
    print(f"\nDevelopment environment setup complete!")
    print(f"Project root: {project_path}")
    print(f"Run 'source ~/.bashrc' to activate Python helpers")

if __name__ == "__main__":
    main()