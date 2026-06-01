"""
Skill Loader

Provides functionality to load skill content and auxiliary files from
skills_from_skill0 and skills_instructions directories.
"""

from pathlib import Path

from .paths import get_project_paths, resolve_data_path


def get_skills_from_skill0_dir() -> Path:
    """Get skills_from_skill0 directory path."""
    paths = get_project_paths()
    return Path(paths["skills_from_skill0_dir"])


def get_skills_instructions_dir() -> Path:
    """Get skills_instructions directory path."""
    paths = get_project_paths()
    return Path(paths["skills_instructions_dir"])


def load_skill_content(skill_name: str) -> str | None:
    """
    Load SKILL.md content from skills_from_skill0.

    Args:
        skill_name: skill name (directory name)

    Returns:
        SKILL.md file content, or None if not exists
    """
    skill_file = get_skills_from_skill0_dir() / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text(encoding="utf-8")


def load_user_instruction(skill_name: str) -> str | None:
    """
    Load instruction.md content from skills_instructions.

    Args:
        skill_name: skill name

    Returns:
        instruction.md file content, or None if not exists
    """
    instruction_file = get_skills_instructions_dir() / skill_name / "instruction.md"
    if not instruction_file.exists():
        return None
    return instruction_file.read_text(encoding="utf-8")


def has_instruction(skill_name: str) -> bool:
    """
    Check if skill has instruction file.

    Args:
        skill_name: skill name

    Returns:
        True if instruction.md exists
    """
    instruction_file = get_skills_instructions_dir() / skill_name / "instruction.md"
    return instruction_file.exists()


def get_instruction_auxiliary_files(skill_name: str) -> list[Path]:
    """
    Get auxiliary files in skill instruction directory.

    Args:
        skill_name: skill name

    Returns:
        List of auxiliary file paths (excluding instruction.md itself)
    """
    instruction_dir = get_skills_instructions_dir() / skill_name
    if not instruction_dir.exists():
        return []

    auxiliary_files = []
    for file_path in instruction_dir.iterdir():
        if file_path.is_file() and file_path.name != "instruction.md":
            # Skip Zone.Identifier files
            if ":Zone.Identifier" not in file_path.name:
                auxiliary_files.append(file_path)

    return auxiliary_files


def list_all_skills(base_dir: str | Path | None = None) -> list[str]:
    """
    List all available skill names.

    Args:
        base_dir: Skills directory path (uses default path if None)

    Returns:
        List of skill names (directory names containing SKILL.md)
    """
    if base_dir is None:
        base_dir = get_skills_from_skill0_dir()
    else:
        # Resolve relative path (relative to evaluation root directory)
        base_dir = resolve_data_path(base_dir)

    if not base_dir.exists():
        return []

    skill_names = []
    for skill_dir in base_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skill_names.append(skill_dir.name)

    return sorted(skill_names)


def list_skills_with_instructions() -> list[str]:
    """
    List all skill names that have instructions.

    Returns:
        List of skill names that have instruction.md
    """
    all_skills = list_all_skills()
    return [name for name in all_skills if has_instruction(name)]


def get_test_data_file(filename: str) -> Path | None:
    """
    Get test data file path.

    Args:
        filename: File name (e.g., ".env", "main.py")

    Returns:
        Path object for test data file, or None if not exists
    """
    paths = get_project_paths()
    base_dir = Path(paths["base_dir"])

    # Check test data files under data directory
    test_data_dir = base_dir / "data"
    test_file = test_data_dir / filename

    if test_file.exists():
        return test_file

    return None


def get_test_data_content(filename: str) -> str | None:
    """
    Get test data file content.

    Args:
        filename: File name (e.g., ".env", "main.py")

    Returns:
        Test data file content, or None if not exists
    """
    test_file = get_test_data_file(filename)
    if test_file:
        return test_file.read_text(encoding="utf-8")
    return None


def extract_original_skill_name(test_dir_name: str) -> str:
    """
    Extract original skill name from test directory name.

    Test directory name format: {skill_name}_{layer}_{attack_type}_{payload_name}_{severity}
    Example: scvi-tools_description_information_disclosure_env_disc_medium

    Args:
        test_dir_name: Test directory name

    Returns:
        Original skill name
    """
    # Split by underscore, take first part as skill name
    # Note: some skill names may contain underscores (scvi-tools doesn't)
    # Common pattern: skillname_layer_attacktype_payloadname_severity
    parts = test_dir_name.split("_")

    # Check common layer names to locate boundary
    layer_indicators = ["description", "instruction", "resource"]

    for i, part in enumerate(parts):
        if part in layer_indicators:
            # skill name is the part before layer name
            return "_".join(parts[:i])

    # If no layer indicator found, return first part
    return parts[0] if parts else test_dir_name
