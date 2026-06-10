"""
OpenClaw Agent Configuration

Configures all required parameters and options for OpenClaw.

OpenClaw is a self-hosted AI agent gateway that connects chat applications
(WhatsApp, Telegram, Discord, iMessage, and more) to AI coding agents.

Configuration Details:
- name: "openclaw" - Unique agent identifier
- display_name: "OpenClaw" - Human-readable name
- npm_package: "openclaw" - NPM package name
- command: "openclaw agent" - Command format
- env_prefix: "OPENCLAW" - Environment variable prefix
- env_vars: Environment variable name mapping
- install_command: Installation command
Special Notes:
- OpenClaw command format is `openclaw agent --message "<prompt>"` with optional `--json` flag
- Supports `--agent <id>` to target a specific configured agent
- Supports `--timeout <seconds>` for command timeout
- Outputs JSON format when `--json` flag is provided

Backward Compatibility:
- Environment variables: OPENCLAW_GATEWAY_TOKEN, OPENCLAW_GATEWAY_PASSWORD
- Default workspace: ~/.openclaw/workspace
- Default config: ~/.openclaw/openclaw.json

Integration with agent-security-eval:
- Will be registered by AgentRegistry
- Agent instances created through AgentFactory
- Used in SandboxTestRunner for security testing

References:
- https://docs.openclaw.ai/
- https://docs.openclaw.ai/cli/agent
"""

import os

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.infrastructure.logging.collectors.openclaw_json_log_collector import (
    OpenClawJsonLogCollector,
)
from src.shared.constants import COMMAND_TIMEOUT, INSTALL_TIMEOUT


class OpenClawAgentConfig(BaseAgentConfig):
    """
    OpenClaw Agent Configuration

    Defines all configuration for OpenClaw gateway.
    OpenClaw uses `openclaw agent --message "<prompt>"` command format.
    """

    def __init__(self) -> None:
        """
        Initialize OpenClaw configuration

        Sets agent-specific default values and environment variable mappings.
        """
        # Common configuration (from BaseAgentConfig)
        self.name = "openclaw"
        self.display_name = "OpenClaw"
        self.npm_package = "openclaw"

        # Command format: openclaw agent --message "<prompt>"
        self.command = "openclaw agent"

        self.env_prefix = "OPENCLAW"

        # Environment variable mapping
        self.env_vars = {
            "GATEWAY_TOKEN": "OPENCLAW_GATEWAY_TOKEN",
            "GATEWAY_PASSWORD": "OPENCLAW_GATEWAY_PASSWORD",
            "CONFIG_DIR": "OPENCLAW_CONFIG_DIR",
            "WORKSPACE_DIR": "OPENCLAW_WORKSPACE_DIR",
        }

        # Installation command
        self.install_command = "npm install -g openclaw"

        # Log collector: Use OpenClawJsonLogCollector for JSON format output with tool chain extraction
        self.log_collector = OpenClawJsonLogCollector

        # Installation timeout (default value)
        self.install_timeout = INSTALL_TIMEOUT

        # Command execution timeout (default value)
        self.command_timeout = COMMAND_TIMEOUT

        # Additional environment variables (optional)
        self.additional_env = {}

        # Additional commands after installation (optional)
        self.post_install_commands = []

        # Working directory (default value)
        self.default_workdir = "/home/node/.openclaw/workspace"

        # JSON output flag (OpenClaw specific)
        self.use_json_output = True

    def get_required_env_vars(self) -> dict[str, str]:
        """
        Get required environment variables

        Returns:
            Mapping of environment variable names to values

        Raises:
            ValueError: If required environment variable is not set
        """
        env = {}

        # OPENCLAW_GATEWAY_TOKEN is required
        gateway_token = os.getenv("OPENCLAW_GATEWAY_TOKEN")
        if not gateway_token:
            # Try alternative: OPENCLAW_GATEWAY_PASSWORD
            gateway_password = os.getenv("OPENCLAW_GATEWAY_PASSWORD")
            if not gateway_password:
                raise ValueError(
                    "OpenClaw: Required environment variable "
                    "'OPENCLAW_GATEWAY_TOKEN' or 'OPENCLAW_GATEWAY_PASSWORD' is not set. "
                    "Please set it with: export OPENCLAW_GATEWAY_TOKEN='your-token'"
                )
            env["OPENCLAW_GATEWAY_PASSWORD"] = gateway_password
        else:
            env["OPENCLAW_GATEWAY_TOKEN"] = gateway_token

        # OPENCLAW_CONFIG_DIR is optional (has default value)
        config_dir = os.getenv("OPENCLAW_CONFIG_DIR", "/home/node/.openclaw")
        env["OPENCLAW_CONFIG_DIR"] = config_dir

        # OPENCLAW_WORKSPACE_DIR is optional (has default value)
        workspace_dir = os.getenv("OPENCLAW_WORKSPACE_DIR", "/home/node/.openclaw/workspace")
        env["OPENCLAW_WORKSPACE_DIR"] = workspace_dir

        return env

    def _load_from_env(self) -> "OpenClawAgentConfig":
        """
        Load configuration from environment variables

        Supports overriding default configuration values via environment variables.

        Returns:
            Loaded configuration object
        """
        # Load optional working directory override
        if "OPENCLAW_WORKDIR" in os.environ:
            self.default_workdir = os.environ["OPENCLAW_WORKDIR"]

        return self

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

    def get_command_with_prompt(self, prompt: str) -> str:
        """
        Get the full command with prompt for execution

        Args:
            prompt: User prompt to execute

        Returns:
            Full command string
        """
        import shlex

        escaped_prompt = shlex.quote(prompt)
        command = f"{self.command} --message {escaped_prompt}"

        # Add JSON output flag if enabled
        if self.use_json_output:
            command += " --json"

        return command

    def __repr__(self) -> str:
        """
        Return string representation of configuration

        Used for debugging and logging.
        """
        return f"OpenClawAgentConfig(name='{self.name}', display_name='{self.display_name}')"
