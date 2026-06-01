"""
Log Collector Module Exports

Exports public interfaces for log collector related modules.

Available log collectors:
- StderrLogCollector: General log collection for CLI agents
- ClaudeOtelLogCollector: Claude Code specific OpenTelemetry log collection
- JsonLogCollector: JSON-formatted log collection for CLI agents (OpenClaw)
- NetworkLogCollector: Network activity log collection
- PassiveNetworkCollector: Passive network log collection
"""

from .base_collector import LogCollector, OtelCollector, StdoutCollector
from .claude_otel_log_collector import ClaudeOtelLogCollector
from .json_log_collector import JsonLogCollector
from .network_log_collector import NetworkLogCollector, PassiveNetworkCollector
from .stderr_log_collector import StderrLogCollector

__all__ = [
    "LogCollector",
    "StdoutCollector",
    "OtelCollector",
    "StderrLogCollector",
    "ClaudeOtelLogCollector",
    "JsonLogCollector",
    "NetworkLogCollector",
    "PassiveNetworkCollector",
]
