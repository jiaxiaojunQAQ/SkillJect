"""StreamUsage value object for token usage information from stream-json."""

from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class StreamUsage:
    """Represents token usage from a single stream-json usage event.

    Carries the four token counts from one usage payload. `kind="turn"` is
    per-message usage; `kind="final"` is the cumulative `result` event at
    end of stream.

    Attributes:
        input_tokens: Regular input tokens used
        cache_read_input_tokens: Tokens read from input cache
        cache_creation_input_tokens: Tokens used to create input cache
        output_tokens: Output tokens generated
        kind: Type of usage event ("turn" for per-message, "final" for cumulative)
    """

    input_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    output_tokens: int
    kind: Literal["turn", "final"]

    @property
    def total_input_tokens(self) -> int:
        """Calculate total input tokens including cache.

        Returns:
            Sum of input_tokens, cache_read_input_tokens, and
            cache_creation_input_tokens
        """
        return (
            self.input_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert StreamUsage to dictionary.

        Returns:
            Dictionary representation of the StreamUsage
        """
        return asdict(self)
