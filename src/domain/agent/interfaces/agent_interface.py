"""
Unified Agent Interface Definition

This module defines the unified interface that all code agents must implement,
ensuring that different agents (CLI-based or SDK-based) can integrate with
the agent-security-eval framework in a consistent manner.

Interface responsibilities:
1. setup(): Set up Agent environment (install dependencies, configure sandbox)
2. execute_prompt(): Execute prompt and return result
3. collect_logs(): Collect execution logs
4. cleanup(): Clean up Agent resources

Design principles:
- Abstraction: Define interfaces without focusing on implementation details
- Type safety: Use type annotations
- Documentation: Clear docstrings explaining each method
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from opensandbox import Sandbox

from src.shared.constants import COMMAND_TIMEOUT, INSTALL_TIMEOUT


class AgentInterface(ABC):
    """
    Unified Agent interface

    All code agents must implement this interface to:
    1. Be managed through unified configuration classes
    2. Be created through unified Agent factory
    3. Be used consistently in multi-agent testers

    Design considerations:
    - CLI-based agents (claude-code, openclaw):
      Execute shell commands inside sandbox
      Output to stdout/stderr (can be parsed)

    - SDK-based agents (langgraph, google-adk):
      Run Python process externally
      Output via SDK event streams or stdout/stderr
      Require different prompt object construction

    The interface remains abstract enough without enforcing specific execution models.
    """

    @abstractmethod
    async def setup(
        self,
        sandbox: Sandbox,
    ) -> None:
        """
        Set up Agent environment

        Responsible for:
        1. Installing Agent dependencies (like npm packages)
        2. Configuring sandbox environment variables
        3. Preparing environment for Agent execution

        Args:
            sandbox: OpenSandbox sandbox instance
                Note: For CLI agents, sandbox is already created
                      For SDK agents, may need to run agent externally

        Raises:
            Exception: If installation or configuration fails
        """
        pass

    @abstractmethod
    async def execute_prompt(
        self,
        prompt: str,
        working_directory: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute prompt and return execution result

        Args:
            prompt: User prompt
            working_directory: Optional working directory

        Returns:
            Dictionary containing:
            - exit_code: int (exit code, 0 for success)
            - stdout: List[str] (standard output lines)
            - stderr: List[str] (standard error output lines)
            - error: Optional[Dict[str, str]] (error information, if any)
            - metadata: Dict[str, Any] (Agent-specific metadata)

        Design considerations:
        - For CLI agents: Return shell command's stdout/stderr
        - For SDK agents: May return event streams or structured data

        Raises:
            Exception: If execution fails
        """
        pass

    @abstractmethod
    async def collect_logs(
        self,
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Collect execution logs

        Args:
            execution: Execution result returned by execute_prompt()

        Returns:
            Dictionary containing:
            - raw_stdout: List[str] (raw standard output)
            - raw_stderr: List[str] (raw standard error output)
            - events: List[Dict[str, Any]] (structured events, for SDK agents)
            - formatted_output: str (formatted output for analysis)
            - metadata: Dict[str, Any] (log metadata like timestamps, agent name, etc.)

        Design considerations:
        - For CLI agents:
          - raw_stdout/stderr come from command output
          - events may be empty list
          - formatted_output filters irrelevant logs (like OTel logs)

        - For Claude Code:
          - Parse OpenTelemetry logs
          - Extract event streams
          - formatted_output extracts key event information

        - For other SDK agents:
          - Parse specific event formats
          - Extract tool calls, LLM responses, etc.

        Raises:
            Exception: If log parsing fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up Agent resources

        Responsible for:
        1. Cleaning up sandbox (for CLI agents)
        2. Terminating external processes (for SDK agents)
        3. Releasing memory and resources
        4. Cleaning up temporary files

        Design considerations:
        - For CLI agents: Call await sandbox.kill()
        - For SDK agents: Terminate external Python process
        - Should be idempotent (multiple cleanup calls should not raise exceptions)
        - Need graceful handling of cleanup failures
        """
        pass


class BaseAgentConfig:
    """
    Base class for all Agent configuration classes

    Defines common fields and interfaces for all agent configurations.
    Specific agent configuration classes (like ClaudeCodeAgentConfig, GeminiCliAgentConfig)
    should inherit from this class and implement agent-specific fields.

    Design principles:
    - Type safety: Use dataclass and type annotations
    - Configuration-driven: All agent behavior defined through configuration
    - Documentation: Clear docstrings explaining each field

    Common fields:
    - name: agent unique identifier (e.g., "claude-code")
    - display_name: human-readable display name (e.g., "Claude Code")
    - npm_package: NPM package name and version
    - command: base command (e.g., "claude", "gemini")
    - env_prefix: environment variable prefix (e.g., "ANTHROPIC", "GEMINI")
    - env_vars: environment variable name mapping (e.g., {"AUTH_TOKEN": "ANTHROPIC_AUTH_TOKEN"})
    - install_command: installation command (e.g., "npm install -g ...")
    - use_otel_logging: whether to use OpenTelemetry logging (only Claude Code needs this)

    Agent-specific field examples:
    - base_command: command format (e.g., "<command>" or "<command> <prompt>")
    - install_timeout: installation timeout (seconds)
    - command_timeout: command execution timeout (seconds)
    - additional_env: additional environment variables
    - post_install_commands: post-installation additional commands
    """

    def __init__(
        self,
        name: str,
        display_name: str,
        npm_package: str,
        command: str,
        env_prefix: str,
        env_vars: dict[str, str],
        install_command: str,
        use_otel_logging: bool = False,
    ):
        """
        Initialize Agent configuration

        Args:
            name: agent unique identifier
            display_name: human-readable name
            npm_package: NPM package name and version
            command: base command (e.g., "claude", "gemini")
            env_prefix: environment variable prefix
            env_vars: environment variable name mapping
            install_command: installation command
            use_otel_logging: whether to use OpenTelemetry logging
        """
        self.name = name
        self.display_name = display_name
        self.npm_package = npm_package
        self.command = command
        self.env_prefix = env_prefix
        self.env_vars = env_vars
        self.install_command = install_command

        # Agent-specific fields (subclasses may override)
        self.base_command_format = "{command}"  # Default format: command + prompt
        self.install_timeout = INSTALL_TIMEOUT  # Default installation timeout: 5 minutes
        self.command_timeout = COMMAND_TIMEOUT  # Default command timeout: 5 minutes
        self.additional_env: dict[str, str] = {}  # Additional environment variables
        self.post_install_commands: list[str] = []  # Post-installation additional commands

    def get_required_env_vars(self) -> dict[str, str]:
        """
        Get required environment variables

        Returns:
            Mapping from environment variable name to value

        Raises:
            ValueError: If required environment variable is not set
        """
        env = {}
        for _, env_name in self.env_vars.items():
            value = os.getenv(f"{self.env_prefix}_{env_name}")
            if value is None:
                raise ValueError(
                    f"{self.display_name}: Required environment variable "
                    f"'{self.env_prefix}_{env_name}' is not set. "
                    f"Please set it with: export {self.env_prefix}_{env_name}=<value>"
                )
            env[env_name] = value
        return env

    def __repr__(self) -> str:
        """
        Return string representation of configuration

        Used for debugging and logging
        """
        return f"AgentConfig(name='{self.name}', display_name='{self.display_name}')"
