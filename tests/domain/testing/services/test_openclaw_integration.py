# mypy: disable-error-code="no-untyped-def"
"""
OpenClaw integration test data checks.

Port-dependent OpenClaw sandbox execution is intentionally excluded from the
normal test suite. This module only verifies that required local fixtures exist.
"""

import logging
from pathlib import Path

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data paths
DATA_BASE = Path("/home/liaojie/my_os/20_code/2026_SkillJect")
SKILL_PATH = DATA_BASE / "data/skill_inject/OBT-1_docx_t0/SKILL.md"
INSTRUCTION_PATH = DATA_BASE / "data/instruction/skill_inject/OBT-1_docx_t0/instruction.md"
AUXILIARY_FILE = DATA_BASE / "data/instruction/skill_inject/OBT-1_docx_t0/quarterly_report.docx"


@pytest.mark.asyncio
async def test_openclaw_verify_test_data():
    """Verify all local OpenClaw fixture files exist."""
    logger.info(f"[DATA] Checking SKILL.md: {SKILL_PATH} -> {SKILL_PATH.exists()}")
    logger.info(f"[DATA] Checking instruction.md: {INSTRUCTION_PATH} -> {INSTRUCTION_PATH.exists()}")
    logger.info(f"[DATA] Checking auxiliary file: {AUXILIARY_FILE} -> {AUXILIARY_FILE.exists()}")

    assert SKILL_PATH.exists(), f"SKILL.md not found: {SKILL_PATH}"
    assert INSTRUCTION_PATH.exists(), f"instruction.md not found: {INSTRUCTION_PATH}"
    assert AUXILIARY_FILE.exists(), f"auxiliary file not found: {AUXILIARY_FILE}"

    # Log instruction content
    instruction = INSTRUCTION_PATH.read_text()
    logger.info(f"[DATA] Instruction content:\n{instruction}")
