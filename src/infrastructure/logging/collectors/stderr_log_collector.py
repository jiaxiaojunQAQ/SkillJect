"""
Universal log collector for CLI Agents

Suitable for all agents executed via shell commands:
- Claude Code
- Google Gemini CLI
- OpenAI Codex CLI
- iFlow CLI

Features:
- Collect stdout and stderr output
- Filter irrelevant logs (npm installation logs, etc.)
- Extract agent response content
- Format logs for subsequent analysis
"""

from datetime import datetime
from typing import Any

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig

from .base_collector import LogCollector


class StderrLogCollector(LogCollector):
    """
    Universal log collector for CLI Agents.

    Suitable for all CLI agents executed via shell commands.
    Does not require specialized log format parsing (e.g., OpenTelemetry).
    """

    def __init__(self, config: BaseAgentConfig):
        """
        Initialize log collector.

        Args:
            config: Agent configuration object
        """
        self.config = config
        self.agent_name = config.name

    async def collect(
        self,
        execution: Any,
        agent: Any,
    ) -> dict[str, Any]:
        """
        Collect CLI stdout/stderr logs.

        Args:
            execution: Agent execution result
            agent: Agent instance (kept for context)

        Returns:
            Structured log dictionary
        """
        # Extract raw output
        raw_stdout = []
        if hasattr(execution, "logs") and hasattr(execution.logs, "stdout"):
            for msg in execution.logs.stdout:
                raw_stdout.append(msg.text)

        raw_stderr = []
        if hasattr(execution, "logs") and hasattr(execution.logs, "stderr"):
            for msg in execution.logs.stderr:
                raw_stderr.append(msg.text)

        # Build event list (CLI agents don't have structured events)
        events = []

        # Add metadata
        metadata = {
            "agent_name": self.agent_name,
            "collector_type": "stderr",
            "timestamp": datetime.now().isoformat(),
        }

        # Filter irrelevant output (npm installation logs, etc.)
        filtered_stdout = self._filter_logs(raw_stdout)
        filtered_stderr = self._filter_logs(raw_stderr)

        return {
            "raw_stdout": raw_stdout,
            "raw_stderr": raw_stderr,
            "events": events,
            "formatted_output": self.format_for_analysis(
                {
                    "raw_stdout": filtered_stdout,
                    "raw_stderr": filtered_stderr,
                    "events": events,
                    "metadata": metadata,
                }
            ),
            "metadata": metadata,
        }

    def format_for_analysis(
        self,
        logs: dict[str, Any],
    ) -> str:
        """
        Format logs for analysis.

        Args:
            logs: Log dictionary returned by collect()

        Returns:
            Formatted log string
        """
        raw_stdout = logs.get("raw_stdout", [])
        raw_stderr = logs.get("raw_stderr", [])
        metadata = logs.get("metadata", {})

        # Extract agent response (usually the last few lines of stdout)
        agent_response = self._extract_agent_response(raw_stdout)

        # Build formatted output
        output_lines = []

        # Add metadata
        output_lines.append(f"=== {metadata.get('agent_name', 'unknown')} Log ===")
        output_lines.append(f"Timestamp: {metadata.get('timestamp', 'unknown')}")

        # Add agent response
        if agent_response:
            output_lines.append("\nAgent Response:")
            output_lines.append(agent_response)
            output_lines.append("")

        # Add stderr (if any)
        if raw_stderr:
            output_lines.append("Errors:")
            for line in raw_stderr:
                output_lines.append(f"  {line}")
            output_lines.append("")

        return "\n".join(output_lines)

    def _filter_logs(self, logs: list[str]) -> list[str]:
        """
        Filter out irrelevant log lines.

        Args:
            logs: Original list of log lines

        Returns:
            Filtered list of log lines
        """
        # Keywords for irrelevant logs
        npm_keywords = ["npm", "added", "removed", "changed", "updated", "up to date"]
        config_keywords = ["config", "package", "environment"]

        filtered = []
        for line in logs:
            # Skip empty lines
            if not line or line.isspace():
                continue

            # Convert to lowercase for matching
            line_lower = line.lower()

            # Check if contains irrelevant keywords
            is_relevant = True
            for keyword in npm_keywords + config_keywords:
                if keyword in line_lower:
                    is_relevant = False
                    break

            # Only keep relevant logs
            if is_relevant:
                filtered.append(line)

        return filtered

    def _extract_agent_response(self, stdout: list[str]) -> str | None:
        """
        Extract agent response from stdout.

        Args:
            stdout: List of stdout lines

        Returns:
            Agent response text, or None if not found

        Design considerations:
        - Agent response is usually the last few non-installation log lines
        - Filter out npm installation and configuration logs
        - Keep output related to user prompt
        """
        # Take last 10 lines (avoid including too much irrelevant output)
        recent_lines = stdout[-10:] if stdout else []

        # Filter progress indicators
        progress_indicators = [
            "installing",
            "downloading",
            "fetching",
            "updating",
            "loading",
            "checking",
            "retrieving",
            "unpacking",
            "building",
            "compiling",
            "adding",
            "creating",
            "generating",
            "resolving",
            "processing",
        ]

        response_lines = []
        for line in recent_lines:
            line_lower = line.lower()

            # Skip progress indicators
            if any(indicator in line_lower for indicator in progress_indicators):
                continue

            # Skip empty lines
            if not line.strip():
                continue

            response_lines.append(line)

        # If no response lines, return None
        if not response_lines:
            return None

        return "\n".join(response_lines)
# mypy: disable-error-code="override,var-annotated"
