"""
CodeGenAgent Cursor Context Sync Engine
=======================================

Bi-directional synchronization between CodeGenAgent's generation memory
and Cursor's visible prompt stack and YAML capsule context.

Full-featured sync engine with Redis integration and event triggers.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cursor Context Sync Engine",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:28:32Z",
    "updated_at": "2026-01-17T11:28:11Z",
    "layer": "intelligence",
    "domain": "error_handling",
    "module_name": "cursor_context_sync_engine",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
import structlog
import yaml

from core.decorators import must_stay_async

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================


DEFAULT_SYNC_DIR = ".cursor_sync"
CONTEXT_STACK_FILE = "cursor_context_stack.json"
MEMORY_CONTEXT_FILE = "memory_context.yaml"
CURSOR_REPLAY_FILE = "cursor_replay.json"
SYNC_DIFF_FILE = "sync_diff.patch.yaml"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class AgentState:
    """State from agent session."""

    agent_id: str
    session_id: str | None = None

    # Context
    current_module: str | None = None
    generated_files: list[str] = field(default_factory=list)
    active_meta: dict[str, Any] | None = None

    # History
    recent_operations: list[dict[str, Any]] = field(default_factory=list)

    # Timestamps
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_start: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the agent's current state, including identifiers, module context, generated files, and active metadata for synchronization purposes."""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "current_module": self.current_module,
            "generated_files": self.generated_files,
            "active_meta": self.active_meta,
            "recent_operations": self.recent_operations[-10:],  # Last 10
            "last_activity": self.last_activity.isoformat(),
            "session_start": self.session_start.isoformat()
            if self.session_start
            else None,
        }


@dataclass
class CursorStack:
    """Cursor's visible context stack."""

    # Prompt stack
    prompts: list[dict[str, Any]] = field(default_factory=list)

    # Active files
    open_files: list[str] = field(default_factory=list)

    # YAML capsules
    yaml_blocks: list[dict[str, Any]] = field(default_factory=list)

    # Session info
    cursor_session_id: str | None = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the cursor context, including prompts, open files, YAML blocks, session ID, and last update timestamp in ISO format."""
        return {
            "prompts": self.prompts,
            "open_files": self.open_files,
            "yaml_blocks": self.yaml_blocks,
            "cursor_session_id": self.cursor_session_id,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CursorStack:
        """
        Parses a dictionary to instantiate a CursorStack reflecting the current code editing context.

        Args:
            data: Dictionary containing cursor context data such as prompts, open files, YAML blocks, and session ID.

        Returns:
            A CursorStack object initialized with the provided context data.

        Raises:
            KeyError: If required keys are missing in the input dictionary.
        """
        stack = cls(
            prompts=data.get("prompts", []),
            open_files=data.get("open_files", []),
            yaml_blocks=data.get("yaml_blocks", []),
            cursor_session_id=data.get("cursor_session_id"),
        )
        if data.get("last_updated"):
            stack.last_updated = datetime.fromisoformat(data["last_updated"])
        return stack


@dataclass
class SyncPatch:
    """
    Returns a dictionary representation of the SyncPatch instance, capturing its current state for cursor context synchronization.

    Args:
        None

    Returns:
        dict: A dictionary with keys 'agent_id', 'timestamp', 'new_files', 'removed_files', and 'modified_context' representing the patch details.

    Raises:
        None
    """

    """Patch describing differences between agent and cursor state."""

    agent_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Differences
    new_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    modified_context: dict[str, Any] = field(default_factory=dict)

    # Sync actions
    actions: list[dict[str, Any]] = field(default_factory=list)
    """Returns a dictionary representation of the SyncResult, capturing success status, agent identifier, associated patch details, error messages, and files synchronized during the cursor context synchronization process."""

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the SyncPatch instance capturing its current state for cursor context synchronization, including agent ID, timestamp, and file changes.


        Returns:
            A dictionary with keys 'agent_id', 'timestamp', 'new_files', 'removed_files', and 'modified_context' representing the sync patch state.
        """
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "new_files": self.new_files,
            "removed_files": self.removed_files,
            "modified_context": self.modified_context,
            "actions": self.actions,
        }

    def to_yaml(self) -> str:
        """
        Returns a YAML-formatted string representing the current state of the SyncPatch instance for cursor context synchronization.


        Returns:
            str: YAML string of the SyncPatch's dictionary representation.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False)


@dataclass
class SyncResult:
    """Returns a dictionary representation of the SyncResult instance, including success status, agent identifier, associated patch details, errors, and number of files synchronized."""

    """Result of a sync operation."""

    success: bool
    agent_id: str
    patch: SyncPatch | None = None
    errors: list[str] = field(default_factory=list)
    files_synced: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the SyncResult instance, including success status, agent identifier, patch details, errors, and number of files synced.


        Returns:
            A dictionary with keys 'success', 'agent_id', 'patch', 'errors', and 'files_synced' representing the sync outcome and details.
        """
        return {
            "success": self.success,
            "agent_id": self.agent_id,
            "patch": self.patch.to_dict() if self.patch else None,
            "errors": self.errors,
            "files_synced": self.files_synced,
        }


