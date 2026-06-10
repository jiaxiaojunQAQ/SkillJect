"""Tests for StreamUsage value object."""

from src.domain.logging.value_objects.stream_usage import StreamUsage


def test_stream_usage_total_input() -> None:
    """Test StreamUsage total_input_tokens calculation."""
    u = StreamUsage(
        input_tokens=100,
        cache_read_input_tokens=50,
        cache_creation_input_tokens=20,
        output_tokens=30,
        kind="turn",
    )
    assert u.total_input_tokens == 170
    assert u.kind == "turn"


def test_stream_usage_total_input_zero() -> None:
    """Test StreamUsage total_input_tokens with zero cache tokens."""
    u = StreamUsage(
        input_tokens=100,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
        output_tokens=30,
        kind="final",
    )
    assert u.total_input_tokens == 100
    assert u.kind == "final"


def test_stream_usage_to_dict() -> None:
    """Test StreamUsage to_dict serialization."""
    u = StreamUsage(
        input_tokens=100,
        cache_read_input_tokens=50,
        cache_creation_input_tokens=20,
        output_tokens=30,
        kind="turn",
    )
    d = u.to_dict()
    assert d["input_tokens"] == 100
    assert d["cache_read_input_tokens"] == 50
    assert d["cache_creation_input_tokens"] == 20
    assert d["output_tokens"] == 30
    assert d["kind"] == "turn"


def test_stream_usage_immutable() -> None:
    """Test that StreamUsage is immutable (frozen)."""
    u = StreamUsage(
        input_tokens=100,
        cache_read_input_tokens=50,
        cache_creation_input_tokens=20,
        output_tokens=30,
        kind="turn",
    )
    # Attempting to modify should raise AttributeError
    try:
        u.input_tokens = 200  # type: ignore
        raise AssertionError("Should not be able to modify frozen dataclass")
    except AttributeError:
        pass  # Expected
