"""
Secret Masking Utilities

Helpers for logging credentials without exposing them.
"""


def mask_secret(value: str) -> str:
    """Mask a secret for logging, keeping only the last 4 characters.

    Args:
        value: Secret value (API key, token)

    Returns:
        Masked representation, e.g. "***abcd"; short values become "***"
    """
    if len(value) <= 8:
        return "***"
    return f"***{value[-4:]}"
