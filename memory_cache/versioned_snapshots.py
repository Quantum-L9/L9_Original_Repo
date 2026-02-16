"""
Versioned Snapshots with Optimistic Locking for Working Memory

Enables concurrent readers without blocking, detects write conflicts.

Usage:
    from memory_cache.versioned_snapshots import VersionedSnapshotService

    snapshot_service = VersionedSnapshotService(cache)
    snapshot = await snapshot_service.get_snapshot(agent_id="agent_123")

    # Modify snapshot
    snapshot.data['new_fact'] = "value"

    # Commit with optimistic lock check
    success = await snapshot_service.commit_snapshot(snapshot)
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class MemorySnapshot:
    """
    Versioned snapshot of working memory state.

    Attributes:
        agent_id: Agent whose memory this snapshot represents
        version: Monotonic version number (increments on each write)
        data: The actual memory data (dict)
        created_at: When snapshot was created
        metadata: Additional snapshot metadata
    """

    agent_id: str
    version: int
    data: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize snapshot to dictionary."""
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemorySnapshot":
        """Deserialize snapshot from dictionary."""
        return cls(
            agent_id=d["agent_id"],
            version=d["version"],
            data=d["data"],
            created_at=datetime.fromisoformat(d["created_at"]),
            metadata=d.get("metadata", {}),
        )


class OptimisticLockError(Exception):
    """Raised when a snapshot commit fails due to version conflict."""

    pass


