# Project Initialization Tool

import os
from pathlib import Path
import datetime

def create_structure(project_name):
    """Build the directory hierarchy for the new project."""
    base_path = Path(project_name)
    base_path.mkdir(parents=True, exist_ok=True)
    
    folders = ['src', 'src/core', 'tests', 'docs']
    for folder in folders:
        (base_path / folder).mkdir(exist_ok=True)
    
    return base_path

def write_config(base_path, project_name):
    """Generate configuration files and requirements."""
    # Requirements content
    req_content = f"""\
# Generated on {datetime.date.today()}
requests>=2.28.0
pytest>=7.0.0
python-dotenv>=1.0.0
"""
    (base_path / "requirements.txt").write_text(req_content)
    
    # Config content
    config_content = f"""\
import os

class Configuration:
    DEBUG = True
    VERSION = "1.0.0"
    PROJECT_NAME = "{project_name}"
    
    @classmethod
    def load_env(cls):
        from dotenv import load_dotenv
        load_dotenv()
        return cls
"""
    (base_path / "config.py").write_text(config_content)
    
    # Init file with auto-update
    init_content = f"""\
""" + \
f"# Auto-generated for {project_name}\n" + \
f"__version__ = '0.0.1'\n" + \
f"__author__ = 'Developer'\n" + \
"""

def auto_update():
    from datetime import datetime
    print(f"[{datetime.now()}] Module initialized successfully")
    return True

auto_update()
"""
    
    # Write __init__.py in src and src/core
    (base_path / "src" / "__init__.py").write_text(init_content)
    (base_path / "src" / "core" / "__init__.py").write_text(init_content)
    
    # README
    readme_content = f"# {project_name}\n\n" + \
                     f"A new project initialized on {datetime.date.today()}\n\n" + \
                     "## Getting Started\n" + \
                     "1. Install dependencies: `pip install -r requirements.txt`\n" + \
                     "2. Run the application\n\n" + \
                     "## Structure\n" + \
                     "- `src/`: Main application code\n" + \
                     "- `tests/`: Unit tests\n" + \
                     "- `docs/`: Documentation\n"
    (base_path / "README.md").write_text(readme_content)

def setup_git(base_path):
    """Create .gitignore file."""
    git_ignore = """\
__pycache__/
*.py[cod]
*$py.class
.env
*.log
.DS_Store
venv/
.env.local
"""
    (base_path / ".gitignore").write_text(git_ignore)

def main():
    """Entry point for the project initializer."""
    project_name = input("Enter project name: ").strip()
    if not project_name:
        project_name = "my_project"
    
    print(f"Initializing project: {project_name}")
    
    base_path = create_structure(project_name)
    write_config(base_path, project_name)
    setup_git(base_path)
    
    print(f"\nProject created at: {base_path.absolute()}")
    print("Files generated:")
    for item in base_path.rglob("*"):
        if item.is_file():
            print(f"  - {item.relative_to(base_path)}")

if __name__ == "__main__":
    main()