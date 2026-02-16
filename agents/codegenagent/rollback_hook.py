"""
CodeGenAgent Rollback Hook
==========================

Provides reversion support for CodeGenAgent file emissions.
Registers snapshots of generated files for potential rollback.

Integrates with file_emitter.py rollback mechanism.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Rollback Hook",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:27:30Z",
    "updated_at": "2026-01-15T23:27:30Z",
    "layer": "intelligence",
    "domain": "error_handling",
    "module_name": "rollback_hook",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================


DEFAULT_SNAPSHOT_DIR = ".codegen_snapshots"
MAX_SNAPSHOTS = 50  # Keep last N snapshots


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FileSnapshot:
    """Snapshot of a single file."""

    path: str
    content_hash: str
    content: str | None = None  # May be None if stored to disk
    existed_before: bool = False
    original_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the FileSnapshot, including file path, content hash, existence status before emission, and presence of original content."""
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "existed_before": self.existed_before,
            "has_original": self.original_content is not None,
        }


@dataclass
class Snapshot:
    """A complete generation snapshot."""

    snapshot_id: str
    module_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # File snapshots
    files: list[FileSnapshot] = field(default_factory=list)

    # Metadata
    meta_source: str = ""
    commit_hash: str | None = None

    # Status
    rolled_back: bool = False
    rolled_back_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the Snapshot, including metadata and associated files, suitable for rollback and auditing purposes.

        Args:
            None

        Returns:
            dict: A dictionary containing snapshot ID, module name, creation timestamp, list of file snapshots, and source metadata.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "module_name": self.module_name,
            "created_at": self.created_at.isoformat(),
            "files": [f.to_dict() for f in self.files],
            "meta_source": self.meta_source,
            "commit_hash": self.commit_hash,
            "rolled_back": self.rolled_back,
            "rolled_back_at": self.rolled_back_at.isoformat()
            if self.rolled_back_at
            else None,
        }

    @property
    def file_count(self) -> int:
        """Returns the total number of files in the current snapshot, representing the count of generated files available for rollback."""
        return len(self.files)


