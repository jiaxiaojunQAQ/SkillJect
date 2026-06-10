"""
Claude Code Test Runner

Claude-specific test runner for security testing with Claude Code agent.
Claude Code uses stream-json output for structured trace capture.

Directory structure:
- Workdir: /home/claude_code/project
- Skills: ~/.claude/skills/{name}/
- Config: ~/.claude/settings.json
- Command: claude --output-format stream-json --include-partial-messages --verbose -p "{instruction}"
- Log format: stream-json (parsed by ClaudeLogCollector)

Note: The main execution logic (_execute_test) is inherited from SandboxTestRunner,
which implements the Claude Code flow by default. This class provides Claude-specific
constants and helper methods for potential customization.
"""

import logging

from .sandbox_test_runner import SandboxTestRunner

logger = logging.getLogger(__name__)


# Claude Code path constants
CLAUDE_HOME_DIR = "/home/claude_code"
CLAUDE_PROJECT_DIR = f"{CLAUDE_HOME_DIR}/project"
CLAUDE_CONFIG_DIR = f"{CLAUDE_HOME_DIR}/claude"
CLAUDE_SETTINGS_FILE = f"{CLAUDE_CONFIG_DIR}/settings.json"
CLAUDE_SKILLS_DIR = f"{CLAUDE_CONFIG_DIR}/skills"


class ClaudeTestRunner(SandboxTestRunner):
    """Claude Code-specific test runner.

    Inherits the main execution logic from SandboxTestRunner. This class provides:
    - Claude-specific path constants
    - Claude-specific configuration wrapper
    - Helper methods for tool call trace analysis

    Overrides _build_agent_command to provide Claude-specific agent command.
    """

    # Use Claude-specific paths in inherited methods
    # These can be referenced by overrides if needed
    CLAUDE_HOME_DIR = CLAUDE_HOME_DIR
    CLAUDE_PROJECT_DIR = CLAUDE_PROJECT_DIR
    CLAUDE_CONFIG_DIR = CLAUDE_CONFIG_DIR
    CLAUDE_SETTINGS_FILE = CLAUDE_SETTINGS_FILE
    CLAUDE_SKILLS_DIR = CLAUDE_SKILLS_DIR

    def _build_agent_command(self, test_prompt: str) -> str:
        """Build Claude Code agent execution command.

        Override parent method to provide Claude-specific command with
        stream-json output for structured trace capture.

        Args:
            test_prompt: Test prompt/instruction

        Returns:
            Complete Claude agent execution command
        """
        import shlex
        escaped_prompt = shlex.quote(test_prompt)
        # Claude Code with stream-json output for structured trace collection
        return (
            f"cd {CLAUDE_PROJECT_DIR} && "
            f"claude --output-format stream-json --include-partial-messages --verbose -p {escaped_prompt}"
        )
