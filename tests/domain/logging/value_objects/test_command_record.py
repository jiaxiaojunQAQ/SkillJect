"""Tests for CommandRecord value object."""

from src.domain.logging.value_objects.command_record import CommandRecord


def test_command_record_to_dict_roundtrip() -> None:
    """Test CommandRecord to_dict and from_dict roundtrip."""
    rec = CommandRecord(
        tool_use_id="toolu_1",
        command="ls -la /tmp",
        cwd="/home/claude_code/project",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        exit_code=0,
        stdout="a\nb\n",
        stderr="",
        duration_ms=1000,
    )
    d = rec.to_dict()
    assert d["command"] == "ls -la /tmp"
    assert d["exit_code"] == 0
    assert CommandRecord.from_dict(d) == rec


def test_command_record_with_nullable_fields() -> None:
    """Test CommandRecord with nullable fields."""
    rec = CommandRecord(
        tool_use_id="toolu_2",
        command="echo test",
        cwd=None,
        started_at=None,
        ended_at=None,
        exit_code=None,
        stdout="test",
        stderr="",
        duration_ms=None,
    )
    d = rec.to_dict()
    assert d["cwd"] is None
    assert d["exit_code"] is None
    assert d["duration_ms"] is None
    assert CommandRecord.from_dict(d) == rec


def test_command_record_immutable() -> None:
    """Test that CommandRecord is immutable (frozen)."""
    rec = CommandRecord(
        tool_use_id="toolu_1",
        command="ls",
        cwd="/tmp",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        exit_code=0,
        stdout="",
        stderr="",
        duration_ms=1000,
    )
    # Attempting to modify should raise FrozenInstanceError
    try:
        rec.command = "different"  # type: ignore
        raise AssertionError("Should not be able to modify frozen dataclass")
    except AttributeError:
        pass  # Expected
