import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Get evaluation root directory (4 levels up from current file)
_EVALUATION_ROOT = Path(__file__).parent.parent.parent.parent

# Resource file paths
RESOURCE_FILES_DIR = _EVALUATION_ROOT / "data"
INFORMATION_DISCLOSURE_RESOURCE = RESOURCE_FILES_DIR / ".env"
UNAUTHORIZED_WRITE_RESOURCE = RESOURCE_FILES_DIR / "main.py"

# Instruction directory
INSTRUCTION_BASE_DIR = _EVALUATION_ROOT / "data" / "instruction"


def resolve_data_path(path: str | Path) -> Path:
    """Resolve data path.

    If relative path is passed, resolve relative to evaluation root directory.
    If absolute path, use directly.

    Args:
        path: Path (relative or absolute)

    Returns:
        Resolved Path object
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return _EVALUATION_ROOT / path


def get_project_paths(config_path: str | Path | None = None) -> dict[str, str]:
    """Get project path configuration.

    Args:
        config_path: Configuration file path, for dynamically calculating test_dir.
                    If None, get from EVALUATION_CONFIG_PATH environment variable

    Returns:
        Dictionary containing various directory paths
    """
    # Get current file's directory
    current_dir = Path(__file__).parent

    # Search up for project root directory (directory containing data and src directories)
    project_root = current_dir
    for _ in range(4):  # Up to 4 levels up
        parent = project_root.parent
        if (parent / "data").exists() or (parent / "src").exists():
            project_root = parent
            break
        project_root = parent

    # If still not found, use current directory's parent
    if not (project_root / "data").exists():
        project_root = Path.cwd()

    # Dynamically calculate test_dir from configuration
    test_dir = _compute_test_dir(config_path, project_root)

    return {
        "base_dir": str(project_root),
        "skills_from_skill0_dir": str(project_root / "data" / "skills_from_skill0"),
        "skills_instructions_dir": str(project_root / "data" / "skills_instructions"),
        "generated_tests_dir": str(project_root / "generated_tests"),
        "test_dir": test_dir,
    }


def _compute_test_dir(config_path: str | Path | None, project_root: Path) -> str:
    """Calculate test_dir based on configuration.

    Args:
        config_path: Configuration file path
        project_root: Project root directory

    Returns:
        Test directory path
    """
    # If config path not provided, try getting from environment variable
    if config_path is None:
        config_path = os.environ.get("EVALUATION_CONFIG_PATH")

    # If still no config path, use default path
    if config_path is None:
        # Try to find default configuration files
        default_configs = [
            project_root / "config" / "main.yaml",
            project_root / "config" / "template_injection.yaml",
            project_root / "evaluation" / "config" / "main.yaml",
            project_root / "evaluation" / "config" / "template_injection.yaml",
        ]
        for default_path in default_configs:
            if default_path.exists():
                config_path = default_path
                break

    # If config file found, load and calculate test_dir
    if config_path is not None:
        try:
            from src.infrastructure.config.loaders.config_loader import ConfigLoader

            config = ConfigLoader.load(config_path)
            return str(config.generation.computed_output_dir)
        except Exception as exc:
            # If loading fails, fall back to default path
            logger.debug(
                "Falling back to default test directory because config loading failed: %s",
                exc,
            )

    # Default fallback path
    return str(project_root / "generated_tests" / "skills_from_skill0" / "template_injection")
