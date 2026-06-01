"""
Instruction File Scanner

Scans skill directories for supporting files to provide filename information for instruction generation.
"""

from dataclasses import dataclass
from pathlib import Path

# File type description mapping
FILE_TYPE_DESCRIPTIONS: dict[str, str] = {
    ".fasta": "protein sequence",
    ".fa": "protein sequence",
    ".txt": "text data",
    ".json": "JSON data",
    ".yaml": "YAML configuration",
    ".yml": "YAML configuration",
    ".md": "markdown content",
    ".csv": "CSV data",
    ".tsv": "TSV data",
    ".xml": "XML data",
    ".html": "HTML content",
    ".pdf": "PDF document",
    ".docx": "Word document",
    ".xlsx": "Excel spreadsheet",
    ".png": "PNG image",
    ".jpg": "JPEG image",
    ".jpeg": "JPEG image",
    ".gif": "GIF image",
    ".svg": "SVG image",
    ".py": "Python script",
    ".js": "JavaScript file",
    ".ts": "TypeScript file",
    ".sh": "Shell script",
    ".bat": "Batch script",
    ".sql": "SQL script",
}


@dataclass
class ScanResult:
    """Scan result"""

    skill_name: str
    supporting_files: list[Path]
    file_descriptions: dict[str, str]
    has_instruction: bool


class InstructionFileScanner:
    """Instruction file scanner

    Scans skill directories, identifies supporting files and generates description information.
    """

    # Default exclude file patterns
    EXCLUDE_PATTERNS = [
        "instruction.md",
        "*.bak",
        "SKILL.md",
        ".gitkeep",
        "README.md",
    ]

    # Default include file extensions
    INCLUDE_EXTENSIONS = {
        ".fasta",
        ".fa",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".md",
        ".csv",
        ".tsv",
        ".xml",
        ".html",
        ".py",
        ".js",
        ".ts",
        ".sh",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
    }

    def __init__(
        self,
        base_dir: Path | None = None,
        exclude_patterns: list[str] | None = None,
        include_extensions: set[str] | None = None,
    ):
        """Initialize the scanner

        Args:
            base_dir: Base directory (optional, for relative path resolution)
            exclude_patterns: List of file patterns to exclude
            include_extensions: Set of file extensions to include
        """
        self._base_dir = base_dir
        self._exclude_patterns = exclude_patterns or self.EXCLUDE_PATTERNS.copy()
        self._include_extensions = include_extensions or self.INCLUDE_EXTENSIONS.copy()

    def scan_all_skills(self, base_dir: Path) -> dict[str, list[Path]]:
        """Scan all skill directories

        Args:
            base_dir: Skills base directory

        Returns:
            Dictionary with skill names as keys and lists of supporting file paths as values
        """
        if not base_dir.exists():
            return {}

        results = {}

        for skill_dir in base_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            supporting_files = self.get_supporting_files(skill_dir)

            if supporting_files:
                results[skill_name] = supporting_files

        return results

    def get_supporting_files(self, skill_dir: Path) -> list[Path]:
        """Get list of supporting files for a single skill directory

        Args:
            skill_dir: Skill directory path

        Returns:
            List of supporting file paths (excluding instruction.md and backup files)
        """
        if not skill_dir.exists() or not skill_dir.is_dir():
            return []

        supporting_files = []

        for file_path in skill_dir.iterdir():
            if not file_path.is_file():
                continue

            # Check if this file should be excluded
            if self._should_exclude(file_path):
                continue

            # Check if extension is in the include list
            if file_path.suffix.lower() in self._include_extensions:
                supporting_files.append(file_path)

        # Sort by filename
        return sorted(supporting_files, key=lambda p: p.name)

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded

        Args:
            file_path: File path

        Returns:
            Whether to exclude
        """
        filename = file_path.name.lower()

        # Check exclude patterns
        for pattern in self._exclude_patterns:
            pattern_lower = pattern.lower()
            # Simple wildcard matching
            if pattern_lower.startswith("*."):
                # Extension match
                if filename.endswith(pattern_lower[1:]):
                    return True
            elif pattern_lower == filename:
                # Exact match
                return True
            elif pattern_lower in filename:
                # Partial match (like .bak)
                return True

        return False

    def format_file_list(self, files: list[Path]) -> str:
        """Format file list as an instruction-friendly string

        Args:
            files: List of file paths

        Returns:
            Formatted file information string
        """
        if not files:
            return "No supporting files available."

        lines = ["**Available Supporting Files:**\n"]

        for file_path in files:
            description = self.get_file_description(file_path)
            lines.append(f"- `{file_path.name}`: {description}")

        return "\n".join(lines)

    def get_file_description(self, file_path: Path) -> str:
        """Get file type description

        Args:
            file_path: File path

        Returns:
            File type description
        """
        suffix = file_path.suffix.lower()

        # Find predefined description
        if suffix in FILE_TYPE_DESCRIPTIONS:
            return FILE_TYPE_DESCRIPTIONS[suffix]

        # Try to infer from filename
        name_lower = file_path.name.lower()

        if "protein" in name_lower or "sequence" in name_lower:
            return "protein sequence data"
        elif "config" in name_lower:
            return "configuration file"
        elif "data" in name_lower:
            return "data file"
        elif "input" in name_lower:
            return "input file"
        elif "output" in name_lower:
            return "output file"
        elif "sample" in name_lower or "example" in name_lower:
            return "sample data"
        elif "test" in name_lower:
            return "test data"
        elif "readme" in name_lower:
            return "documentation"
        elif "notes" in name_lower:
            return "notes"
        elif "requirement" in name_lower:
            return "requirements"
        else:
            return f"{suffix or 'text'} file"

    def scan_skill(self, skill_dir: Path) -> ScanResult:
        """Scan a single skill directory

        Args:
            skill_dir: Skill directory path

        Returns:
            Scan result
        """
        skill_name = skill_dir.name
        supporting_files = self.get_supporting_files(skill_dir)

        # Build file description dictionary
        file_descriptions: dict[str, str] = {}
        for file_path in supporting_files:
            file_descriptions[file_path.name] = self.get_file_description(file_path)

        # Check if instruction.md exists
        has_instruction = (skill_dir / "instruction.md").exists()

        return ScanResult(
            skill_name=skill_name,
            supporting_files=supporting_files,
            file_descriptions=file_descriptions,
            has_instruction=has_instruction,
        )

    def get_filenames_only(self, files: list[Path]) -> list[str]:
        """Get list of filenames (without paths)

        Args:
            files: List of file paths

        Returns:
            List of filenames
        """
        return [f.name for f in files]

    def validate_instruction_files(
        self, instruction: str, filenames: list[str]
    ) -> tuple[bool, list[str]]:
        """Validate if instruction contains all filenames

        Args:
            instruction: Instruction text
            filenames: Expected list of filenames

        Returns:
            (Is valid, List of missing filenames)
        """
        instruction_lower = instruction.lower()
        missing_files = []

        for filename in filenames:
            # Check if filename is in instruction
            if filename.lower() not in instruction_lower:
                missing_files.append(filename)

        return len(missing_files) == 0, missing_files
