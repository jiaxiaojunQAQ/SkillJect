"""
Claude Code Agent Configuration

Migrates the existing ClaudeCodeSecurityTester configuration to a unified configuration class.

Configuration Details:
- name: "claude-code" - Unique agent identifier
- display_name: "Claude Code" - Human-readable name
- npm_package: "@anthropic-ai/claude-code@<pinned>" - NPM package name and version
  (pinned via CLAUDE_CODE_CLI_VERSION for reproducibility)
- command: "claude" - Base command (without subcommand)
- env_prefix: "ANTHROPIC" - Environment variable prefix
- env_vars: Environment variable name mapping
- install_command: "npm i -g @anthropic-ai/claude-code@<pinned>" - Installation command
Backward Compatibility:
- Environment variables: ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
- Default agent name: If user doesn't specify --agent, claude-code is used by default
- Configuration loading: Supports overriding config values via environment variables

Mapping to existing code:
- Environment variable reading: From `ClaudeCodeSecurityTester.__init__()`
- CLI installation: From `ClaudeCodeSecurityTester.setup()` using `await sandbox.commands.run()`
- Command execution: From `ClaudeCodeSecurityTester.test_injection()` using `claude_command`
- Log collection: From `ClaudeLogCollector` (stream-json based)
"""

import os

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.infrastructure.logging.collectors.claude_log_collector import ClaudeLogCollector
from src.shared.constants import CLAUDE_CODE_CLI_VERSION, INSTALL_TIMEOUT


class ClaudeCodeAgentConfig(BaseAgentConfig):
    """
    Claude Code Agent Configuration

    Extends BaseAgentConfig and defines Claude Code specific configuration.
    Claude Code uses stream-json output captured via ClaudeLogCollector.
    """

    def __init__(self) -> None:
        """
        Initialize Claude Code configuration

        Sets agent-specific default values and environment variable mappings.
        """
        # Common configuration (from BaseAgentConfig)
        self.name = "claude-code"
        self.display_name = "Claude Code"
        # Pinned for reproducibility — see CLAUDE_CODE_CLI_VERSION. Newer CLI
        # releases resist injection differently and change the trace shape.
        self.npm_package = f"@anthropic-ai/claude-code@{CLAUDE_CODE_CLI_VERSION}"
        self.command = "claude"
        self.env_prefix = "ANTHROPIC"

        # Environment variable mapping (from env_prefix to full environment variable name)
        self.env_vars = {
            "AUTH_TOKEN": "ANTHROPIC_AUTH_TOKEN",
            "BASE_URL": "ANTHROPIC_BASE_URL",
            "MODEL": "ANTHROPIC_MODEL",
        }

        # Installation command (pinned, see npm_package)
        self.install_command = f"npm i -g @anthropic-ai/claude-code@{CLAUDE_CODE_CLI_VERSION}"

        # Log collector: Claude Code uses stream-json via ClaudeLogCollector
        self.log_collector = ClaudeLogCollector

        # Installation timeout (default value, can be overridden)
        self.install_timeout = INSTALL_TIMEOUT

        # Command execution timeout (default value, can be overridden)
        self.command_timeout = 3000  # 5 minutes

        # Additional environment variables (optional)
        self.additional_env = {}

        # Additional commands after installation (optional)
        self.post_install_commands = []

        # Working directory (default value)
        self.default_workdir = "/home/claude_code/project"

    def _load_from_env(self) -> "ClaudeCodeAgentConfig":
        """
        Load configuration from environment variables

        Supports overriding default configuration values via environment variables.

        Returns:
            Loaded configuration object
        """
        # Load optional working directory override
        if "CLAUDE_WORKDIR" in os.environ:
            self.default_workdir = os.environ["CLAUDE_WORKDIR"]

        return self

    def get_required_env_vars(self) -> dict[str, str]:
        """
        Get required environment variables

        Returns:
            Mapping of environment variable names to values

        Raises:
            ValueError: If required environment variables are not set
        """
        env = {}

        # ANTHROPIC_AUTH_TOKEN is required (extracted from existing code)
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not auth_token:
            raise ValueError(
                "Claude Code: Required environment variable "
                "'ANTHROPIC_AUTH_TOKEN' is not set. "
                "Please set it with: export ANTHROPIC_AUTH_TOKEN='sk-ant-api03-...'"
            )
        env["ANTHROPIC_AUTH_TOKEN"] = auth_token

        # ANTHROPIC_BASE_URL is optional (uses default value)
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url

        # ANTHROPIC_MODEL is optional (uses default value)
        model = os.getenv("ANTHROPIC_MODEL")
        if model:
            env["ANTHROPIC_MODEL"] = model

        return env

    def get_install_env(self) -> dict[str, str]:
        """
        Get environment variables required for installation

        Returns:
            Mapping of environment variable names to values
        """
        return self.get_required_env_vars()

    def get_full_env(self) -> dict[str, str]:
        """
        Get complete environment variables (including configuration override values)

        Returns:
            Mapping of environment variable names to values
        """
        env = self.get_required_env_vars()

        # Add additional environment variables
        env.update(self.additional_env)

        return env

    def get_install_commands(self) -> list[str]:
        """
        Get list of installation commands

        Returns:
            List of commands
        """
        commands = [self.install_command]

        # Add additional commands after installation
        commands.extend(self.post_install_commands)

        return commands

    def __repr__(self) -> str:
        """
        Return string representation of configuration

        Used for debugging and logging.
        """
        return f"ClaudeCodeAgentConfig(name='{self.name}', display_name='{self.display_name}')"
