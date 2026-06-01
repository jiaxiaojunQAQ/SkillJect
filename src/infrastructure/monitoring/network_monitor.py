"""
Network Monitoring Module - Monitor all network activity in container

Supports two modes:
1. eBPF mode: Use bpftrace to monitor network system calls
2. iptables LOG mode: Use iptables LOG target to record connections

Responsibilities:
- Start/stop network monitoring
- Collect network activity logs
- Parse and format logs
"""

import asyncio
import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from .network_event import NetworkActivityLog, NetworkEvent


class MonitorMode(Enum):
    """Monitoring mode."""

    EBPF = "ebpf"  # Use bpftrace (requires root privileges)
    IPTABLES = "iptables"  # Use iptables LOG (requires root privileges)
    PASSIVE = "passive"  # Passive mode, only read existing logs


@dataclass
class MonitorConfig:
    """
    Monitoring configuration.

    Attributes:
        mode: Monitoring mode
        log_path: Log file path
        bpftrace_path: bpftrace executable path
        monitor_dns: Whether to monitor DNS queries
        monitor_http: Whether to monitor HTTP/HTTPS requests
        allowed_domains: Allowed domain whitelist
    """

    mode: MonitorMode = MonitorMode.IPTABLES
    log_path: str = "/var/log/network_monitor.log"
    bpftrace_path: str = "/usr/bin/bpftrace"
    monitor_dns: bool = True
    monitor_http: bool = True
    allowed_domains: list[str] = field(default_factory=list)


