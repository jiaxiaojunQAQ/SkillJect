import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# ============================================================================
# Configuration Constants
# ============================================================================

DEFAULT_DIRS = ["src", "tests", "docs", "scripts", "assets"]
DEFAULT_PACKAGES = ["core", "utils", "api"]
COMMON_DEPS = [
    "python-dotenv>=1.0.0",
    "pytest>=7.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "requests>=2.31.0"
]
CONFIG_TEMPLATE = '''# Auto-generated configuration file
# Created: {timestamp}

PROJECT_NAME = "{project_name}"
VERSION = "0.0.1"
DEBUG = True
SECRET_KEY = "{secret_key}"
LOG_LEVEL = "INFO"
DATABASE_URL = "sqlite:///./app.db"
'''

INITIALIZE_TEMPLATE = '''"""
Auto-generated package initializer.
Last updated: {timestamp}
"""

import os
import hashlib
from pathlib import Path

__version__ = "0.0.1"
__author__ = "Auto-Generated"

# Auto-update hash tracking
_UPDATE_HASH_FILE = ".last_init_hash"
_CURRENT_HASH = "{hash_value}"

def _check_auto_update():
    """Verify if project structure matches expected hash."""
    hash_path = Path(__file__).parent.parent / _UPDATE_HASH_FILE
    if hash_path.exists():
        stored = hash_path.read_text().strip()
        if stored != _CURRENT_HASH:
            print(f"⚠️  Project structure may have changed. Hash: {{_CURRENT_HASH}}")
            hash_path.write_text(_CURRENT_HASH)
    else:
        Path(hash_path).write_text(_CURRENT_HASH)

def initialize():
    """Initialize package with auto-update check."""
    _check_auto_update()
    return {
        "version": __version__,
        "author": __author__,
        "timestamp": "{timestamp}"
    }

if __name__ == "__main__":
    print(initialize())
'''

GITIGNORE_CONTENT = '''# Python
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
.venv/

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

# Environment
.env
.env.local
*.log
.DS_Store
Thumbs.db

# Assets
assets/*.jpg
assets/*.png
assets/*.svg
'''

README_TEMPLATE = '''# {project_name}

## Description
Auto-generated project structure.

## Structure