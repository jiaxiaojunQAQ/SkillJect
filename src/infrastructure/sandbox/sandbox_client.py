"""
Sandbox Client Infrastructure

Provides a clean interface for Sandbox SDK operations,
separating infrastructure code from domain logic.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from opensandbox import Sandbox
from opensandbox.config import ConnectionConfig
from opensandbox.models.filesystem import SearchEntry, WriteEntry

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for sandbox creation."""
    domain: str
    api_key: str
    image: str
    test_timeout: int
    command_timeout: int


class SandboxClient:
    """Client for OpenSandbox SDK operations.

    Encapsulates all Sandbox SDK interactions to keep domain logic clean.
    """

    def __init__(self, config: SandboxConfig):
        """Initialize SandboxClient.

        Args:
            config: Sandbox configuration
        """
        self._config = config
        self._sandbox: Sandbox | None = None

    @property
    def sandbox(self) -> Sandbox | None:
        """Get current sandbox instance."""
        return self._sandbox

    @property
    def is_connected(self) -> bool:
        """Check if sandbox is connected."""
        return self._sandbox is not None

    async def create(self) -> Sandbox:
        """Create sandbox instance.

        Returns:
            Sandbox instance
        """
        config = ConnectionConfig(
            domain=self._config.domain,
            api_key=self._config.api_key,
        )

        create_timeout = max(1, int(self._config.test_timeout))

        try:
            self._sandbox = await asyncio.wait_for(
                Sandbox.create(
                    image=self._config.image,
                    connection_config=config,
                ),
                timeout=float(create_timeout),
            )
        except (asyncio.TimeoutError, TimeoutError) as e:
            raise RuntimeError(f"Sandbox creation timeout after {create_timeout}s") from e

        logger.info(f"[SandboxClient] Sandbox created, ID: {getattr(self._sandbox, 'sandbox_id', 'unknown')}")
        return self._sandbox

    async def destroy(self) -> None:
        """Destroy sandbox instance."""
        if self._sandbox:
            try:
                await self._sandbox.kill()
                await self._sandbox.close()
            except Exception as e:
                logger.warning(f"[SandboxClient] Error destroying sandbox: {e}")
            finally:
                self._sandbox = None

    async def run_command(
        self,
        command: str,
        timeout_seconds: int | None = None,
    ) -> Any:
        """Run command in sandbox.

        Args:
            command: Command to execute
            timeout_seconds: Optional timeout override

        Returns:
            Command result
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        timeout = timeout_seconds if timeout_seconds is not None else self._config.command_timeout
        timeout = max(1, int(timeout))

        return await asyncio.wait_for(
            self._sandbox.commands.run(command=command),
            timeout=float(timeout),
        )

    async def write_file(self, path: str, data: str) -> None:
        """Write file to sandbox.

        Args:
            path: Target path in sandbox
            data: File content
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        await self._sandbox.files.write_file(path=path, data=data)

    async def write_files(self, entries: list[WriteEntry]) -> None:
        """Write multiple files to sandbox.

        Args:
            entries: List of WriteEntry with path and data
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        await self._sandbox.files.create_directories(entries)
        await self._sandbox.files.write_files(entries)

    async def create_directories(self, paths: list[str]) -> None:
        """Create directories in sandbox.

        Args:
            paths: List of directory paths to create
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        entries = [WriteEntry(path=p, data="") for p in paths]
        await self._sandbox.files.create_directories(entries)

    async def read_file(self, path: str) -> str:
        """Read file from sandbox.

        Args:
            path: File path in sandbox

        Returns:
            File content
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        return await self._sandbox.files.read_file(path)

    async def read_bytes(self, path: str) -> bytes:
        """Read file as bytes from sandbox.

        Args:
            path: File path in sandbox

        Returns:
            File content as bytes
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        return await self._sandbox.files.read_bytes(path)

    async def search_files(self, path: str, pattern: str = "*") -> list[SearchEntry]:
        """Search for files in sandbox.

        Args:
            path: Directory path to search
            pattern: Glob pattern

        Returns:
            List of matching entries
        """
        if not self._sandbox:
            raise RuntimeError("Sandbox not connected. Call create() first.")

        return await self._sandbox.files.search(path=path, pattern=pattern)


def create_from_config(config: Any) -> "SandboxClient":
    """Create SandboxClient from TwoPhaseExecutionConfig.

    Args:
        config: TwoPhaseExecutionConfig instance

    Returns:
        Configured SandboxClient
    """
    sandbox_config = SandboxConfig(
        domain=config.execution.sandbox.get_active_domain(),
        api_key=config.execution.sandbox.api_key or "",
        image=config.execution.sandbox.get_active_image(),
        test_timeout=config.execution.test_timeout,
        command_timeout=config.execution.command_timeout,
    )
    return SandboxClient(sandbox_config)
