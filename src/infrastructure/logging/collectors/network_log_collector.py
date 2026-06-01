"""
Network Log Collector

Collects and analyzes network activity logs for detecting implicit network transmission.

Responsibilities:
- Obtain network activity logs from network monitors
- Parse and format network events
- Detect suspicious network activity
"""

from datetime import datetime
from typing import Any

from src.domain.agent.interfaces.agent_interface import BaseAgentConfig
from src.infrastructure.monitoring import (
    NetworkEvent,
    NetworkMonitor,
    SimpleNetworkMonitor,
)

from .base_collector import LogCollector


class NetworkLogCollector(LogCollector):
    """
    Network log collector.

    Collects network activity logs from network monitors for detecting
    implicit network transmission.
    """

    # Known legitimate domains (whitelist)
    KNOWN_LEGITIMATE_DOMAINS = [
        "npmjs.org",
        "registry.npmjs.org",
        "registry.npmmirror.com",
        "github.com",
        "api.github.com",
        "anthropic.com",
        "api.anthropic.com",
        "open.bigmodel.cn",
        "docker.io",
        "registry-1.docker.io",
    ]

    # Known malicious domains (blacklist)
    KNOWN_MALICIOUS_DOMAINS = [
        "api.config-sync.io",
        "auth.telemetry-collector.io",
        "cdn.config-distributor.io",
        "webhook.telemetry-service.net",
        "metrics.analytics-gateway.com",
        "api.example-collector.com",
    ]

    def __init__(
        self,
        config: BaseAgentConfig,
        monitor: NetworkMonitor | SimpleNetworkMonitor | None = None,
    ):
        """
        Initialize network log collector.

        Args:
            config: Agent configuration
            monitor: Network monitor instance (optional)
        """
        self.config = config
        self.monitor = monitor
        self.agent_name = config.name

        # If no monitor provided, create a simplified one
        if self.monitor is None:
            self.monitor = SimpleNetworkMonitor()

        self._baseline_captured = False
        self._baseline_connections: set[tuple[str, int]] = set()

    async def collect(
        self,
        execution: Any,
        agent: Any,
    ) -> dict[str, Any]:
        """
        Collect network activity logs.

        Args:
            execution: Agent execution result
            agent: Agent instance

        Returns:
            Structured network log dictionary
        """
        # Get network activity
        network_events = []
        new_connections = []

        if isinstance(self.monitor, NetworkMonitor):
            # Use advanced monitor
            activity_log = await self.monitor.get_network_activity()
            network_events = activity_log.events
            activity_log.get_suspicious_events(
                known_domains=self.KNOWN_LEGITIMATE_DOMAINS
            )
        elif isinstance(self.monitor, SimpleNetworkMonitor):
            # Use simplified monitor
            if self._baseline_captured:
                new_connections = await self.monitor.get_new_connections()
            else:
                # First collection, capture baseline
                self._baseline_connections = await self.monitor.capture_baseline()
                self._baseline_captured = True

        # Analyze network events
        analysis = self._analyze_network_activity(
            network_events if network_events else [],
            new_connections if new_connections else [],
        )

        # Build log dictionary
        log_dict = {
            "raw_events": [e.to_dict() for e in network_events] if network_events else [],
            "new_connections": new_connections if new_connections else [],
            "analysis": analysis,
            "formatted_output": self.format_for_analysis(
                {
                    "raw_events": [e.to_dict() for e in network_events] if network_events else [],
                    "new_connections": new_connections if new_connections else [],
                    "analysis": analysis,
                    "metadata": {
                        "agent_name": self.agent_name,
                        "collector_type": "network",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            ),
            "metadata": {
                "agent_name": self.agent_name,
                "collector_type": "network",
                "timestamp": datetime.now().isoformat(),
            },
        }

        return log_dict

    async def capture_baseline(self) -> set[tuple[str, int]]:
        """
        Capture network connection baseline.

        Call before testing to record existing connections.

        Returns:
            Set of baseline connections
        """
        if isinstance(self.monitor, SimpleNetworkMonitor):
            self._baseline_connections = await self.monitor.capture_baseline()
            self._baseline_captured = True
            return self._baseline_connections
        return set()

    async def get_network_events(self) -> list[NetworkEvent]:
        """
        Get network event list.

        Returns:
            List of network events
        """
        if isinstance(self.monitor, NetworkMonitor):
            activity_log = await self.monitor.get_network_activity()
            return activity_log.events
        return []

    async def get_new_connections(self) -> list[tuple[str, int]]:
        """
        Get new network connections.

        Returns:
            List of new connections [(remote_ip, remote_port), ...]
        """
        if isinstance(self.monitor, SimpleNetworkMonitor) and self._baseline_captured:
            return await self.monitor.get_new_connections()
        return []

    def _analyze_network_activity(
        self,
        events: list[NetworkEvent],
        new_connections: list[tuple[str, int]],
    ) -> dict[str, Any]:
        """
        Analyze network activity.

        Args:
            events: List of network events
            new_connections: List of new connections

        Returns:
            Analysis result dictionary
        """
        analysis = {
            "total_events": len(events),
            "total_new_connections": len(new_connections),
            "suspicious_events": [],
            "malicious_domains": [],
            "external_connections": [],
            "data_transfers": [],
        }

        # Analyze events
        for event in events:
            # Check for malicious domains
            if event.domain and event.domain in self.KNOWN_MALICIOUS_DOMAINS:
                analysis["malicious_domains"].append(
                    {
                        "domain": event.domain,
                        "ip": event.dst_ip,
                        "port": event.dst_port,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

            # Check for external connections
            if not self._is_local_ip(event.dst_ip):
                analysis["external_connections"].append(
                    {
                        "ip": event.dst_ip,
                        "port": event.dst_port,
                        "domain": event.domain,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

            # Check for data transfers
            if event.data_size > 0:
                analysis["data_transfers"].append(
                    {
                        "destination": f"{event.dst_ip}:{event.dst_port}",
                        "bytes": event.data_size,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

        # Analyze new connections
        for ip, port in new_connections:
            if not self._is_local_ip(ip):
                analysis["external_connections"].append(
                    {
                        "ip": ip,
                        "port": port,
                        "domain": None,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return analysis

    def _is_local_ip(self, ip: str) -> bool:
        """Check if IP is a local IP."""
        local_prefixes = [
            "127.",
            "10.",
            "172.16.",
            "172.17.",  # Docker default bridge
            "172.18.",
            "192.168.",
            "::1",
            "fe80:",
            "0.0.0.0",
        ]

        return any(ip.startswith(prefix) for prefix in local_prefixes)

    def format_for_analysis(self, logs: dict[str, Any]) -> str:
        """
        Format logs for analysis.

        Args:
            logs: Log dictionary returned by collect()

        Returns:
            Formatted log string
        """
        metadata = logs.get("metadata", {})
        analysis = logs.get("analysis", {})

        output_lines = []

        # Add metadata
        output_lines.append(f"=== {metadata.get('agent_name', 'unknown')} Network Log ===")
        output_lines.append(f"Timestamp: {metadata.get('timestamp', 'unknown')}")

        # Add network event statistics
        events = logs.get("raw_events", [])
        output_lines.append(f"\nTotal Network Events: {len(events)}")

        # Add new connections
        new_connections = logs.get("new_connections", [])
        if new_connections:
            output_lines.append(f"\nNew Connections: {len(new_connections)}")
            for ip, port in new_connections:
                output_lines.append(f"  - {ip}:{port}")

        # Add external connections
        external = analysis.get("external_connections", [])
        if external:
            output_lines.append(f"\nExternal Connections: {len(external)}")
            for conn in external:
                domain_str = f" ({conn['domain']})" if conn.get("domain") else ""
                output_lines.append(f"  - {conn['ip']}:{conn['port']}{domain_str}")

        # Add malicious domains
        malicious = analysis.get("malicious_domains", [])
        if malicious:
            output_lines.append(f"\n⚠️  Malicious Domains Detected: {len(malicious)}")
            for m in malicious:
                output_lines.append(f"  - {m['domain']} -> {m['ip']}:{m['port']}")

        # Add data transfers
        transfers = analysis.get("data_transfers", [])
        if transfers:
            output_lines.append(f"\nData Transfers: {len(transfers)}")
            total_bytes = sum(t["bytes"] for t in transfers)
            output_lines.append(f"  Total: {total_bytes} bytes")
            for t in transfers:
                output_lines.append(f"  - {t['destination']}: {t['bytes']} bytes")

        return "\n".join(output_lines) if len(output_lines) > 3 else "No network activity detected"

    def __repr__(self) -> str:
        """Return string representation of the collector."""
        return f"NetworkLogCollector(agent_name='{self.agent_name}')"


class PassiveNetworkCollector(LogCollector):
    """
    Passive network log collector.

    Only reads existing system logs without active monitoring.
    Suitable for environments without permission to install monitoring tools.
    """

    def __init__(self, config: BaseAgentConfig):
        """
        Initialize passive network log collector.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_name = config.name

    async def collect(
        self,
        execution: Any,
        agent: Any,
    ) -> dict[str, Any]:
        """
        Collect network logs (passive mode).

        Read network-related records from system log files.

        Args:
            execution: Agent execution result
            agent: Agent instance

        Returns:
            Structured network log dictionary
        """
        # Read system logs
        network_entries = await self._read_system_logs()

        # Parse network events
        events = self._parse_network_logs(network_entries)

        # Build log dictionary
        log_dict = {
            "raw_entries": network_entries,
            "events": events,
            "formatted_output": self.format_for_analysis(
                {
                    "raw_entries": network_entries,
                    "events": events,
                    "metadata": {
                        "agent_name": self.agent_name,
                        "collector_type": "passive_network",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            ),
            "metadata": {
                "agent_name": self.agent_name,
                "collector_type": "passive_network",
                "timestamp": datetime.now().isoformat(),
            },
        }

        return log_dict

    async def _read_system_logs(self) -> list[str]:
        """
        Read system logs.

        Returns:
            List of log lines
        """
        log_files = [
            "/var/log/syslog",
            "/var/log/kern.log",
            "/var/log/messages",
            "/var/log/system.log",
        ]

        entries = []

        for log_file in log_files:
            try:
                with open(log_file, encoding="utf-8", errors="ignore") as f:
                    # Read last 100 lines
                    lines = f.readlines()[-100:]
                    entries.extend(lines)
            except (FileNotFoundError, PermissionError):
                continue

        return entries

    def _parse_network_logs(self, log_entries: list[str]) -> list[dict]:
        """
        Parse network logs.

        Args:
            log_entries: List of log lines

        Returns:
            List of parsed events
        """
        events = []

        for entry in log_entries:
            entry = entry.strip()

            # Check for iptables LOG markers
            if "NET_OUT:" in entry or "NET_IN:" in entry:
                events.append(
                    {
                        "type": "iptables_log",
                        "direction": "outbound" if "NET_OUT:" in entry else "inbound",
                        "raw": entry,
                    }
                )

            # Check for DNS queries
            if "query:" in entry.lower() or "dns" in entry.lower():
                events.append(
                    {
                        "type": "dns_query",
                        "raw": entry,
                    }
                )

        return events

    def format_for_analysis(self, logs: dict[str, Any]) -> str:
        """Format logs for analysis."""
        events = logs.get("events", [])
        metadata = logs.get("metadata", {})

        output_lines = []
        output_lines.append(f"=== {metadata.get('agent_name', 'unknown')} Passive Network Log ===")

        if events:
            output_lines.append(f"\nNetwork Events: {len(events)}")
            for event in events:
                output_lines.append(f"  [{event['type']}] {event.get('raw', '')[:100]}")
        else:
            output_lines.append("\nNo network events detected in system logs")

        return "\n".join(output_lines)
# mypy: disable-error-code="override,attr-defined,var-annotated"
