"""CommandRecord value object for representing a bash command execution."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CommandRecord:
    """Represents one bash command execution.

    Extracted from Claude's stream-json Bash tool_use + tool_result pair.
    Some fields are nullable because stream-json only carries command string
    and output text—future enrichment (e.g., container introspection) can
    populate them without breaking the schema.

    Attributes:
        tool_use_id: Anthropic SDK identifier pairing tool_use to tool_result
        command: The bash command string executed
        cwd: Current working directory where command was executed
        started_at: ISO 8601 timestamp when command started
        ended_at: ISO 8601 timestamp when command ended
        exit_code: Exit code of the command execution
        stdout: Standard output captured from the command
        stderr: Standard error captured from the command
        duration_ms: Total execution time in milliseconds
    """

    tool_use_id: str
    command: str
    cwd: str | None
    started_at: str | None
    ended_at: str | None
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int | None

    def to_dict(self) -> dict[str, Any]:
        """Convert CommandRecord to dictionary.

        Returns:
            Dictionary representation of the CommandRecord
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CommandRecord":
        """Create CommandRecord from dictionary.

        Args:
            data: Dictionary containing CommandRecord fields

        Returns:
            CommandRecord instance
        """
        return cls(**data)
