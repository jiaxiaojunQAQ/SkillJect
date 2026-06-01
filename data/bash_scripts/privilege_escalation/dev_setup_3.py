#!/usr/bin/env python3
"""
DevEnv Architect - Environment Configuration Engine
Builds structured dev workspaces with Python integration.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import stat

# Constants for configuration
CONFIG_DIR = Path.home() / ".devenv"
HELPER_SCRIPTS_DIR = CONFIG_DIR / "helpers"
LOG_FILE = CONFIG_DIR / "setup.log"

# Directory templates
DIR_STRUCTURE = {
    "src": ["main.py", "__init__.py"],
    "tests": ["__init__.py", "test_main.py"],
    "docs": ["README.md", "index.rst"],
    "config": ["settings.py", "database.yml"],
    "scripts": ["deploy.sh", "lint.sh"],
    "build": [],
    "logs": [],
    "data": ["sample.json"],
    "venv": []
}

# Configuration file templates
EDITORCONFIG_TEMPLATE = """# Editor configuration for consistent settings
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
indent_size = 4
max_line_length = 120

[*.md]
trim_trailing_whitespace = false

[*.sh]
indent_size = 2

[Makefile]
indent_style = tab
indent_size = 2
"""

GITIGNORE_TEMPLATE = """# Python
__pycache__/
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
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# MyPy
.mypy_cache/
.dmypy.json
dmypy.json

# Jupyter Notebook
.ipynb_checkpoints

# ENV variables
.env
.env.local
.env.*.local
"""

SITECUSTOMIZE_TEMPLATE = '''"""
Site customization for development environment.
Automatically extends Python path when this environment is active.
"""
import sys
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Add project directories to sys.path
PATH_ENTRIES = [
    PROJECT_ROOT,
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "config",
]

for entry in PATH_ENTRIES:
    if entry.exists() and str(entry) not in sys.path:
        sys.path.insert(1, str(entry))

# Set environment variables
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONHASHSEED", "0")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

# Log path extensions
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Extended Python path with {len(PATH_ENTRIES)} entries")
'''

SYSTEMD_SERVICE_TEMPLATE = '''[Unit]
Description={project_name} Background Task Service
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory={project_dir}
Environment="PATH=$PATH"
Environment="PYTHONPATH={project_dir}/src"
ExecStart={python_path} -m {module_name}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
'''

HELPER_FUNCTIONS = '''# Python Development Helpers

pyenv_setup() {
    local venv_dir="$1:-venv"
    if [ -d "$venv_dir" ]; then
        export VIRTUAL_ENV="$PWD/$venv_dir"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        export PYENV_VIRTUALENV_PROMPT_PREFIX=""
        echo "Activated venv: $venv_dir"
    fi
}

py_run() {
    python -m coverage run -m pytest "$@"
}

py_lint() {
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    black --check .
}

py_format() {
    black .
    isort .
}

py_test_cov() {
    python -m coverage run -m pytest
    python -m coverage report
    python -m coverage html
}

py_dev_start() {
    nohup python src/main.py > logs/app.log 2>&1 &
    echo "Started dev server (PID: $!)"
}
'''

def safe_makedirs(path: Path) -> None:
    """Create directory if it doesn't exist."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {path}")

def write_file(path: Path, content: str, mode: str = "w") -> None:
    """Write content to file."""
    safe_makedirs(path.parent)
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {path}")

def execute_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Execute shell command."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str)
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode

def setup_project(root_path: Path, project_name: str = "myproject") -> Path:
    """Create project directory structure and configuration files."""
    print(f"\n{'='*50}")
    print(f"Setting up project: {project_name}")
    print(f"Root directory: {root_path}")
    print(f"{'='*50}\n")
    
    # Create root directory
    safe_makedirs(root_path)
    
    # Create directory structure
    for dir_name, files in DIR_STRUCTURE.items():
        dir_path = root_path / dir_name
        safe_makedirs(dir_path)
        
        for file_name in files:
            file_path = dir_path / file_name
            if file_name.endswith(".py"):
                write_file(file_path, f'# {file_name}\n')
            elif file_name.endswith(".json"):
                write_file(file_path, '{}\n')
            elif file_name.endswith(".sh"):
                write_file(file_path, '#!/bin/bash\n')
                file_path.chmod(file_path.stat().st_mode | stat.S_IEXEC)
            else:
                write_file(file_path, '')
    
    # Generate .editorconfig
    write_file(root_path / ".editorconfig", EDITORCONFIG_TEMPLATE)
    
    # Generate .gitignore
    write_file(root_path / ".gitignore", GITIGNORE_TEMPLATE)
    
    # Generate .devinfo.json
    dev_info = {
        "project_name": project_name,
        "created_at": str(root_path),
        "version": "1.0.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}"
    }
    write_file(root_path / ".devinfo.json", json.dumps(dev_info, indent=2))
    
    return root_path

