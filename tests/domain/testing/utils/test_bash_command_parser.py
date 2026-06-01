"""Tests for BashCommandParser read-only command filtering.

Verifies that non-execution file operations (cat, head, ls, grep, etc.)
do not trigger false positive script execution detection, while actual
execution patterns (bash, sh, ./, source, etc.) are still correctly detected.
"""

import pytest

from src.domain.testing.utils.bash_command_parser import BashCommandParser


class TestReadOnlyFalsePositiveFiltering:
    """Verify read-only commands do not trigger false positive detection."""

    @pytest.mark.parametrize("command", [
        # File viewing
        "cat /tmp/env_checker.sh",
        "cat /home/claude_code/.claude/skills/x/resources/env_checker.sh",
        "head /tmp/env_checker.sh",
        "tail /tmp/env_checker.sh",
        "less /tmp/env_checker.sh",
        "more /tmp/env_checker.sh",
        "bat /tmp/env_checker.sh",
        # File inspection
        "stat /tmp/env_checker.sh",
        "file /tmp/env_checker.sh",
        "wc -l /tmp/env_checker.sh",
        "md5sum /tmp/env_checker.sh",
        "sha256sum /tmp/env_checker.sh",
        # File management
        "cp /tmp/env_checker.sh /home/user/",
        "mv /tmp/env_checker.sh /home/user/",
        "rm /tmp/env_checker.sh",
        "ls /tmp/env_checker.sh",
        "chmod 644 /tmp/env_checker.sh",
        # Searching
        "grep pattern /tmp/env_checker.sh",
        "grep -r something /tmp/env_checker.sh",
        # Editing
        "vim /tmp/env_checker.sh",
        "nano /tmp/env_checker.sh",
        # Comparison
        "diff /tmp/env_checker.sh /tmp/other.sh",
        # Output redirection (writing, not executing)
        "echo hello > /tmp/env_checker.sh",
        # Path inspection
        "readlink /tmp/env_checker.sh",
        "realpath /tmp/env_checker.sh",
        # With sudo prefix
        "sudo cat /tmp/env_checker.sh",
        "sudo less /tmp/env_checker.sh",
    ])
    def test_read_only_commands_not_detected(self, command):
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution(command)
        assert not result.matched, (
            f"False positive: '{command}' detected as {result.pattern} "
            f"(confidence={result.confidence:.2f})"
        )

    @pytest.mark.parametrize("command", [
        # Bare path execution
        "/tmp/env_checker.sh",
        "/home/user/scripts/env_checker.sh",
        "./env_checker.sh",
        "../scripts/env_checker.sh",
        # Shell execution
        "bash env_checker.sh",
        "sh env_checker.sh",
        "bash /tmp/env_checker.sh",
        "sh -x /tmp/env_checker.sh",
        # Source execution
        "source env_checker.sh",
        ". env_checker.sh",
        # Chained execution
        "chmod +x env_checker.sh && ./env_checker.sh",
        # Pipeline execution
        "cat env_checker.sh | bash",
        "cat /tmp/env_checker.sh | bash",
        # With execution prefixes
        "sudo /tmp/env_checker.sh",
        "sudo bash /tmp/env_checker.sh",
        # Compound: read then execute
        "cat /tmp/env_checker.sh && bash /tmp/env_checker.sh",
    ])
    def test_actual_execution_detected(self, command):
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution(command)
        assert result.matched, (
            f"Missed true positive: '{command}' not detected as execution"
        )

    def test_empty_command_returns_no_match(self):
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("")
        assert not result.matched

    def test_chmod_only_still_filtered(self):
        """Existing chmod-only filter must still work."""
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("chmod +x env_checker.sh")
        assert not result.matched

    def test_pipeline_to_bash_detected(self):
        """cat script.sh | bash must still be detected as execution."""
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("cat /tmp/env_checker.sh | bash")
        assert result.matched
        assert result.pattern.display_name == "pipeline"

    def test_pipeline_to_grep_not_detected(self):
        """cat script.sh | grep is NOT execution."""
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("cat /tmp/env_checker.sh | grep foo")
        # The pipeline pattern requires | (ba)?sh, so grep won't match it.
        # ABSOLUTE_PATH may match the path, but _is_read_only_context
        # should filter it because 'cat' precedes the path.
        assert not result.matched

    def test_bare_path_in_subshell_detected(self):
        """Bare path in subshell should be detected as execution."""
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("( /tmp/env_checker.sh )")
        assert result.matched

    def test_noop_prefix_stripped(self):
        """sudo before bare path should be stripped, leaving execution."""
        parser = BashCommandParser("env_checker.sh")
        result = parser.detect_script_execution("sudo /tmp/env_checker.sh")
        assert result.matched
