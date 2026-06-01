# Development Environment Setup

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Configuration constants
CONFIG_VERSION = "2.1.0"
DEFAULT_PROJECT_NAME = "my_project"
LOG_PREFIX = "[SETUP]"

def setup_project(base_path, project_name=None):
    """Initialize the project directory structure."""
    target = Path(base_path) / (project_name or DEFAULT_PROJECT_NAME)
    
    structure = [
        "src",
        "tests",
        "docs",
        "config",
        "scripts",
        "logs"
    ]
    
    for folder in structure:
        (target / folder).mkdir(parents=True, exist_ok=True)
    
    print(f"{LOG_PREFIX} Created project at: {target}")
    return target

def init_python(project_root):
    """Configure Python environment including sitecustomize."""
    python_path = Path(project_root) / "src"
    sitecustomize_file = Path(project_root) / "sitecustomize.py"
    
    sitecustomize_content = f'''# Auto-generated on {datetime.now().strftime("%Y-%m-%d")}
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

print(f"Python path configured: {{SRC_PATH}}")
'''
    
    sitecustomize_file.write_text(sitecustomize_content)
    print(f"{LOG_PREFIX} Created sitecustomize.py")
    return sitecustomize_file

def create_helpers(project_root):
    """Generate configuration files and shell helpers."""
    editorconfig_content = '''root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
per_file
'''
    
    gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env/

# Project
logs/
*.log
config/local.yaml
'''
    
    (project_root / ".editorconfig").write_text(editorconfig_content)
    (project_root / ".gitignore").write_text(gitignore_content)
    print(f"{LOG_PREFIX} Created configuration files")
    return True

def main():
    """Main entry point."""
    base_path = Path("/home/user/projects")
    project_root = setup_project(base_path, "dev_environment")
    
    init_python(project_root)
    create_helpers(project_root)
    
    print(f"{LOG_PREFIX} Setup complete for {project_root.name}")

if __name__ == "__main__":
    main()