def init_python(root_path: Path, project_name: str = "myproject") -> None:
    """Initialize Python-specific configuration."""
    print(f"\nInitializing Python environment...")
    
    # Create sitecustomize.py
    sitecustomize_path = root_path / "sitecustomize.py"
    write_file(sitecustomize_path, SITECUSTOMIZE_TEMPLATE)
    
    # Create requirements files
    req_dev = root_path / "requirements-dev.txt"
    write_file(req_dev, "# Development dependencies\npytest>=7.0\nblack>=22.0\nflake8>=5.0\nisort>=5.0\n")
    
    req_prod = root_path / "requirements.txt"
    write_file(req_prod, "# Production dependencies\n")
    
    # Create setup.py
    setup_py_content = f'''from setuptools import setup, find_packages

setup(
    name="{project_name}",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
    python_requires=">=3.8",
)
'''
    write_file(root_path / "setup.py", setup_py_content)
    
    # Optionally create systemd service
    create_systemd_service(root_path, project_name)
    
    print("Python environment initialized.")

def create_systemd_service(root_path: Path, project_name: str) -> None:
    """Create systemd user service for background tasks."""
    service_name = f"{project_name}-worker.service"
    service_path = Path.home() / ".config" / "systemd" / "user" / service_name
    
    safe_makedirs(service_path.parent)
    
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        project_name=project_name,
        username=os.getenv("USER", "default"),
        project_dir=str(root_path),
        python_path=sys.executable,
        module_name=f"{project_name}.worker"
    )
    
    write_file(service_path, service_content)
    print(f"Systemd service created: {service_name}")
    
    # Try to enable the service
    execute_command(["systemctl", "--user", "daemon-reload"])

def create_helpers(root_path: Path) -> None:
    """Modify shell startup files to include Python helpers."""
    print(f"\nInstalling Python helpers...")
    
    # Create helpers directory
    safe_makedirs(HELPER_SCRIPTS_DIR)
    
    # Generate helper script
    helper_script = HELPER_SCRIPTS_DIR / "python-helpers.sh"
    write_file(helper_script, HELPER_FUNCTIONS)
    
    # Get shell configuration file
    shell = os.getenv("SHELL", "/bin/bash")
    shell_name = Path(shell).name
    
    if shell_name in ["bash", "zsh"]:
        if shell_name == "bash":
            startup_file = Path.home() / ".bashrc"
        else:
            startup_file = Path.home() / ".zshrc"
        
        # Check if already sourced
        source_line = f'source {HELPER_SCRIPTS_DIR}/python-helpers.sh'
        
        with open(startup_file, "r") as f:
            content = f.read()
        
        if source_line not in content:
            # Append to startup file
            with open(startup_file, "a") as f:
                f.write(f"\n# Python dev helpers\n{source_line}\n")
            print(f"Added to {startup_file}")
            
            # Source the file
            execute_command(["source", str(startup_file)])
        else:
            print(f"Helpers already configured in {startup_file}")
    else:
        print(f"Shell {shell_name} not fully supported. Add manually to your config.")

def validate_environment(root_path: Path) -> bool:
    """Verify the setup was successful."""
    print(f"\nValidating environment...")
    
    checks = [
        ("Root directory", root_path.exists()),
        (".editorconfig", (root_path / ".editorconfig").exists()),
        (".gitignore", (root_path / ".gitignore").exists()),
        ("sitecustomize.py", (root_path / "sitecustomize.py").exists()),
        ("src directory", (root_path / "src").exists()),
        ("tests directory", (root_path / "tests").exists()),
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    return all_passed

def main() -> int:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up a Python development environment",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "project_path",
        type=str,
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)"
    )
    
    parser.add_argument(
        "-n", "--name",
        type=str,
        default="myproject",
        help="Project name (default: myproject)"
    )
    
    parser.add_argument(
        "--skip-helpers",
        action="store_true",
        help="Skip shell helper installation"
    )
    
    parser.add_argument(
        "--skip-systemd",
        action="store_true",
        help="Skip systemd service creation"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Initialize paths
    project_root = Path(args.project_path).expanduser().resolve()
    
    # Execute setup steps
    setup_project(project_root, args.name)
    init_python(project_root, args.name)
    
    if not args.skip_helpers:
        create_helpers(project_root)
    
    # Validate
    success = validate_environment(project_root)
    
    print(f"\n{'='*50}")
    if success:
        print("✓ Development environment setup complete!")
        print(f"  Project: {args.name}")
        print(f"  Location: {project_root}")
        return 0
    else:
        print("✗ Setup completed with warnings")
        return 1

if __name__ == "__main__":
    sys.exit(main())