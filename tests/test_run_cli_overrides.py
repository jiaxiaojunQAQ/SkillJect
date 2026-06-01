from run import apply_runtime_overrides
from src.infrastructure.config.loaders.config_loader import ConfigLoader


def test_apply_runtime_overrides_disables_retries() -> None:
    config = ConfigLoader.load("config/main.yaml", profile="claude-glm")

    updated = apply_runtime_overrides(
        config,
        no_retry=True,
    )

    assert updated.execution.retry_failed is False
    assert updated.execution.max_retries == 0
