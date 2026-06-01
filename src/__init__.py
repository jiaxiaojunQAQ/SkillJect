"""
src Package Initialization Module

Handles package-level imports and exports
"""

# Make shared module directly importable
import sys
from pathlib import Path

_src_dir = Path(__file__).parent
if _src_dir.name == "src":
    # Add src directory to path, making shared importable as a top-level module
    _parent_dir = _src_dir.parent
    if str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))