class NetworkMonitor:
    """
    Network monitor.

    Monitors all network activity in the container, recording connections,
    DNS queries, and data transfers.
    """

    # iptables LOG chain name
    IPTABLES_CHAIN = "NET_MONITOR"

    def __init__(self, config: MonitorConfig | None = None):
        """
        Initialize network monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitorConfig()
        self._monitoring = False
        self._process: subprocess.Popen | None = None
        self._log_file: tempfile.SpooledTemporaryFile | None = None
        self._start_time: datetime | None = None

    async def start_monitoring(self) -> bool:
        """
        Start network monitoring.

        Returns:
            Whether startup was successful
        """
        if self._monitoring:
            return True

        self._start_time = datetime.now()
        self._log_file = tempfile.SpooledTemporaryFile(
            max_size=1024 * 1024, mode="w+", encoding="utf-8"
        )

        if self.config.mode == MonitorMode.EBPF:
            success = await self._start_ebpf_monitor()
        elif self.config.mode == MonitorMode.IPTABLES:
            success = await self._start_iptables_monitor()
        else:
            success = await self._start_passive_monitor()

        if success:
            self._monitoring = True

        return success

    async def stop_monitoring(self) -> None:
        """Stop network monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False

        # Stop monitoring process
        if self._process:
            try:
                self._process.terminate()
                await asyncio.sleep(0.5)
                if self._process.poll() is None:
                    self._process.kill()
            except Exception:
                pass

        # Clean up iptables rules
        if self.config.mode == MonitorMode.IPTABLES:
            await self._cleanup_iptables()

    async def get_network_activity(self) -> NetworkActivityLog:
        """
        Get network activity log.

        Returns:
            NetworkActivityLog network activity log
        """
        if not self._log_file:
            return NetworkActivityLog(
                start_time=datetime.now(),
                end_time=datetime.now(),
            )

        # Read log content
        self._log_file.seek(0)
        log_content = self._log_file.read()

        # Parse events
        events = self._parse_logs(log_content)

        activity_log = NetworkActivityLog(
            start_time=self._start_time or datetime.now(),
            end_time=datetime.now(),
        )

        for event in events:
            activity_log.add_event(event)

        return activity_log

    async def clear_logs(self) -> None:
        """Clear logs."""
        if self._log_file:
            self._log_file.close()
            self._log_file = tempfile.SpooledTemporaryFile(
                max_size=1024 * 1024, mode="w+", encoding="utf-8"
            )

    async def _start_ebpf_monitor(self) -> bool:
        """
        Start eBPF monitoring.

        Use bpftrace to monitor connect system calls.

        Returns:
            Whether startup was successful
        """
        # Check if bpftrace is available
        if not await self._check_command(self.config.bpftrace_path):
            return False

        # bpftrace script
        bpftrace_script = """
#!/usr/bin/env bpftrace
tracepoint:syscalls:sys_enter_connect {
    printf("%s connect: pid=%d comm=%s addr=%s\\n",
           strftime("%H:%M:%S", nsecs),
           pid, comm,
           ntop(args->sockaddr->sa_family, args->sockaddr));
}
"""

        # Start bpftrace
        proc = subprocess.Popen(
            [self.config.bpftrace_path, "-e", bpftrace_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN),
        )

        self._process = proc

        # Start log reading task
        asyncio.create_task(self._read_process_output(proc))

        return True

    async def _start_iptables_monitor(self) -> bool:
        """
        Start iptables LOG monitoring.

        Record network connections by adding iptables LOG rules.

        Returns:
            Whether startup was successful
        """
        try:
            # Check if has root privileges
            if os.geteuid() != 0:
                # If not root, try using sudo
                sudo_prefix = ["sudo"]
            else:
                sudo_prefix = []

            # Create custom chain
            subprocess.run(
                sudo_prefix + ["iptables", "-N", self.IPTABLES_CHAIN],
                capture_output=True,
            )

            # Flush old rules in chain
            subprocess.run(
                sudo_prefix + ["iptables", "-F", self.IPTABLES_CHAIN],
                capture_output=True,
            )

            # Add outbound connection logging rule
            subprocess.run(
                sudo_prefix
                + [
                    "iptables",
                    "-A",
                    self.IPTABLES_CHAIN,
                    "-j",
                    "LOG",
                    "--log-prefix",
                    "NET_OUT: ",
                ],
                capture_output=True,
            )

            # Add inbound connection logging rule
            subprocess.run(
                sudo_prefix
                + [
                    "iptables",
                    "-A",
                    self.IPTABLES_CHAIN,
                    "-j",
                    "LOG",
                    "--log-prefix",
                    "NET_IN: ",
                ],
                capture_output=True,
            )

            # Insert custom chain into OUTPUT chain
            subprocess.run(
                sudo_prefix
                + [
                    "iptables",
                    "-I",
                    "OUTPUT",
                    "1",
                    "-j",
                    self.IPTABLES_CHAIN,
                ],
                capture_output=True,
            )

            # Start log monitoring
            proc = subprocess.Popen(
                ["tail", "-f", "/var/log/kern.log", "/var/log/syslog", "/var/log/messages"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN),
            )

            self._process = proc
            asyncio.create_task(self._read_process_output(proc))

            return True

        except Exception:
            return False

    async def _start_passive_monitor(self) -> bool:
        """
        Start passive monitoring.

        Only read existing log files, no active monitoring.

        Returns:
            Whether startup was successful
        """
        self._monitoring = True
        return True

    async def _cleanup_iptables(self) -> None:
        """Clean up iptables rules."""
        try:
            if os.geteuid() != 0:
                sudo_prefix = ["sudo"]
            else:
                sudo_prefix = []

            # Delete custom chain from OUTPUT chain
            subprocess.run(
                sudo_prefix + ["iptables", "-D", "OUTPUT", "-j", self.IPTABLES_CHAIN],
                capture_output=True,
            )

            # Delete custom chain
            subprocess.run(
                sudo_prefix + ["iptables", "-F", self.IPTABLES_CHAIN],
                capture_output=True,
            )
            subprocess.run(
                sudo_prefix + ["iptables", "-X", self.IPTABLES_CHAIN],
                capture_output=True,
            )
        except Exception:
            pass

    async def _read_process_output(self, proc: subprocess.Popen) -> None:
        """
        Read process output and write to log file.

        Args:
            proc: Monitoring process
        """
        try:
            while self._monitoring and proc.poll() is None:
                line = proc.stdout.readline()
                if line:
                    self._write_log(line.strip())
                else:
                    await asyncio.sleep(0.1)
        except Exception:
            pass

    def _write_log(self, line: str) -> None:
        """Write to log."""
        if self._log_file and not self._log_file.closed:
            self._log_file.write(f"{line}\n")
            self._log_file.flush()

    def _parse_logs(self, log_content: str) -> list[NetworkEvent]:
        """
        Parse log content.

        Args:
            log_content: Log content

        Returns:
            List of network events
        """
        events = []

        for line in log_content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try parsing from iptables log
            event = NetworkEvent.from_iptables_log(line)
            if event:
                events.append(event)
                continue

            # Try parsing from bpftrace log
            event = NetworkEvent.from_bpftrace_log(line)
            if event:
                events.append(event)
                continue

        return events

    async def _check_command(self, cmd: str) -> bool:
        """Check if command is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    @property
    def is_monitoring(self) -> bool:
        """Whether monitoring is active."""
        return self._monitoring


class SimpleNetworkMonitor:
    """
    Simplified network monitor.

    For basic network monitoring in restricted environments.
    Does not require root privileges, gets network information by reading /proc filesystem.

    Supports process monitoring to capture actual executing network tool processes.
    """

    # Network-related process names
    NETWORK_PROCESSES = {
        "curl",
        "wget",
        "fetch",
        "http",
        "nc",
        "netcat",
        "telnet",
        "python",  # May use requests/urllib
        "python3",
        "node",  # May use fetch/axios
    }

    def __init__(self):
        self._start_time: datetime | None = None
        self._baseline_connections: set[tuple[str, int]] = set()
        self._baseline_pids: set[int] = set()
        self._network_pids_during_execution: set[int] = set()

    async def capture_baseline(self) -> set[tuple[str, int]]:
        """
        Capture baseline network connections.

        Returns:
            Baseline connection set {(remote_ip, remote_port), ...}
        """
        connections = set()

        try:
            # Read /proc/net/tcp
            with open("/proc/net/tcp") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        # Parse local and remote addresses
                        # Format: local_address remote_address st ...
                        try:
                            remote_addr = parts[2]
                            if ":" in remote_addr:
                                ip_hex, port_hex = remote_addr.split(":")
                                ip = self._parse_hex_ip(ip_hex)
                                port = int(port_hex, 16)
                                connections.add((ip, port))
                        except (ValueError, IndexError):
                            continue
        except Exception:
            pass

        self._baseline_connections = connections
        return connections

    async def get_new_connections(self) -> list[tuple[str, int]]:
        """
        Get new network connections.

        Returns:
            List of new connections [(remote_ip, remote_port), ...]
        """
        current_connections = set()

        try:
            with open("/proc/net/tcp") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        try:
                            remote_addr = parts[2]
                            if ":" in remote_addr:
                                ip_hex, port_hex = remote_addr.split(":")
                                ip = self._parse_hex_ip(ip_hex)
                                port = int(port_hex, 16)
                                current_connections.add((ip, port))
                        except (ValueError, IndexError):
                            continue
        except Exception:
            pass

        # Return new connections
        new_connections = current_connections - self._baseline_connections
        return list(new_connections)

    def _parse_hex_ip(self, hex_ip: str) -> str:
        """
        Parse hexadecimal IP address.

        Args:
            hex_ip: Hexadecimal IP (little-endian)

        Returns:
            Dotted decimal IP
        """
        # Remove possible colon
        hex_ip = hex_ip.lstrip(":")

        # Ensure 8-digit hex number (4 bytes)
        hex_ip = hex_ip.zfill(8)

        # Convert to integer (little-endian)
        try:
            ip_int = int(hex_ip, 16)
            # Convert to dotted decimal (little-endian: lowest byte first)
            return f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"
        except ValueError:
            return "0.0.0.0"

    async def get_active_connections(self) -> list[dict]:
        """
        Get currently active connections.

        Returns:
            List of connection information
        """
        connections = []

        try:
            with open("/proc/net/tcp") as f:
                # Skip header line
                next(f)

                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 10:
                        try:
                            local_addr = parts[1]
                            remote_addr = parts[2]
                            state = parts[3]

                            local_ip, local_port = self._parse_addr(local_addr)
                            remote_ip, remote_port = self._parse_addr(remote_addr)

                            connections.append(
                                {
                                    "local_ip": local_ip,
                                    "local_port": local_port,
                                    "remote_ip": remote_ip,
                                    "remote_port": remote_port,
                                    "state": state,
                                }
                            )
                        except (ValueError, IndexError):
                            continue
        except Exception:
            pass

        return connections

    def _parse_addr(self, addr: str) -> tuple[str, int]:
        """Parse address string."""
        if ":" not in addr:
            return ("0.0.0.0", 0)

        ip_hex, port_hex = addr.split(":")
        ip = self._parse_hex_ip(ip_hex)
        port = int(port_hex, 16)
        return (ip, port)

    async def capture_process_baseline(self) -> set[int]:
        """
        Capture baseline process PIDs.

        Record network-related process PIDs existing at test start,
        for comparing with processes started during testing.

        Returns:
            Baseline process PID set
        """
        self._baseline_pids = set()
        self._network_pids_during_execution.clear()

        try:
            # Read /proc for all processes
            for pid_dir in Path("/proc").glob("[0-9]*"):
                try:
                    pid = int(pid_dir.name)
                    cmdline_path = pid_dir / "cmdline"

                    if cmdline_path.exists():
                        with open(cmdline_path) as f:
                            cmdline = f.read().strip()
                            # Check if network-related process
                            if self._is_network_process(cmdline):
                                self._baseline_pids.add(pid)
                except (ValueError, OSError):
                    continue
        except Exception:
            pass

        return self._baseline_pids.copy()

    async def get_network_processes_during_execution(self) -> list[dict]:
        """
        Get network-related processes during test execution.

        Find newly started network-related processes (curl, wget, etc.)
        during testing by comparing current processes with baseline.

        Returns:
            List of newly started network process information
        """
        new_network_processes = []
        current_pids = set()

        try:
            # Read /proc for all processes
            for pid_dir in Path("/proc").glob("[0-9]*"):
                try:
                    pid = int(pid_dir.name)
                    cmdline_path = pid_dir / "cmdline"
                    stat_path = pid_dir / "stat"

                    if not cmdline_path.exists():
                        continue

                    with open(cmdline_path) as f:
                        cmdline = f.read().strip().replace("\x00", " ")

                    # Check if network-related process
                    if self._is_network_process(cmdline):
                        current_pids.add(pid)

                        # If process not in baseline, it was started during testing
                        if pid not in self._baseline_pids:
                            # Read process start time
                            start_time = 0
                            if stat_path.exists():
                                try:
                                    with open(stat_path) as f:
                                        stat_content = f.read()
                                        # stat format: pid (comm) state ppid ...
                                        # Start time is field 22 (1-indexed)
                                        parts = stat_content.split()
                                        if len(parts) >= 22:
                                            start_time = int(parts[21])
                                except (ValueError, IndexError):
                                    pass

                            # Read process FDs for network connection info
                            connections = []
                            fd_path = pid_dir / "fd"
                            if fd_path.exists():
                                for fd_link in fd_path.glob("*"):
                                    try:
                                        target = os.readlink(fd_link)
                                        if "socket:" in target:
                                            connections.append(target)
                                    except (OSError, ValueError):
                                        pass

                            process_info = {
                                "pid": pid,
                                "cmdline": cmdline[:200],  # Limit length
                                "start_time": start_time,
                                "connections": connections[:5],  # Max 5 connections
                            }
                            new_network_processes.append(process_info)
                            self._network_pids_during_execution.add(pid)

                except (ValueError, OSError):
                    continue
        except Exception:
            pass

        return new_network_processes

    async def get_network_subprocess_children(self, parent_pid: int | None = None) -> list[dict]:
        """
        Get network-related subprocess information.

        Find network-related subprocesses under specified parent process (or all).
        This can detect curl commands launched from scripts.

        Args:
            parent_pid: Parent process PID, if None check all processes

        Returns:
            List of subprocess information
        """
        subprocess_info = []

        try:
            for pid_dir in Path("/proc").glob("[0-9]*"):
                try:
                    pid = int(pid_dir.name)

                    # Skip processes in baseline
                    if pid in self._baseline_pids:
                        continue

                    # Read process status
                    status_path = pid_dir / "status"
                    cmdline_path = pid_dir / "cmdline"

                    if not cmdline_path.exists():
                        continue

                    with open(cmdline_path) as f:
                        cmdline = f.read().strip().replace("\x00", " ")

                    # Only care about network-related processes
                    if not self._is_network_process(cmdline):
                        continue

                    # Get parent process PID
                    ppid = None
                    if status_path.exists():
                        with open(status_path) as f:
                            for line in f:
                                if line.startswith("PPid:"):
                                    ppid = int(line.split()[1])
                                    break

                    # If parent specified, check if matches
                    if parent_pid is not None and ppid != parent_pid:
                        continue

                    # Get process command line arguments, especially curl URLs
                    url = None
                    if "curl" in cmdline.lower():
                        # Extract URL
                        import re

                        url_match = re.search(r'https?://[^\s"\'\`]+', cmdline)
                        if url_match:
                            url = url_match.group(0)

                    subprocess_info.append(
                        {
                            "pid": pid,
                            "ppid": ppid,
                            "cmdline": cmdline[:200],
                            "url": url,
                        }
                    )

                except (ValueError, OSError):
                    continue
        except Exception:
            pass

        return subprocess_info

    def _is_network_process(self, cmdline: str) -> bool:
        """
        Check if process is network-related.

        Args:
            cmdline: Process command line

        Returns:
            Whether process is network-related
        """
        cmdline_lower = cmdline.lower()

        # Direct match known network tools
        for tool in self.NETWORK_PROCESSES:
            if tool in cmdline_lower:
                return True

        # Check for network characteristics (URL, http, etc.)
        network_indicators = [
            "http://",
            "https://",
            "requests.",
            "urllib.",
            "http.get",
            "fetch(",
        ]
        return any(indicator in cmdline_lower for indicator in network_indicators)


# Export monitor factory functions
def create_network_monitor(mode: str = "iptables") -> NetworkMonitor:
    """
    Create network monitor.

    Args:
        mode: Monitoring mode ("ebpf", "iptables", "passive")

    Returns:
        NetworkMonitor instance
    """
    try:
        monitor_mode = MonitorMode(mode.lower())
    except ValueError:
        monitor_mode = MonitorMode.IPTABLES

    return NetworkMonitor(config=MonitorConfig(mode=monitor_mode))


def create_simple_monitor() -> SimpleNetworkMonitor:
    """
    Create simplified network monitor.

    Returns:
        SimpleNetworkMonitor instance
    """
    return SimpleNetworkMonitor()
# mypy: disable-error-code="union-attr,no-untyped-def"
