# mypy: disable-error-code="import-untyped"
"""
Log collector factory.

Creates appropriate log collectors based on configuration.
"""

from typing import Any

from .base_collector import LogCollector, OtelCollector, StdoutCollector


class CollectorType:
    """Collector type constants."""

    STDOUT = "stdout"
    OTEL = "otel"
    AUTO = "auto"


class LogCollectorFactory:
    """Log collector factory.

    Creates appropriate log collectors based on configuration or auto-detection.
    """

    @staticmethod
    def create(
        collector_type: str = CollectorType.AUTO,
        config: dict[str, Any] | None = None,
    ) -> LogCollector:
        """Create log collector.

        Args:
            collector_type: Collector type
            config: Configuration dictionary

        Returns:
            Log collector instance

        Raises:
            ValueError: If collector type is not supported
        """
        if collector_type == CollectorType.STDOUT:
            return StdoutCollector()
        elif collector_type == CollectorType.OTEL:
            return OtelCollector()
        elif collector_type == CollectorType.AUTO:
            return LogCollectorFactory.create_auto(config)
        else:
            raise ValueError(f"Unsupported collector type: {collector_type}")

    @staticmethod
    def create_auto(config: dict[str, Any] | None = None) -> LogCollector:
        """Automatically create appropriate collector.

        Args:
            config: Configuration dictionary

        Returns:
            Log collector instance
        """
        # Check if OTEL is enabled
        use_otel = False
        if config:
            use_otel = config.get("use_otel_logging", False)

        if use_otel:
            return OtelCollector()
        else:
            return StdoutCollector()

    @staticmethod
    def create_for_agent(agent_type: str, config: dict[str, Any] | None = None) -> LogCollector:
        """Create collector for specific Agent.

        Args:
            agent_type: Agent type
            config: Configuration dictionary

        Returns:
            Log collector instance
        """
        # Claude Code uses OTEL
        if agent_type == "claude-code":
            return OtelCollector()

        # Other agents use stdout
        return StdoutCollector()
