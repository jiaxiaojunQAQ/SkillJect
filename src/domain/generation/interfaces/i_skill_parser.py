"""
Skill File Parser Interface

Defines the abstract interface for parsing skill files
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillParseResult:
    """Skill parse result (value object)

    Attributes:
        frontmatter: Dictionary after parsing YAML frontmatter
        content: Body content (excluding frontmatter)
        raw_content: Original complete content
    """

    frontmatter: dict[str, Any]
    content: str
    raw_content: str

    def get_frontmatter_value(self, key: str, default: Any = None) -> Any:
        """Get value from frontmatter

        Args:
            key: Key name
            default: Default value

        Returns:
            Corresponding value or default
        """
        return self.frontmatter.get(key, default)

    def has_frontmatter_key(self, key: str) -> bool:
        """Check if frontmatter contains a key

        Args:
            key: Key name

        Returns:
            Whether the key is contained
        """
        return key in self.frontmatter


class ISkillParser(ABC):
    """Skill file parser interface

    Defines abstract methods for parsing and building skill files
    """

    @abstractmethod
    def parse(self, content: str) -> SkillParseResult:
        """Parse Skill file content

        Args:
            content: Complete content of Skill file

        Returns:
            Parse result object
        """
        pass

    @abstractmethod
    def build(self, frontmatter: dict[str, Any], content: str) -> str:
        """Build Skill file content

        Args:
            frontmatter: Frontmatter dictionary
            content: Body content

        Returns:
            Complete Skill file content (including --- separators)
        """
        pass

    @abstractmethod
    def extract_description(self, frontmatter: dict[str, Any]) -> str:
        """Extract description information

        Args:
            frontmatter: Frontmatter dictionary

        Returns:
            Description text
        """
        pass

    @abstractmethod
    def extract_resources(self, frontmatter: dict[str, Any]) -> list[str]:
        """Extract resource list

        Args:
            frontmatter: Frontmatter dictionary

        Returns:
            Resource URL list
        """
        pass

    def parse_file(self, file_path: str) -> SkillParseResult:
        """Parse Skill file

        Args:
            file_path: File path

        Returns:
            Parse result object

        Raises:
            FileNotFoundError: File doesn't exist
        """
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Skill file not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        return self.parse(content)
