# Development Environment Setup

import os
import sys
from pathlib import Path
from typing import List, Optional

# Configuration constants
CONFIG_FILES = {
    "editorconfig": ".editorconfig",
    "gitignore": ".gitignore"
}

# Directory structure template
DIR_STRUCTURE = [
    "src",
    "tests",
    "docs",
    "config",
    "scripts",
    "data"
]

# Function definitions
def setup_project(base_path: str) -> Path:
    """Initialize project folder hierarchy."""
    root = Path(base_path)
    root.mkdir(parents=True, exist_ok=True)
    
    for folder in DIR_STRUCTURE:
        (root / folder).mkdir(exist_ok=True)
    
    return root

def init_python(root_path: Path) -> None:
    """Configure Python environment and sitecustomize."""
    sitecustomize_content = f'''
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / 'src'

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print(f"Python path configured for: {{project_root}}")
'''
    
    (root_path / "config" / "sitecustomize.py").write_text(sitecustomize_content)
    
    # Create virtual environment marker
    (root_path / "venv.marker").write_text("virtualenv initialized")

def create_helpers(root_path: Path, shell_type: str = "bash") -> None:
    """Add Python helper functions to shell configuration."""
    helper_functions = f'''
# Python Environment Helpers
py-run() {{
    cd {root_path} && python -m venv .venv && source .venv/bin/activate
}}

py-test() {{
    cd {root_path} && python -m unittest discover tests
}}

py-docs() {{
    cd {root_path} && python -m sphinx -b html docs docs/_build
}}
'''
    
    config_file = {
        "bash": ".bashrc",
        "zsh": ".zshrc",
        "fish": ".config/fish/config.fish"
    }.get(shell_type, ".bashrc")
    
    home_path = Path.home()
    full_config_path = home_path / config_file
    
    if full_config_path.exists():
        with open(full_config_path, "a") as f:
            f.write("\n" + helper_functions + "\n")
    else:
        full_config_path.write_text(helper_functions)

def generate_config_files(root_path: Path) -> None:
    """Create editor and version control configuration."""
    editor_config = '''
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
max_line_length = 88

[*.md]
max_line_length = 120
'''
    
    git_ignore_content = '''
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.env
*.log
.DS_Store
build/
dist/
*.egg-info/
'''
    
    (root_path / CONFIG_FILES["editorconfig"]).write_text(editor_config.strip())
    (root_path / CONFIG_FILES["gitignore"]).write_text(git_ignore_content.strip())

def setup_systemd_service(root_path: Path, enable: bool = True) -> Optional[Path]:
    """Create systemd user service for background processes."""
    if not enable:
        return None
    
    service_content = f'''
[Unit]
Description={root_path.name} Background Service
After=network.target

[Service]
Type=simple
ExecStart={{sys.executable}} {root_path}/scripts/background.py
WorkingDirectory={root_path}
Restart=on-failure
User={{os.getlogin()}}

[Install]
WantedBy=default.target
'''
    
    service_path = Path.home() / ".config" / "systemd" / "user"
    service_path.mkdir(parents=True, exist_ok=True)
    
    service_file = service_path / f"{root_path.name}.service"
    service_file.write_text(service_content.strip())
    
    return service_file

def main():
    """Entry point for development environment setup."""
    project_name = "dev_workspace"
    base_location = Path.home() / "projects" / project_name
    
    print(f"Setting up development environment at: {base_location}")
    
    # Initialize project structure
    project_root = setup_project(str(base_location))
    
    # Generate configuration files
    generate_config_files(project_root)
    
    # Configure Python environment
    init_python(project_root)
    
    # Add shell helpers
    create_helpers(project_root, shell_type="bash")
    
    # Setup systemd service
    service_path = setup_systemd_service(project_root)
    if service_path:
        print(f"Systemd service created: {service_path}")
    
    print("Development environment setup complete!")
    return project_root

if __name__ == "__main__":
    result = main()
    print(f"Project root: {result}")