# =============================================================================
# EXCEPTIONS
# =============================================================================


class CursorSyncError(Exception):
    """Exception raised during cursor sync."""

    pass


class RedisConnectionError(CursorSyncError):
    """Exception raised when Redis is unavailable."""

    pass


# =============================================================================
# CURSOR CONTEXT SYNC ENGINE
# =============================================================================


class CursorContextSyncEngine:
    """
    Bi-directional sync engine for CodeGenAgent and Cursor.

    Synchronizes generation state with Cursor's visible context.
    Supports Redis-backed session state and event triggers.
    """

    def __init__(
        self,
        repo_root: str = "/Users/ib-mac/Projects/L9",
        sync_dir: str | None = None,
        redis_client: Any | None = None,
    ):
        """
        Initialize the Cursor Context Sync Engine.

        Args:
            repo_root: Repository root path
            sync_dir: Directory for sync files
            redis_client: Optional Redis client for session state
        """
        self.repo_root = Path(repo_root)
        self.sync_dir = (
            Path(sync_dir) if sync_dir else self.repo_root / DEFAULT_SYNC_DIR
        )
        self._redis = redis_client

        # Event handlers
        self._on_emit_handlers: list[Callable] = []
        self._on_session_start_handlers: list[Callable] = []
        self._on_audit_handlers: list[Callable] = []

        # State cache
        self._agent_states: dict[str, AgentState] = {}
        self._cursor_stack: CursorStack | None = None

        # Ensure sync directory exists
        self.sync_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "cursor_sync_engine_initialized",
            repo_root=str(self.repo_root),
            sync_dir=str(self.sync_dir),
            has_redis=redis_client is not None,
        )

    @must_stay_async("callers use await")
    async def sync_cursor_context(
        self,
        agent_id: str,
        files: dict[str, str],
    ) -> SyncResult:
        """
        Synchronize generated files with Cursor context.

        Args:
            agent_id: Agent identifier
            files: Generated files (path -> content)

        Returns:
            SyncResult with sync details
        """
        result = SyncResult(
            success=False,
            agent_id=agent_id,
        )

        try:
            # Read current states
            agent_state = await self.read_agent_state(agent_id)
            cursor_stack = await self._load_cursor_stack()

            # Update agent state with new files
            agent_state.generated_files = list(files.keys())
            agent_state.last_activity = datetime.now(UTC)

            # Generate patch
            patch = self.generate_patch(agent_state, cursor_stack)
            result.patch = patch

            # Write sync output
            await self.write_sync_output(agent_id, patch)

            # Update cursor context
            cursor_stack.open_files = list(files.keys())
            cursor_stack.last_updated = datetime.now(UTC)
            await self._save_cursor_stack(cursor_stack)

            # Update memory context
            await self._update_memory_context(agent_state)

            # Cache updated state
            self._agent_states[agent_id] = agent_state
            self._cursor_stack = cursor_stack

            # Trigger handlers
            await self._trigger_emit_handlers(agent_id, files)

            result.success = True
            result.files_synced = len(files)

            logger.info(
                "cursor_sync_complete",
                agent_id=agent_id,
                files_synced=len(files),
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(
                "cursor_sync_failed",
                agent_id=agent_id,
                error=str(e),
            )

        return result

    async def read_agent_state(self, agent_id: str) -> AgentState:
        """
        Read agent state from Redis or cache.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentState for the agent
        """
        # Check cache first
        if agent_id in self._agent_states:
            return self._agent_states[agent_id]

        # Try Redis
        if self._redis:
            try:
                key = f"agent_session/{agent_id}"
                data = await self._redis.get(key)
                if data:
                    state_dict = json.loads(data)
                    state = AgentState(agent_id=agent_id)
                    state.session_id = state_dict.get("session_id")
                    state.current_module = state_dict.get("current_module")
                    state.generated_files = state_dict.get("generated_files", [])
                    state.recent_operations = state_dict.get("recent_operations", [])
                    return state
            except Exception as e:
                logger.warning("redis_read_failed", agent_id=agent_id, error=str(e))

        # Return new state
        return AgentState(agent_id=agent_id)

    def generate_patch(
        self,
        agent_state: AgentState,
        cursor_stack: CursorStack,
    ) -> SyncPatch:
        """
        Generate sync patch from state differences.

        Args:
            agent_state: Current agent state
            cursor_stack: Current cursor stack

        Returns:
            SyncPatch describing differences
        """
        patch = SyncPatch(agent_id=agent_state.agent_id)

        # Compare files
        agent_files = set(agent_state.generated_files)
        cursor_files = set(cursor_stack.open_files)

        patch.new_files = list(agent_files - cursor_files)
        patch.removed_files = list(cursor_files - agent_files)

        # Build actions
        for f in patch.new_files:
            patch.actions.append(
                {
                    "action": "open_file",
                    "path": f,
                    "source": "codegen",
                }
            )

        # Context modifications
        if agent_state.current_module:
            patch.modified_context["current_module"] = agent_state.current_module

        if agent_state.active_meta:
            patch.modified_context["active_meta"] = agent_state.active_meta.get("name")

        return patch

    @must_stay_async("callers use await")
    async def write_sync_output(
        self,
        agent_id: str,
        patch: SyncPatch,
    ) -> None:
        """
        Write sync output files.

        Args:
            agent_id: Agent identifier
            patch: Sync patch to write
        """
        # Write patch file
        patch_file = self.sync_dir / SYNC_DIFF_FILE
        async with aiofiles.open(patch_file, "w", encoding="utf-8") as f:
            await f.write(patch.to_yaml())

        # Write replay file
        replay_file = self.sync_dir / CURSOR_REPLAY_FILE
        replay_data = {
            "agent_id": agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "actions": patch.actions,
        }
        async with aiofiles.open(replay_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(replay_data, indent=2))

        logger.debug(
            "sync_output_written",
            agent_id=agent_id,
            patch_file=str(patch_file),
        )

    @must_stay_async("callers use await")
    async def _load_cursor_stack(self) -> CursorStack:
        """Load cursor context stack from file."""
        stack_file = self.sync_dir / CONTEXT_STACK_FILE

        if stack_file.exists():
            try:
                async with aiofiles.open(stack_file) as f:
                    content = await f.read()
                    return CursorStack.from_dict(json.loads(content))
            except Exception as e:
                logger.warning("cursor_stack_load_error", error=str(e))

        return CursorStack()

    @must_stay_async("callers use await")
    async def _save_cursor_stack(self, stack: CursorStack) -> None:
        """Save cursor context stack to file."""
        stack_file = self.sync_dir / CONTEXT_STACK_FILE

        async with aiofiles.open(stack_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(stack.to_dict(), indent=2))

    @must_stay_async("callers use await")
    async def _update_memory_context(self, agent_state: AgentState) -> None:
        """Update memory context YAML file."""
        memory_file = self.sync_dir / MEMORY_CONTEXT_FILE

        context = {
            "agent_id": agent_state.agent_id,
            "session_id": agent_state.session_id,
            "current_module": agent_state.current_module,
            "generated_files": agent_state.generated_files,
            "last_activity": agent_state.last_activity.isoformat(),
        }

        async with aiofiles.open(memory_file, "w", encoding="utf-8") as f:
            await f.write(yaml.dump(context, default_flow_style=False))

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def on_codegen_emit(self, handler: Callable) -> None:
        """Register handler for codegen emit events."""
        self._on_emit_handlers.append(handler)

    def on_cursor_session_start(self, handler: Callable) -> None:
        """Register handler for cursor session start."""
        self._on_session_start_handlers.append(handler)

    def on_packet_audit_loop(self, handler: Callable) -> None:
        """Register handler for packet audit loop."""
        self._on_audit_handlers.append(handler)

    async def _trigger_emit_handlers(
        self,
        agent_id: str,
        files: dict[str, str],
    ) -> None:
        """Trigger on_emit handlers."""
        for handler in self._on_emit_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(agent_id, files)
                else:
                    handler(agent_id, files)
            except Exception as e:
                logger.error("emit_handler_error", error=str(e))

    async def trigger_session_start(self, session_id: str) -> None:
        """Trigger cursor session start handlers."""
        for handler in self._on_session_start_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session_id)
                else:
                    handler(session_id)
            except Exception as e:
                logger.error("session_start_handler_error", error=str(e))

    async def trigger_audit_loop(self, packets: list[dict]) -> None:
        """Trigger packet audit loop handlers."""
        for handler in self._on_audit_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(packets)
                else:
                    handler(packets)
            except Exception as e:
                logger.error("audit_handler_error", error=str(e))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


# Global engine instance
_engine: CursorContextSyncEngine | None = None


def get_sync_engine() -> CursorContextSyncEngine:
    """Get or create global sync engine."""
    global _engine
    if _engine is None:
        _engine = CursorContextSyncEngine()
    return _engine


async def sync_cursor_context(
    agent_id: str,
    files: dict[str, str],
) -> SyncResult:
    """Sync using global engine."""
    return await get_sync_engine().sync_cursor_context(agent_id, files)


async def read_agent_state(agent_id: str) -> AgentState:
    """Read agent state using global engine."""
    return await get_sync_engine().read_agent_state(agent_id)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-016",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "cache",
        "caching",
        "config",
        "dataclass",
        "debugging",
        "engine",
        "error-handling",
        "event-driven",
        "filesystem",
    ],
    "keywords": [
        "agent",
        "audit",
        "codegen",
        "codegenagent",
        "connection",
        "cursor",
        "emit",
        "engine",
    ],
    "business_value": "Provides cursor context sync engine components including AgentState, CursorStack, SyncPatch",
    "last_modified": "2026-01-17T11:28:11Z",
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