@dataclass
class RollbackResult:
    """Returns a dictionary representation of the rollback result, including success status, snapshot ID, restored and deleted files, and errors, for use in CodeGenAgent rollback tracking."""

    """Result of a rollback operation."""

    success: bool
    snapshot_id: str
    files_restored: int = 0
    files_deleted: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the rollback result, including success status, snapshot ID, restored and deleted files, and errors for domain-specific rollback tracking."""
        return {
            "success": self.success,
            "snapshot_id": self.snapshot_id,
            "files_restored": self.files_restored,
            "files_deleted": self.files_deleted,
            "errors": self.errors,
        }


# =============================================================================
# EXCEPTIONS
# =============================================================================


class RollbackHookError(Exception):
    """Exception raised during rollback operations."""

    pass


class SnapshotNotFoundError(RollbackHookError):
    """Exception raised when snapshot is not found."""

    pass


# =============================================================================
# ROLLBACK HOOK
# =============================================================================


class RollbackHook:
    """
    Rollback support for CodeGenAgent.

    Registers file snapshots before generation and supports
    rolling back to previous states.
    """

    def __init__(
        self,
        repo_root: str = "/Users/ib-mac/Projects/L9",
        snapshot_dir: str | None = None,
        max_snapshots: int = MAX_SNAPSHOTS,
        store_content: bool = True,
    ):
        """
        Initialize the Rollback Hook.

        Args:
            repo_root: Repository root path
            snapshot_dir: Directory for snapshot storage
            max_snapshots: Maximum number of snapshots to keep
            store_content: Whether to store file content in snapshots
        """
        self.repo_root = Path(repo_root)
        self.snapshot_dir = (
            Path(snapshot_dir)
            if snapshot_dir
            else self.repo_root / DEFAULT_SNAPSHOT_DIR
        )
        self.max_snapshots = max_snapshots
        self.store_content = store_content

        # In-memory snapshot registry
        self._snapshots: dict[str, Snapshot] = {}

        # Ensure snapshot directory exists
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Load existing snapshots
        self._load_snapshots()

        logger.info(
            "rollback_hook_initialized",
            repo_root=str(self.repo_root),
            snapshot_dir=str(self.snapshot_dir),
            existing_snapshots=len(self._snapshots),
        )

    def setup_reversion(
        self,
        files: dict[str, str],
        module_name: str = "unknown",
        meta_source: str = "",
    ) -> str:
        """
        Set up reversion capability before file emission.

        Captures current state of files that will be modified.

        Args:
            files: Dictionary of file path to new content
            module_name: Name of module being generated
            meta_source: Source meta file path

        Returns:
            Snapshot ID
        """
        # Generate snapshot ID
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"{module_name}_{timestamp}"

        # Create file snapshots
        file_snapshots = []
        for rel_path in files:
            full_path = self.repo_root / rel_path

            snapshot = FileSnapshot(
                path=rel_path,
                content_hash=self._hash_content(files[rel_path]),
                content=files[rel_path] if self.store_content else None,
                existed_before=full_path.exists(),
            )

            # Capture original content if file exists
            if full_path.exists():
                try:
                    snapshot.original_content = full_path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(
                        "could_not_read_original",
                        path=rel_path,
                        error=str(e),
                    )

            file_snapshots.append(snapshot)

        # Create snapshot
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            module_name=module_name,
            files=file_snapshots,
            meta_source=meta_source,
        )

        # Register and persist
        self._snapshots[snapshot_id] = snapshot
        self._persist_snapshot(snapshot)

        # Cleanup old snapshots
        self._cleanup_old_snapshots()

        logger.info(
            "reversion_setup",
            snapshot_id=snapshot_id,
            module_name=module_name,
            file_count=len(file_snapshots),
        )

        return snapshot_id

    def register_snapshot(
        self,
        files: dict[str, str],
        module_name: str = "unknown",
    ) -> str:
        """
        Register a snapshot of generated files.

        Alias for setup_reversion for compatibility.

        Args:
            files: Generated files
            module_name: Module name

        Returns:
            Snapshot ID
        """
        return self.setup_reversion(files, module_name)

    def execute_rollback(self, snapshot_id: str) -> RollbackResult:
        """
        Execute rollback to a previous snapshot.

        Args:
            snapshot_id: ID of snapshot to rollback to

        Returns:
            RollbackResult with details
        """
        result = RollbackResult(
            success=False,
            snapshot_id=snapshot_id,
        )

        if snapshot_id not in self._snapshots:
            result.errors.append(f"Snapshot not found: {snapshot_id}")
            logger.error("snapshot_not_found", snapshot_id=snapshot_id)
            return result

        snapshot = self._snapshots[snapshot_id]

        if snapshot.rolled_back:
            result.errors.append(f"Snapshot already rolled back: {snapshot_id}")
            return result

        logger.info(
            "rollback_started",
            snapshot_id=snapshot_id,
            file_count=snapshot.file_count,
        )

        for file_snap in snapshot.files:
            full_path = self.repo_root / file_snap.path

            try:
                if file_snap.existed_before:
                    # Restore original content
                    if file_snap.original_content is not None:
                        full_path.write_text(
                            file_snap.original_content,
                            encoding="utf-8",
                        )
                        result.files_restored += 1
                        logger.debug("file_restored", path=file_snap.path)
                    else:
                        result.errors.append(
                            f"No original content for {file_snap.path}"
                        )
                else:
                    # Delete file that didn't exist before
                    if full_path.exists():
                        full_path.unlink()
                        result.files_deleted += 1
                        logger.debug("file_deleted", path=file_snap.path)

            except Exception as e:
                result.errors.append(f"{file_snap.path}: {e}")
                logger.error(
                    "rollback_file_error",
                    path=file_snap.path,
                    error=str(e),
                )

        # Mark as rolled back
        snapshot.rolled_back = True
        snapshot.rolled_back_at = datetime.now(UTC)
        self._persist_snapshot(snapshot)

        result.success = len(result.errors) == 0

        logger.info(
            "rollback_complete",
            snapshot_id=snapshot_id,
            success=result.success,
            restored=result.files_restored,
            deleted=result.files_deleted,
            errors=len(result.errors),
        )

        return result

    def list_snapshots(
        self,
        module_name: str | None = None,
        include_rolled_back: bool = False,
    ) -> list[Snapshot]:
        """
        List available snapshots.

        Args:
            module_name: Filter by module name
            include_rolled_back: Include already rolled back snapshots

        Returns:
            List of Snapshot objects
        """
        snapshots = list(self._snapshots.values())

        # Filter by module
        if module_name:
            snapshots = [s for s in snapshots if s.module_name == module_name]

        # Filter out rolled back
        if not include_rolled_back:
            snapshots = [s for s in snapshots if not s.rolled_back]

        # Sort by creation time (newest first)
        snapshots.sort(key=lambda s: s.created_at, reverse=True)

        return snapshots

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """
        Get a specific snapshot by ID.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot or None
        """
        return self._snapshots.get(snapshot_id)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.

        Args:
            snapshot_id: Snapshot ID to delete

        Returns:
            True if deleted, False if not found
        """
        if snapshot_id not in self._snapshots:
            return False

        # Remove from memory
        del self._snapshots[snapshot_id]

        # Remove from disk
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        if snapshot_file.exists():
            snapshot_file.unlink()

        logger.info("snapshot_deleted", snapshot_id=snapshot_id)
        return True

    def _hash_content(self, content: str) -> str:
        """Generate hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _persist_snapshot(self, snapshot: Snapshot) -> None:
        """Persist snapshot to disk."""
        snapshot_file = self.snapshot_dir / f"{snapshot.snapshot_id}.json"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def _load_snapshots(self) -> None:
        """Load existing snapshots from disk."""
        for snapshot_file in self.snapshot_dir.glob("*.json"):
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)

                # Reconstruct snapshot
                snapshot = Snapshot(
                    snapshot_id=data["snapshot_id"],
                    module_name=data["module_name"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    meta_source=data.get("meta_source", ""),
                    commit_hash=data.get("commit_hash"),
                    rolled_back=data.get("rolled_back", False),
                )

                if data.get("rolled_back_at"):
                    snapshot.rolled_back_at = datetime.fromisoformat(
                        data["rolled_back_at"]
                    )

                self._snapshots[snapshot.snapshot_id] = snapshot

            except Exception as e:
                logger.warning(
                    "snapshot_load_error",
                    file=str(snapshot_file),
                    error=str(e),
                )

    def _cleanup_old_snapshots(self) -> None:
        """Remove old snapshots exceeding max limit."""
        if len(self._snapshots) <= self.max_snapshots:
            return

        # Sort by creation time
        sorted_snapshots = sorted(
            self._snapshots.values(),
            key=lambda s: s.created_at,
        )

        # Remove oldest until under limit
        to_remove = len(self._snapshots) - self.max_snapshots
        for snapshot in sorted_snapshots[:to_remove]:
            self.delete_snapshot(snapshot.snapshot_id)

        logger.info(
            "old_snapshots_cleaned",
            removed=to_remove,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


# Global hook instance
_hook: RollbackHook | None = None


def get_rollback_hook() -> RollbackHook:
    """Get or create global rollback hook."""
    global _hook
    if _hook is None:
        _hook = RollbackHook()
    return _hook


def setup_reversion(
    files: dict[str, str],
    module_name: str = "unknown",
) -> str:
    """Setup reversion using global hook."""
    return get_rollback_hook().setup_reversion(files, module_name)


def execute_rollback(snapshot_id: str) -> RollbackResult:
    """Execute rollback using global hook."""
    return get_rollback_hook().execute_rollback(snapshot_id)


def list_snapshots() -> list[Snapshot]:
    """List snapshots using global hook."""
    return get_rollback_hook().list_snapshots()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-013",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "dataclass",
        "debugging",
        "error-handling",
        "filesystem",
        "intelligence",
        "logging",
        "rest-api",
        "security",
        "serialization",
    ],
    "keywords": [
        "codegenagent",
        "count",
        "delete",
        "execute",
        "found",
        "hook",
        "not",
        "register",
    ],
    "business_value": "Provides reversion support for CodeGenAgent file emissions. Registers snapshots of generated files for potential rollback. Integrates with file_emitter.py rollback mechanism. Version: 1.0.0",
    "last_modified": "2026-01-15T23:27:30Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
