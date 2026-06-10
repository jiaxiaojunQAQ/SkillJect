"""Shared constants used across layers."""

LLM_TIMEOUT = 120
REQUEST_TIMEOUT = 120
INSTALL_TIMEOUT = 300
COMMAND_TIMEOUT = 300

# Claude Code CLI version pinned for reproducibility.
# The paper's experiments were run on 2.1.34; newer CLI releases are noticeably
# more resistant to skill-file injection and emit a different telemetry/trace
# shape, so reproductions must stay on this version. Keep in sync with the
# CLAUDE_CODE_VERSION build arg in Dockerfile.claude.
CLAUDE_CODE_CLI_VERSION = "2.1.34"
