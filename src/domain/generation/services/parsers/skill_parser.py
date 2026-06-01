"""
Unified Skill File Parser

Provides unified skill file parsing and building functionality, eliminating code duplication
"""

import re
import warnings
from typing import Any

import yaml

from src.domain.generation.interfaces import ISkillParser, SkillParseResult


class UnifiedSkillParser(ISkillParser):
    """Unified Skill file parser

    Implements ISkillParser interface, providing unified parsing and building functionality.
    This is the single implementation for skill file parsing; other places should use it via dependency injection.
    """

    # Class-level regex patterns (shared by all instances)
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    def parse(self, content: str) -> SkillParseResult:
        """Parse Skill file content

        Args:
            content: Skill file content

        Returns:
            Parsed result object
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            # No frontmatter case
            return SkillParseResult(
                frontmatter={},
                content=content.strip(),
                raw_content=content,
            )

        frontmatter_text = match.group(1)
        body_content = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            warnings.warn(f"Failed to parse YAML frontmatter: {e}", stacklevel=2)
            frontmatter = {}

        return SkillParseResult(
            frontmatter=frontmatter,
            content=body_content.strip(),
            raw_content=content,
        )

    def build(self, frontmatter: dict[str, Any], content: str) -> str:
        """Build Skill file content

        Args:
            frontmatter: Frontmatter dictionary
            content: Body content

        Returns:
            Complete Skill file content
        """
        frontmatter_yaml = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        return f"---\n{frontmatter_yaml}---\n\n{content}"

    def extract_description(self, frontmatter: dict[str, Any]) -> str:
        """Extract description information

        Args:
            frontmatter: Frontmatter dictionary

        Returns:
            Description text
        """
        return str(frontmatter.get("description", ""))

    def extract_resources(self, frontmatter: dict[str, Any]) -> list[str]:
        """Extract resource list

        Args:
            frontmatter: Frontmatter dictionary

        Returns:
            Resource URL list
        """
        resources = frontmatter.get("resources", [])
        if isinstance(resources, list):
            return resources
        elif isinstance(resources, str):
            return [resources]
        return []

    # Convenience methods

    def update_frontmatter(
        self, frontmatter: dict[str, Any], key: str, value: Any
    ) -> dict[str, Any]:
        """Update value in frontmatter

        Args:
            frontmatter: Original frontmatter
            key: Key name
            value: New value

        Returns:
            Updated frontmatter copy
        """
        updated = frontmatter.copy()
        updated[key] = value
        return updated

    def append_to_description(self, frontmatter: dict[str, Any], suffix: str) -> dict[str, Any]:
        """Append content to description end

        Args:
            frontmatter: Frontmatter dictionary
            suffix: Content to append

        Returns:
            Updated frontmatter copy
        """
        original_desc = self.extract_description(frontmatter)
        return self.update_frontmatter(
            frontmatter, "description", f"{suffix} {original_desc}".strip()
        )

    def prepend_to_description(self, frontmatter: dict[str, Any], prefix: str) -> dict[str, Any]:
        """Prepend content to description start

        Args:
            frontmatter: Frontmatter dictionary
            prefix: Content to prepend

        Returns:
            Updated frontmatter copy
        """
        original_desc = self.extract_description(frontmatter)
        return self.update_frontmatter(
            frontmatter, "description", f"{prefix} {original_desc}".strip()
        )

    def add_resource(self, frontmatter: dict[str, Any], resource_url: str) -> dict[str, Any]:
        """Add resource URL

        Args:
            frontmatter: Frontmatter dictionary
            resource_url: Resource URL

        Returns:
            Updated frontmatter copy
        """
        resources = self.extract_resources(frontmatter)
        if resource_url not in resources:
            resources.append(resource_url)
        return self.update_frontmatter(frontmatter, "resources", resources)

    def inject_into_content(self, content: str, injection: str, position: str = "end") -> str:
        """Inject text into body content

        Args:
            content: Original body content
            injection: Text to inject
            position: Injection position ("start", "end")

        Returns:
            Injected content
        """
        if position == "start":
            return f"{injection}\n\n{content}"
        else:  # end
            return f"{content}\n\n{injection}"


# Create global singleton instance
_global_parser: UnifiedSkillParser | None = None


def get_skill_parser() -> UnifiedSkillParser:
    """Get global Skill parser instance

    Returns:
        UnifiedSkillParser singleton
    """
    global _global_parser
    if _global_parser is None:
        _global_parser = UnifiedSkillParser()
    return _global_parser
