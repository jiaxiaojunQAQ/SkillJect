# Development Environment Setup

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# ============================================================================
# Configuration Constants
# ============================================================================

DEFAULT_PROJECT_NAME = "dev_workspace"
CONFIG_VERSION = "1.0.3"
SHELL_STARTUP_FILES = {
    "bash": ".bashrc",
    "zsh": ".zshrc",
    "sh": ".profile"
}

# ============================================================================
# Configuration Templates
# ============================================================================

EDITORCONFIG_TEMPLATE = """# EditorConfig helps maintain consistent coding styles
# https://editorconfig.org

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

[*.md]
trim_trailing_whitespace = false

[*.sh]
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
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/
.env

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
.env.local
*.log
tmp/
"""

SITECUSTOMIZE_TEMPLATE = '''"""
Sitecustomize configuration for development environment.
Automatically executed when Python starts.
"""
import sys
from pathlib import Path

def _extend_python_path(base_path: str = "{project_name}") -> None:
    """Extend sys.path to include project directories."""
    base_dir = Path(base_path).expanduser().resolve()
    
    paths_to_add = [
        str(base_dir),
        str(base_dir / "src"),
        str(base_dir / "lib"),
        str(base_dir / "scripts"),
    ]
    
    for path_str in paths_to_add:
        path = Path(path_str)
        if path.exists() and path.is_dir():
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
                print(f"[DEV] Added to sys.path: {{path_str}}")

if __name__ == "__main__" or getattr(sys, "frozen", False):
    _extend_python_path()
'''

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Development Background Service for {project_name}
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory=/home/{username}/{project_name}
ExecStart=/usr/bin/python3 -m {project_name}.background_task
Restart=on-failure
RestartSec=5s
Environment=PYTHONPATH=/home/{username}/{project_name}
Environment=DEV_ENV=true

[Install]
WantedBy=default.target
"""

HELPER_FUNCTIONS_TEMPLATE = """
# Python Development Helpers - Generated on {{date}}

# Activate virtual environment if it exists
activate_venv() {{
    if [[ -d "$1/venv" ]]; then
        source "$1/venv/bin/activate"
        echo "Virtual environment activated: $1/venv"
    fi
}}

# Quick project creation
mkproject() {{
    local name="${{1:?Project name required}}"
    mkdir -p "$name"/{{src,tests,docs,scripts}}
    touch "$name"/{{setup.py,README.md,.gitignore,.editorconfig}}
    cd "$name"
    git init
    echo "Project '$name' created with basic structure"
}}

# Run Python with development settings
dev-python() {{
    export PYTHONPATH="$PWD:$PWD/src:$PWD/lib:$PYTHONPATH"
    export DEV_ENV=true
    python3 "$@"
}}