class VersionedSnapshotService:
    """
    Manages versioned snapshots of working memory with optimistic locking.

    Concurrency model:
    - Readers always get a consistent snapshot (never blocked)
    - Writers use optimistic locking (commit fails if version changed)
    - Version numbers are monotonically increasing

    Example workflow:
        # Thread A: Read and modify
        snapshot_a = await service.get_snapshot("agent_123")  # version=5
        snapshot_a.data['key'] = 'value_a'

        # Thread B: Read and modify (concurrent)
        snapshot_b = await service.get_snapshot("agent_123")  # version=5
        snapshot_b.data['key'] = 'value_b'

        # Thread A commits first
        await service.commit_snapshot(snapshot_a)  # SUCCESS, version -> 6

        # Thread B commit fails (version mismatch)
        try:
            await service.commit_snapshot(snapshot_b)  # FAIL, expected version=5, got version=6
        except OptimisticLockError:
            # Retry: fetch new snapshot and reapply changes
            pass
    """

    def __init__(self, cache_service, substrate_service=None):
        """
        Initialize the versioned snapshot service.

        Args:
            cache_service: Redis cache for storing snapshots
            substrate_service: Optional substrate for persisting snapshots
        """
        self.cache = cache_service
        self.substrate = substrate_service
        self._version_locks: dict[str, asyncio.Lock] = {}

        logger.info("VersionedSnapshotService initialized")

    def _get_version_key(self, agent_id: str) -> str:
        """Get Redis key for version counter."""
        return f"snapshot_version:{agent_id}"

    def _get_snapshot_key(self, agent_id: str) -> str:
        """Get Redis key for snapshot data."""
        return f"snapshot_data:{agent_id}"

    @must_stay_async("callers use await")
    async def _get_or_create_lock(self, agent_id: str) -> asyncio.Lock:
        """Get or create a lock for an agent's version updates."""
        if agent_id not in self._version_locks:
            self._version_locks[agent_id] = asyncio.Lock()
        return self._version_locks[agent_id]

    async def get_snapshot(self, agent_id: str) -> MemorySnapshot:
        """
        Get current versioned snapshot for an agent.

        This operation never blocks - returns latest committed snapshot.

        Args:
            agent_id: Agent whose memory to snapshot

        Returns:
            MemorySnapshot with current version and data
        """
        try:
            # Get current version
            version_key = self._get_version_key(agent_id)
            version = await self.cache.redis.get(version_key)
            version = int(version) if version else 0

            # Get snapshot data
            snapshot_key = self._get_snapshot_key(agent_id)
            snapshot_json = await self.cache.redis.get(snapshot_key)

            if snapshot_json:
                data = json.loads(snapshot_json)
            else:
                # No snapshot exists yet, create empty
                data = {}

            snapshot = MemorySnapshot(agent_id=agent_id, version=version, data=data)

            logger.debug(f"Retrieved snapshot for {agent_id}, version={version}")
            return snapshot

        except Exception as e:
            logger.error(f"Error getting snapshot for {agent_id}: {e}")
            # Return empty snapshot on error
            return MemorySnapshot(agent_id=agent_id, version=0, data={})

    @must_stay_async("callers use await")
    async def commit_snapshot(
        self, snapshot: MemorySnapshot, force: bool = False
    ) -> bool:
        """
        Commit a modified snapshot with optimistic lock check.

        Algorithm:
        1. Acquire lock for agent's version counter
        2. Check current version matches snapshot.version (optimistic lock)
        3. If match: increment version, write data, release lock
        4. If mismatch: raise OptimisticLockError

        Args:
            snapshot: Modified snapshot to commit
            force: If True, skip version check (dangerous!)

        Returns:
            True if commit succeeded

        Raises:
            OptimisticLockError: If version mismatch detected (concurrent write)
        """
        lock = await self._get_or_create_lock(snapshot.agent_id)

        async with lock:
            # Check current version
            version_key = self._get_version_key(snapshot.agent_id)
            current_version = await self.cache.redis.get(version_key)
            current_version = int(current_version) if current_version else 0

            if not force and current_version != snapshot.version:
                error_msg = (
                    f"Optimistic lock failure for {snapshot.agent_id}: "
                    f"expected version={snapshot.version}, got version={current_version}"
                )
                logger.warning(error_msg)
                raise OptimisticLockError(error_msg)

            # Increment version
            new_version = current_version + 1

            # Write snapshot data
            snapshot_key = self._get_snapshot_key(snapshot.agent_id)
            snapshot_json = json.dumps(snapshot.data)

            await self.cache.redis.set(snapshot_key, snapshot_json)
            await self.cache.redis.set(version_key, new_version)

            logger.info(
                f"Committed snapshot for {snapshot.agent_id}: "
                f"version {current_version} -> {new_version}"
            )

            # Optionally persist to substrate
            if self.substrate:
                try:
                    await self.substrate.writepacket(
                        packettype="MEMORY_SNAPSHOT",
                        content=snapshot.to_dict(),
                        metadata={"version": new_version},
                    )
                except Exception as e:
                    logger.error(f"Failed to persist snapshot to substrate: {e}")

            return True

    async def get_version(self, agent_id: str) -> int:
        """
        Get current version number for an agent's memory.

        Args:
            agent_id: Agent to check

        Returns:
            Current version number
        """
        version_key = self._get_version_key(agent_id)
        version = await self.cache.redis.get(version_key)
        return int(version) if version else 0

    async def rollback_snapshot(self, agent_id: str, target_version: int) -> bool:
        """
        Rollback to a previous snapshot version (if available in substrate).

        Args:
            agent_id: Agent whose memory to rollback
            target_version: Version to rollback to

        Returns:
            True if rollback succeeded
        """
        if not self.substrate:
            logger.error("Cannot rollback: substrate service not configured")
            return False

        try:
            # Query substrate for historical snapshot
            historical_snapshot = await self.substrate.querypackets(
                packettype="MEMORY_SNAPSHOT",
                filters={"agent_id": agent_id, "version": target_version},
            )

            if not historical_snapshot:
                logger.error(f"No snapshot found for version {target_version}")
                return False

            # Restore snapshot (forced commit)
            snapshot = MemorySnapshot.from_dict(historical_snapshot[0]["content"])
            await self.commit_snapshot(snapshot, force=True)

            logger.info(f"Rolled back {agent_id} to version {target_version}")
            return True

        except Exception as e:
            logger.error(f"Error rolling back snapshot: {e}")
            return False
