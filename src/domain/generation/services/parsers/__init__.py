"""
Parser Module

Provides unified skill file parsing functionality
"""

from src.domain.generation.services.parsers.skill_parser import UnifiedSkillParser

__all__ = ["UnifiedSkillParser"]


def get_skill_parser() -> UnifiedSkillParser:
    """Get Skill parser instance (singleton)

    Returns:
        UnifiedSkillParser instance
    """
    return UnifiedSkillParser()