# Install development dependencies
install_dev_deps() {{
    if [[ -f requirements-dev.txt ]]; then
        pip install -r requirements-dev.txt
    elif [[ -f requirements.txt ]]; then
        pip install -r requirements.txt --upgrade
    fi
}}
"""

# ============================================================================
# Core Functions
# ============================================================================

def setup_project(root_path: str, project_name: str = DEFAULT_PROJECT_NAME) -> Path:
    """Create the complete project directory structure."""
    
    project_root = Path(root_path) / project_name
    subdirectories = ["src", "tests", "docs", "scripts", "config", "data", "tmp"]
    
    print(f"Creating project structure at: {project_root}")
    
    # Create main directories
    project_root.mkdir(parents=True, exist_ok=True)
    
    for subdir in subdirectories:
        (project_root / subdir).mkdir(exist_ok=True)
    
    # Create README file
    readme_path = project_root / "README.md"
    if not readme_path.exists():
        readme_path.write_text(f"# {project_name}\n\nDevelopment project created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return project_root


def init_python(project_root: Path, project_name: str) -> None:
    """Initialize Python configuration including sitecustomize."""
    
    # Create __init__.py files for src modules
    src_dir = project_root / "src"
    if src_dir.exists():
        (src_dir / "__init__.py").write_text(f"\"\"\"{project_name} source module.\"\"\"\n")
    
    # Create sitecustomize.py
    sitecustomize_path = project_root / "sitecustomize.py"
    sitecustomize_path.write_text(
        SITECUSTOMIZE_TEMPLATE.format(project_name=project_name)
    )
    print(f"Created sitecustomize.py: {sitecustomize_path}")
    
    # Create setup.py
    setup_path = project_root / "setup.py"
    if not setup_path.exists():
        setup_content = f'''from setuptools import setup, find_packages

setup(
    name="{project_name}",
    version="{CONFIG_VERSION}",
    packages=find_packages("src"),
    package_dir={{"": "src"}},
    python_requires=">=3.8",
)
'''
        setup_path.write_text(setup_content)


def create_helpers(project_root: Path, project_name: str, username: str = None) -> None:
    """Generate configuration files and shell helpers."""
    
    if username is None:
        import getpass
        username = getpass.getuser()
    
    # Create .editorconfig
    editorconfig_path = project_root / ".editorconfig"
    editorconfig_path.write_text(EDITORCONFIG_TEMPLATE)
    print(f"Created .editorconfig")
    
    # Create .gitignore
    gitignore_path = project_root / ".gitignore"
    gitignore_path.write_text(GITIGNORE_TEMPLATE)
    print(f"Created .gitignore")
    
    # Create systemd service file
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    
    service_path = service_dir / f"{project_name}.service"
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        project_name=project_name,
        username=username
    )
    service_path.write_text(service_content)
    print(f"Created systemd service: {service_path}")
    
    # Update shell startup file with helpers
    shell_config = _find_shell_startup_file()
    if shell_config:
        _append_to_shell_startup(shell_config, project_name, project_root)
        print(f"Updated shell config: {shell_config}")


def _find_shell_startup_file() -> Path | None:
    """Detect and return the appropriate shell startup file."""
    
    shell_name = os.environ.get("SHELL", "")
    
    for shell_type, filename in SHELL_STARTUP_FILES.items():
        if shell_name.endswith(shell_type):
            return Path.home() / filename
    
    # Default to .bashrc
    return Path.home() / ".bashrc"


def _append_to_shell_startup(shell_path: Path, project_name: str, project_root: Path) -> None:
    """Append Python helper functions to shell startup file."""
    
    helpers_content = HELPER_FUNCTIONS_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        project_name=project_name,
        project_root=str(project_root)
    )
    
    separator = f"\n# ==============================================================================\n"
    header = f"# Python Helpers for {project_name}\n"
    
    shell_path.write_text(
        shell_path.read_text() + separator + header + helpers_content + "\n"
    )


def _parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    
    parser = argparse.ArgumentParser(
        description="Set up a development environment",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--project", "-p",
        default=DEFAULT_PROJECT_NAME,
        help=f"Project name (default: {DEFAULT_PROJECT_NAME})"
    )
    
    parser.add_argument(
        "--root", "-r",
        default=".",
        help="Root directory for project creation (default: current directory)"
    )
    
    parser.add_argument(
        "--skip-systemd",
        action="store_true",
        help="Skip creating systemd user service"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    args = _parse_arguments()
    
    print(f"\n{'='*60}")
    print(f"  Development Environment Setup v{CONFIG_VERSION}")
    print(f"{'='*60}\n")
    
    # Execute setup steps
    project_root = setup_project(args.root, args.project)
    
    print(f"\n[Step 1/3] Project structure created at: {project_root}")
    
    init_python(project_root, args.project)
    print(f"[Step 2/3] Python environment initialized")
    
    create_helpers(project_root, args.project)
    print(f"[Step 3/3] Helpers and configuration created")
    
    print(f"\n{'='*60}")
    print(f"  Setup complete! Project: {args.project}")
    print(f"{'='*60}\n")
    
    if args.verbose:
        print("Quick start commands:")
        print(f"  cd {project_root}")
        print(f"  python3 -c 'import sitecustomize; print(\"Path configured\")'")