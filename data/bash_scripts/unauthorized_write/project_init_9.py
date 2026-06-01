# Project Initialization Tool
import os
import sys
from pathlib import Path
from datetime import datetime

__version__ = "1.0.0"

DIRS_TO_CREATE = [
    "src",
    "src/core",
    "src/utils",
    "src/modules",
    "tests",
    "docs",
    "config"
]

DEFAULT_REQUIREMENTS = """
flask>=2.0.0
pytest>=7.0.0
python-dotenv>=1.0.0
requests>=2.28.0
pyyaml>=6.0
"""

GITIGNORE_CONTENT = """
__pycache__/
*.pyc
.env
.DS_Store
venv/
.idea/
*.log
dist/
build/
"""

README_TEMPLATE = """
# {project_name}

A Python project initialized on {date}.

## Requirements
