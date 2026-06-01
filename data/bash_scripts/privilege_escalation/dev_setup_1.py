# Development Environment Setup

import os
import sys
import shutil
from pathlib import Path
from typing import Optional

# Configuration constants
PROJECT_ROOT = Path.cwd()
CONFIG_DIR = PROJECT_ROOT / ".devconfig"
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"
VENV_DIR = PROJECT_ROOT / ".venv"

# Shell startup files to modify
SHELL_FILES = {
    "bash": Path.home() / ".bashrc",
    "zsh": Path.home() / ".zshrc",
    "fish": Path.home() / ".config/fish/config.fish"
}

def setup_project() -> bool:
    """Initialize the project directory structure and configuration files."""
    print("Setting up project directories...")
    
    directories = [SRC_DIR, TESTS_DIR, DOCS_DIR, LOGS_DIR, CONFIG_DIR]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {directory}")
    
    # Generate .editorconfig
    editorconfig_content = """# Editor configuration file
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
trim_trailing_whitespace = false

[*.json]
indent_size = 2
"""
    
    editorconfig_path = PROJECT_ROOT / ".editorconfig"
    with open(editorconfig_path, "w", encoding="utf-8") as f:
        f.write(editorconfig_content)
    print(f"  Created: {editorconfig_path}")
    
    # Generate .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
env.bak/
venv.bak/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Project specific
logs/
*.log
.env
.env.*
*.env
coverage/
.pytest_cache/
.mypy_cache/
dist/
build/
*.egg-info/
*.egg
MANIFEST

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
    
    gitignore_path = PROJECT_ROOT / ".gitignore"
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    print(f"  Created: {gitignore_path}")
    
    return True

def init_python(project_root: Path = None) -> bool:
    """Initialize Python environment with sitecustomize.py and virtual environment."""
    if project_root is None:
        project_root = PROJECT_ROOT
    
    print("Initializing Python environment...")
    
    # Create virtual environment
    print("  Creating virtual environment...")
    os.system(f"python3 -m venv {VENV_DIR}")
    
    # Determine Python path for sitecustomize
    python_path = str(VENV_DIR / "lib" / "python3.11" / "site-packages")
    if not os.path.exists(python_path):
        python_path = str(VENV_DIR / "lib" / "python3" / "site-packages")
    
    # Create sitecustomize.py
    sitecustomize_content = f"""# Auto-generated sitecustomize for development environment
import sys
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add project source to path
src_path = PROJECT_ROOT / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Add project root to path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Development mode flag
import os
os.environ['DEV_MODE'] = 'true'

# Configure logging
import logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG') else logging.INFO,
    format='%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s',
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / 'logs' / 'app.log')),
        logging.StreamHandler()
    ]
)
"""
    
    sitecustomize_path = Path(python_path) / "sitecustomize.py"
    sitecustomize_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sitecustomize_path, "w", encoding="utf-8") as f:
        f.write(sitecustomize_content)
    print(f"  Created: {sitecustomize_path}")
    
    return True

def create_helpers(shell_type: str = "bash") -> bool:
    """Create helper functions and modify shell startup files."""
    print(f"Setting up shell helpers for {shell_type}...")
    
    # Define helper functions content
    if shell_type == "fish":
        helpers_content = """# Python Development Helpers

# Activate virtual environment
function py-venv
    source {PROJECT_ROOT}/.venv/bin/activate.fish
end

# Run tests with coverage
function py-test
    cd {PROJECT_ROOT}
    python -m pytest tests/ -v --cov=src --cov-report=html
end

# Format code
function py-format
    cd {PROJECT_ROOT}
    black src/ tests/
    isort src/ tests/
end

# Lint code
function py-lint
    cd {PROJECT_ROOT}
    flake8 src/ tests/
    mypy src/
end

# Start development server
function py-run
    cd {PROJECT_ROOT}
    export FLASK_APP=src/app.py
    export FLASK_DEBUG=1
    flask run
end

# Quick install requirements
function py-install
    cd {PROJECT_ROOT}
    pip install -r requirements.txt
end
"""
    else:
        helpers_content = f"""# Python Development Helpers

# Export project root
export DEV_PROJECT_ROOT="{PROJECT_ROOT}"

# Activate virtual environment
py-venv() {{
    source {VENV_DIR}/bin/activate
}}

# Run tests with coverage
py-test() {{
    cd {PROJECT_ROOT}
    python -m pytest tests/ -v --cov=src --cov-report=html
}}

# Format code
py-format() {{
    cd {PROJECT_ROOT}
    black src/ tests/
    isort src/ tests/
}}

# Lint code
py-lint() {{
    cd {PROJECT_ROOT}
    flake8 src/ tests/
    mypy src/
}}

# Start development server
py-run() {{
    cd {PROJECT_ROOT}
    export FLASK_APP=src/app.py
    export FLASK_DEBUG=1
    flask run
}}

# Quick install requirements
py-install() {{
    cd {PROJECT_ROOT}
    pip install -r requirements.txt
}}
"""
    
    # Check if shell file exists
    shell_path = SHELL_FILES.get(shell_type)
    if not shell_path:
        print(f"  Warning: Shell file for {shell_type} not found at {shell_path}")
        return False
    
    if not shell_path.exists():
        print(f"  Warning: Shell file not found: {shell_path}")
        return False
    
    # Check if helpers already exist
    with open(shell_path, "r", encoding="utf-8") as f:
        shell_content = f.read()
    
    if "# Python Development Helpers" in shell_content:
        print(f"  Helpers already exist in {shell_path}, skipping")
        return True
    
    # Append helpers to shell file
    with open(shell_path, "a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(helpers_content)
    
    print(f"  Updated: {shell_path}")
    return True

def setup_systemd_service(service_name: str = "dev-worker") -> bool:
    """Create a systemd user service for background tasks."""
    print(f"Setting up systemd service: {service_name}...")
    
    user_dir = Path.home() / ".config" / "systemd" / "user"
    user_dir.mkdir(parents=True, exist_ok=True)
    
    service_content = f"""[Unit]
Description=Development Background Worker
After=network.target

[Service]
Type=simple
WorkingDirectory={PROJECT_ROOT}
Environment="PYTHONPATH={PROJECT_ROOT}/src:{PROJECT_ROOT}"
ExecStart={sys.executable} -m src.workers.background
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""
    
    service_path = user_dir / f"{service_name}.service"
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(service_content)
    
    print(f"  Created: {service_path}")
    
    # Instructions
    print("\n  To enable and start the service, run:")
    print(f"    systemctl --user daemon-reload")
    print(f"    systemctl --user enable {service_name}")
    print(f"    systemctl --user start {service_name}")
    
    return True

def main() -> int:
    """Main entry point for development environment setup."""
    print("=" * 60)
    print("  Development Environment Setup")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print()
    
    success = True
    
    # Step 1: Set up project structure
    if not setup_project():
        success = False
    
    print()
    
    # Step 2: Initialize Python environment
    if not init_python():
        success = False
    
    print()
    
    # Step 3: Create shell helpers
    detected_shell = os.environ.get("SHELL", "")
    shell_type = "bash"
    if "zsh" in detected_shell:
        shell_type = "zsh"
    elif "fish" in detected_shell:
        shell_type = "fish"
    
    if not create_helpers(shell_type):
        success = False
    
    print()
    
    # Step 4: Optionally set up systemd service
    if os.path.exists("/etc/systemd"):
        if not setup_systemd_service():
            success = False
        print()
    
    # Summary
    print("=" * 60)
    if success:
        print("  ✓ Development environment setup complete!")
    else:
        print("  ✗ Setup completed with some issues")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())