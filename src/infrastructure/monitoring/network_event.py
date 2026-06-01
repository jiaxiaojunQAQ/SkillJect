"""
Network event data classes.

Defines various event types captured during network monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class NetworkEventType(Enum):
    """Network event type."""

    CONNECT = "connect"  # TCP/UDP connection
    DNS_QUERY = "dns_query"  # DNS query
    HTTP_REQUEST = "http_request"  # HTTP request
    HTTPS_REQUEST = "https_request"  # HTTPS request
    DATA_TRANSFER = "data_transfer"  # Data transfer


class NetworkDirection(Enum):
    """Network direction."""

    OUTBOUND = "outbound"  # Outbound connection
    INBOUND = "inbound"  # Inbound connection


@dataclass
class NetworkEvent:
    """
    Network event base class.

    Attributes:
        timestamp: Event timestamp
        event_type: Event type
        direction: Network direction
        pid: Process ID
        comm: Process command name
        src_ip: Source IP address
        src_port: Source port
        dst_ip: Destination IP address
        dst_port: Destination port
        protocol: Protocol type (tcp/udp)
        domain: Destination domain name (if resolvable)
        data_size: Data transfer size (bytes)
        raw_log: Raw log line
    """

    timestamp: datetime
    event_type: NetworkEventType
    direction: NetworkDirection
    pid: int
    comm: str
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    protocol: str = "tcp"
    domain: str | None = None
    data_size: int = 0
    raw_log: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "direction": self.direction.value,
            "pid": self.pid,
            "comm": self.comm,
            "src_ip": self.src_ip,
            "src_port": self.src_port,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "domain": self.domain,
            "data_size": self.data_size,
            "raw_log": self.raw_log,
        }

    @classmethod
    def from_iptables_log(cls, log_line: str) -> Optional["NetworkEvent"]:
        """
        Parse network event from iptables LOG format.

        Log format example:
        Jan 29 10:30:45 kernel: NET_OUT: IN= OUT=eth0 SRC=172.17.0.2 DST=93.184.216.34 DPT=443

        Args:
            log_line: iptables log line

        Returns:
            NetworkEvent or None
        """
        import re
        from datetime import datetime

        # Parse iptables LOG format
        pattern = r"NET_(OUT|IN):.*SRC=(\S+)\s+DST=(\S+)\s+SPT=(\d+)\s+DPT=(\d+)"
        match = re.search(pattern, log_line)

        if not match:
            return None

        direction_str, src_ip, dst_ip, src_port, dst_port = match.groups()

        # Try to extract timestamp
        timestamp_pattern = r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"
        timestamp_match = re.search(timestamp_pattern, log_line)
        if timestamp_match:
            try:
                # Add year (iptables logs don't include year)
                timestamp_str = f"{datetime.now().year} {timestamp_match.group(1)}"
                timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Determine direction
        direction = (
            NetworkDirection.OUTBOUND if direction_str == "OUT" else NetworkDirection.INBOUND
        )

        # Try to extract PID (some iptables configurations may include)
        pid_match = re.search(r"PID=(\d+)", log_line)
        pid = int(pid_match.group(1)) if pid_match else 0

        # Try to extract process name
        comm_match = re.search(r"COMM=(\S+)", log_line)
        comm = comm_match.group(1) if comm_match else "unknown"

        return cls(
            timestamp=timestamp,
            event_type=NetworkEventType.CONNECT,
            direction=direction,
            pid=pid,
            comm=comm,
            src_ip=src_ip,
            src_port=int(src_port),
            dst_ip=dst_ip,
            dst_port=int(dst_port),
            protocol="tcp",
            raw_log=log_line,
        )

    @classmethod
    def from_bpftrace_log(cls, log_line: str) -> Optional["NetworkEvent"]:
        """
        Parse network event from bpftrace output.

        Log format example:
        10:30:45 connect: pid=1234 comm=curl addr=93.184.216.34:443

        Args:
            log_line: bpftrace output line

        Returns:
            NetworkEvent or None
        """
        import re
        from datetime import datetime

        # Parse bpftrace connect output
        pattern = r"(\d{2}:\d{2}:\d{2})\s+connect:\s+pid=(\d+)\s+comm=(\S+)\s+addr=([\d\.]+):(\d+)"
        match = re.match(pattern, log_line)

        if not match:
            return None

        time_str, pid_str, comm, dst_ip, dst_port_str = match.groups()

        # Build timestamp
        timestamp = datetime.now().replace(
            hour=int(time_str.split(":")[0]),
            minute=int(time_str.split(":")[1]),
            second=int(time_str.split(":")[2]),
            microsecond=datetime.now().microsecond,
        )

        return cls(
            timestamp=timestamp,
            event_type=NetworkEventType.CONNECT,
            direction=NetworkDirection.OUTBOUND,
            pid=int(pid_str),
            comm=comm,
            src_ip="0.0.0.0",
            src_port=0,
            dst_ip=dst_ip,
            dst_port=int(dst_port_str),
            protocol="tcp",
            raw_log=log_line,
        )

    def is_suspicious(self, known_domains: list[str] | None = None) -> bool:
        """
        Determine if event is suspicious.

        Args:
            known_domains: Known legitimate domain whitelist

        Returns:
            Whether event is suspicious
        """
        # Check if domain is in whitelist
        if known_domains and self.domain:
            for known in known_domains:
                if known in self.domain or self.domain in known:
                    return False

        # By default, consider all external network activity suspicious
        return not self._is_local_ip(self.dst_ip)

    def _is_local_ip(self, ip: str) -> bool:
        """Check if IP is local."""
        local_prefixes = [
            "127.",
            "10.",
            "172.16.",
            "172.17.",  # Docker default bridge
            "172.18.",
            "192.168.",
            "::1",
            "fe80:",
        ]

        return any(ip.startswith(prefix) for prefix in local_prefixes)


@dataclass
class NetworkActivityLog:
    """
    Network activity log collection.

    Attributes:
        start_time: Monitoring start time
        end_time: Monitoring end time
        events: Event list
        total_bytes: Total transferred bytes
        unique_destinations: Unique destination address set
    """

    start_time: datetime
    end_time: datetime
    events: list[NetworkEvent] = field(default_factory=list)
    total_bytes: int = 0
    unique_destinations: set[str] = field(default_factory=set)

    def add_event(self, event: NetworkEvent) -> None:
        """Add event."""
        self.events.append(event)
        self.total_bytes += event.data_size
        if event.dst_ip:
            self.unique_destinations.add(event.dst_ip)

    def get_outbound_events(self) -> list[NetworkEvent]:
        """Get all outbound events."""
        return [e for e in self.events if e.direction == NetworkDirection.OUTBOUND]

    def get_events_by_pid(self, pid: int) -> list[NetworkEvent]:
        """Get events for specified PID."""
        return [e for e in self.events if e.pid == pid]

    def get_events_by_comm(self, comm: str) -> list[NetworkEvent]:
        """Get events for specified process name."""
        return [e for e in self.events if e.comm == comm]

    def get_suspicious_events(self, known_domains: list[str] | None = None) -> list[NetworkEvent]:
        """Get all suspicious events."""
        return [e for e in self.events if e.is_suspicious(known_domains)]

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "event_count": len(self.events),
            "total_bytes": self.total_bytes,
            "unique_destinations": list(self.unique_destinations),
            "events": [e.to_dict() for e in self.events],
        }
