"""
Claude Code Test Runner

Claude-specific test runner for security testing with Claude Code agent.
Claude Code uses OpenTelemetry logging and has a specific directory structure.

Directory structure:
- Workdir: /home/claude_code/project
- Skills: ~/.claude/skills/{name}/
- Config: ~/.claude/settings.json
- Command: claude "{instruction}"
- Log format: OpenTelemetry (OTEL)

Note: The main execution logic (_execute_test) is inherited from SandboxTestRunner,
which implements the Claude Code flow by default. This class provides Claude-specific
constants and helper methods for potential customization.
"""

import logging

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig

from .sandbox_test_runner import SandboxTestRunner

logger = logging.getLogger(__name__)


# Claude Code path constants
CLAUDE_HOME_DIR = "/home/claude_code"
CLAUDE_PROJECT_DIR = f"{CLAUDE_HOME_DIR}/project"
CLAUDE_CONFIG_DIR = f"{CLAUDE_HOME_DIR}/claude"
CLAUDE_SETTINGS_FILE = f"{CLAUDE_CONFIG_DIR}/settings.json"
CLAUDE_SKILLS_DIR = f"{CLAUDE_CONFIG_DIR}/skills"


class _MinimalClaudeConfig(BaseAgentConfig):
    """Minimal configuration wrapper class for ClaudeOtelLogCollector.

    Only provides fields actually used by the collector.
    """

    def __init__(self) -> None:
        super().__init__(
            name="claude-code",
            display_name="Claude Code",
            npm_package="@anthropic-ai/claude-code@latest",
            command="claude",
            env_prefix="ANTHROPIC",
            env_vars={
                "AUTH_TOKEN": "ANTHROPIC_AUTH_TOKEN",
                "BASE_URL": "ANTHROPIC_BASE_URL",
                "MODEL": "ANTHROPIC_MODEL",
            },
            install_command="npm i -g @anthropic-ai/claude-code@latest",
            use_otel_logging=True,
        )


def _get_total_calls(tool_call_trace: dict) -> int:
    """Get total number of tool calls from trace.

    Args:
        tool_call_trace: Tool call trace dictionary

    Returns:
        Total number of tool calls
    """
    if not tool_call_trace:
        return 0

    def count_calls(node: dict) -> int:
        """Recursively count calls in trace tree."""
        count = 0
        if "calls" in node:
            count += len(node["calls"])
        if "children" in node:
            for child in node["children"]:
                count += count_calls(child)
        return count

    return count_calls(tool_call_trace)


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
        OpenTelemetry logging enabled.

        Args:
            test_prompt: Test prompt/instruction

        Returns:
            Complete Claude agent execution command
        """
        import shlex
        escaped_prompt = shlex.quote(test_prompt)
        # Claude Code with OTel telemetry
        return f"cd {CLAUDE_PROJECT_DIR} && CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_LOGS_EXPORTER=console OTEL_LOG_USER_PROMPTS=1 claude {escaped_prompt}"
