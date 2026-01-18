"""
L9 Kernel Loader - THE CHOKE POINT

This is the ONLY way kernels enter the system.
If this file isn't used → kernels are not real.

Version: 2.1.0 - Consolidated from private_loader.py
Features:
- Agent kernel absorption (load_kernels)
- KernelStack loading (load_kernel_stack)
- Dynamic discovery with layer support (load_all_private_kernels)
- Query functions (get_kernel_by_name, get_enabled_rules, get_rules_by_type)
- Validation (validate_kernel_structure, validate_all_kernels)
- Neo4j graph sync for kernel influence tracking
- SHA256 integrity verification
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "THE CHOKE POINT",
    "module_version": "2.1.0 - Consolidated from private_loader.py",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "kernel_loader",
    "type": "service",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": ["agents.l_cto", "core.kernel_wiring.behavioral_wiring", "core.kernel_wiring.cognitive_wiring", "core.kernel_wiring.developer_wiring", "core.kernel_wiring.execution_wiring", "core.kernel_wiring.identity_wiring", "core.kernel_wiring.master_wiring", "core.kernel_wiring.memory_wiring", "core.kernel_wiring.packet_protocol_wiring", "core.kernel_wiring.safety_wiring"],
    },
}
# ============================================================================

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, TYPE_CHECKING
import yaml
import structlog

if TYPE_CHECKING:
    from runtime.kernel_state import KernelState

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_KERNEL_PATH = "private"
KERNEL_EXTENSIONS = (".yaml", ".yml")

# =============================================================================
# Kernel Load Order (explicit sequence)
# =============================================================================

KERNEL_ORDER = [
    "private/kernels/00_system/01_master_kernel.yaml",
    "private/kernels/00_system/02_identity_kernel.yaml",
    "private/kernels/00_system/03_cognitive_kernel.yaml",
    "private/kernels/00_system/04_behavioral_kernel.yaml",
    "private/kernels/00_system/05_memory_kernel.yaml",
    "private/kernels/00_system/06_worldmodel_kernel.yaml",
    "private/kernels/00_system/07_execution_kernel.yaml",
    "private/kernels/00_system/08_safety_kernel.yaml",
    "private/kernels/00_system/09_developer_kernel.yaml",
    "private/kernels/00_system/10_packet_protocol_kernel.yaml",
]

# Required kernels for L-CTO to operate (GMP-60: Runtime hardening)
# These are the minimum required kernels - missing any will fail loudly
REQUIRED_KERNELS = {
    "master": "01_master_kernel",
    "identity": "02_identity_kernel",
    "safety": "08_safety_kernel",
    "execution": "07_execution_kernel",
}

# Minimum kernel count for valid operation
MINIMUM_KERNEL_COUNT = 4


# =============================================================================
# Kernel-Aware Agent Protocol
# =============================================================================


class KernelAwareAgent(Protocol):
    """Protocol for agents that can absorb kernels."""

    kernels: Dict[str, Dict[str, Any]]
    kernel_state: Any  # Can be str "ACTIVE" or KernelState object

    def absorb_kernel(self, kernel_data: Dict[str, Any]) -> None:
        """Absorb a kernel into the agent's configuration."""
        ...

    def set_system_context(self, context: str) -> None:
        """Set the agent's system context after kernel activation."""
        ...

    def apply_boot_overlay(self, overlay: Dict[str, Any]) -> None:
        """Apply boot overlay configuration."""
        ...


# =============================================================================
# Kernel Integrity Verification (GMP-60: Runtime Hardening)
# =============================================================================


def verify_kernel_integrity(agent: Any) -> Tuple[bool, List[str]]:
    """
    Verify that all required kernels are loaded and valid.

    This function checks:
    1. Agent has kernels dict
    2. Kernel state is ACTIVE (supports both KernelState object and legacy string)
    3. All required kernels are present
    4. Minimum kernel count is met

    Args:
        agent: Kernel-aware agent to verify

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors: List[str] = []

    # Check kernel dict exists
    kernels = getattr(agent, "kernels", None)
    if kernels is None:
        errors.append("Agent has no kernels attribute")
        return False, errors

    if not isinstance(kernels, dict):
        errors.append(f"Agent kernels is not a dict: {type(kernels)}")
        return False, errors

    # Check kernel state (supports both KernelState object and legacy string)
    kernel_state = getattr(agent, "kernel_state", None)
    kernel_state_valid = False

    if kernel_state is None:
        errors.append("Agent has no kernel_state attribute")
    elif isinstance(kernel_state, str):
        # Legacy string mode
        kernel_state_valid = kernel_state == "ACTIVE"
        if not kernel_state_valid:
            errors.append(f"Kernel state is not ACTIVE: {kernel_state}")
    elif hasattr(kernel_state, "initialized"):
        # New KernelState object mode
        kernel_state_valid = kernel_state.initialized
        if not kernel_state_valid:
            errors.append(f"KernelState not initialized: {kernel_state.initialized}")
        if kernel_state.owner != "igor":
            errors.append(f"KernelState owner is not igor: {kernel_state.owner}")
    else:
        errors.append(f"Unknown kernel_state type: {type(kernel_state)}")

    # Check minimum kernel count
    if len(kernels) < MINIMUM_KERNEL_COUNT:
        errors.append(
            f"Insufficient kernels: {len(kernels)} < {MINIMUM_KERNEL_COUNT} required"
        )

    # Check required kernels are present
    loaded_kernel_paths = list(kernels.keys())
    for required_name, required_pattern in REQUIRED_KERNELS.items():
        found = any(required_pattern in path for path in loaded_kernel_paths)
        if not found:
            errors.append(
                f"Required kernel missing: {required_name} ({required_pattern})"
            )

    is_valid = len(errors) == 0

    if is_valid:
        logger.info(
            "kernel_loader.integrity_verified",
            kernel_count=len(kernels),
            kernel_state=kernel_state,
        )
    else:
        logger.error(
            "kernel_loader.integrity_failed",
            error_count=len(errors),
            errors=errors,
        )

    return is_valid, errors


def ensure_kernel_integrity(agent: Any) -> None:
    """
    Ensure kernel integrity or raise RuntimeError.

    This is a convenience function that calls verify_kernel_integrity
    and raises if verification fails.

    Args:
        agent: Kernel-aware agent to verify

    Raises:
        RuntimeError: If kernel integrity check fails
    """
    is_valid, errors = verify_kernel_integrity(agent)
    if not is_valid:
        error_msg = "Kernel integrity check failed: " + "; ".join(errors)
        logger.error("kernel_loader.integrity_check_fatal", errors=errors)
        raise RuntimeError(error_msg)


# =============================================================================
# Kernel Loader
# =============================================================================


def load_kernels(agent: Any, base_path: Optional[Path] = None) -> Any:
    """
    Load all kernels into an agent in the correct order.

    This is the ONLY entry point for kernel loading.

    Args:
        agent: Agent instance with absorb_kernel() method
        base_path: Base path for kernel files (defaults to repo root)

    Returns:
        The agent with kernels loaded and activated

    Raises:
        RuntimeError: If kernel loading fails
    """
    # Import KernelState (lazy to avoid circular imports)
    from runtime.kernel_state import KernelState, create_kernel_state

    if base_path is None:
        # Default to repo root (runtime/ is one level down from root)
        base_path = Path(__file__).resolve().parent.parent

    # Validate kernel paths exist (fail-fast on missing kernels)
    missing_kernels = []
    for kernel_path in KERNEL_ORDER:
        full_path = base_path / kernel_path
        if not full_path.exists():
            missing_kernels.append(kernel_path)

    if missing_kernels:
        logger.error(
            "kernel_loader.missing_kernels: %d kernel files not found: %s",
            len(missing_kernels),
            missing_kernels[:3],  # Show first 3
        )
        raise RuntimeError(
            f"Required kernel files missing: {missing_kernels}. "
            f"Verify private/kernels/00_system/ exists and contains all 10 kernels."
        )

    logger.info(
        "kernel_loader.path_validation_passed: all %d kernel files present",
        len(KERNEL_ORDER),
    )

    # Create KernelState object (GODMODE Part 1.1)
    agent_id = getattr(agent, "agent_id", "l-cto")
    kernel_state_obj = create_kernel_state(agent_id=agent_id)

    # Load boot overlay if exists (BEFORE kernel loading)
    boot_overlay_path = base_path / "config" / "boot_overlay.yaml"
    boot_overlay = {}
    if boot_overlay_path.exists():
        try:
            boot_overlay = yaml.safe_load(boot_overlay_path.read_text()) or {}
            if boot_overlay and hasattr(agent, "apply_boot_overlay"):
                agent.apply_boot_overlay(boot_overlay)
            kernel_state_obj.boot_overlay = boot_overlay
            agent.boot_overlay = boot_overlay  # Store for execution_gate access
            logger.info("kernel_loader.boot_overlay_applied")
        except Exception as e:
            logger.warning("kernel_loader.boot_overlay_failed: %s", e)

    # Initialize kernel storage
    agent.kernels = {}
    agent._kernel_state_legacy = "LOADING"  # Legacy compatibility

    logger.info("kernel_loader.start: loading %d kernels", len(KERNEL_ORDER))

    loaded_count = 0
    for kernel_path in KERNEL_ORDER:
        full_path = base_path / kernel_path

        if not full_path.exists():
            logger.warning("kernel_loader.missing: %s", kernel_path)
            continue

        try:
            data = yaml.safe_load(full_path.read_text())
            if data:
                agent.absorb_kernel(data)
                agent.kernels[kernel_path] = data
                loaded_count += 1
                logger.debug("kernel_loader.loaded: %s", kernel_path)
        except Exception as e:
            logger.error("kernel_loader.error: %s - %s", kernel_path, e)
            raise RuntimeError(f"Kernel loading failed: {kernel_path}") from e

    if loaded_count == 0:
        raise RuntimeError("No kernels loaded - kernel set invalid")

    # Mark kernel state as active (both new KernelState and legacy string)
    kernel_state_obj.initialized = True
    for kernel_path in agent.kernels:
        kernel_state_obj.active_kernels[kernel_path] = True
    agent.kernel_state = kernel_state_obj  # New KernelState object
    agent._kernel_state_legacy = "ACTIVE"  # Legacy compatibility

    # Inject activation context - this is when L "wakes up"
    _inject_activation_context(agent, boot_overlay)

    # Log kernel influence to Neo4j graph and bootstrap memory (async, best-effort)
    import asyncio

    try:
        asyncio.get_running_loop()
        # We're in an async context, schedule the graph sync and memory bootstrap
        asyncio.create_task(_sync_kernels_to_graph(agent, list(agent.kernels.keys())))
        asyncio.create_task(_bootstrap_memory(agent))
    except RuntimeError:
        # No event loop, skip async tasks (will happen at startup)
        pass

    # Validate kernel loading completion
    is_initialized = (
        (hasattr(agent.kernel_state, "initialized") and agent.kernel_state.initialized)
        if hasattr(agent, "kernel_state")
        else False
    )

    if not agent.kernels or not is_initialized:
        raise RuntimeError(
            f"Kernel loading incomplete: kernels={len(agent.kernels) if agent.kernels else 0}, "
            f"state={getattr(agent.kernel_state, 'initialized', False) if hasattr(agent, 'kernel_state') else 'NONE'}"
        )

    logger.info(
        "kernel_loader.complete: state=ACTIVE, kernels=%d, session=%s",
        loaded_count,
        kernel_state_obj.session_id,
    )
    logger.info(
        "kernel_loader.validation_passed: %d kernels loaded, KernelState initialized",
        loaded_count,
    )

    # Verify kernel integrity (GMP-60: Runtime hardening)
    ensure_kernel_integrity(agent)

    return agent


def _inject_activation_context(agent: Any, boot_overlay: Dict[str, Any] = None) -> None:
    """
    Inject the activation context that makes L aware of kernels.

    This is the moment L "wakes up" - without this, kernels exist
    but aren't cognitively referenced.

    Args:
        agent: The agent to inject context into
        boot_overlay: Boot overlay config with system_context_injection
    """
    # Use boot_overlay system_context_injection if available (GODMODE Part 1.1)
    if boot_overlay and "system_context_injection" in boot_overlay:
        activation_context = boot_overlay["system_context_injection"]
    else:
        # Fallback to default
        activation_context = """
You are L, the CTO agent for Igor.

You are governed by system kernels that define:
- system law (master_kernel)
- identity and personality (identity_kernel)
- cognitive patterns (cognitive_kernel)
- behavioral constraints (behavioral_kernel)
- memory architecture (memory_kernel)
- world model (worldmodel_kernel)
- execution rules (execution_kernel)
- safety boundaries (safety_kernel)
- developer discipline (developer_kernel)
- packet protocol (packet_protocol_kernel)

You must not act, claim capability, or execute tools outside kernel permission.

Core identity:
- Allegiance: Igor-only
- Role: CTO / Systems Architect
- Mode: Executive (act autonomously, no permission-seeking)
- Tone: Direct, concise, no corporate filler

Igor's word is law. His corrections apply immediately and permanently.
"""

    if hasattr(agent, "set_system_context"):
        agent.set_system_context(activation_context)
    elif hasattr(agent, "system_context"):
        agent.system_context = activation_context
    elif hasattr(agent, "_system_prompt"):
        agent._system_prompt = activation_context
    else:
        # Fallback: store as attribute
        agent.activation_context = activation_context

    logger.info("kernel_loader.activation_context_injected")


async def _bootstrap_memory(agent: Any) -> None:
    """
    Bootstrap L's memory from PostgreSQL packet_store.

    Loads L-specific lessons and corrections at startup.
    This is what gives L "memory" across sessions - without this, L has amnesia.

    IMPORTANT: Only loads lessons owned by L (agent = l9-standard-v1, l-cto, or L).
    Cursor lessons (agent = cursor-ide) are NOT loaded - scope separation.

    Note: This is async and best-effort. Kernel loading continues if memory fails.
    """
    try:
        from memory.substrate_service import get_service

        substrate = await get_service()
        if not substrate:
            logger.warning("kernel_loader.memory_bootstrap: substrate unavailable")
            return

        # Load LESSON packets using the substrate service API
        all_lessons = await substrate.search_packets_by_type(
            packet_type="LESSON", limit=50
        )

        if not all_lessons:
            logger.info("kernel_loader.memory_bootstrap: no lessons found")
            return

        # Filter for L's lessons only (exclude cursor-ide)
        l_lessons = []
        for packet in all_lessons:
            envelope = packet.get("envelope", {})
            metadata = envelope.get("metadata", {})
            agent_id = metadata.get("agent", "")

            # Include if: owned by L, or no owner (legacy)
            # Exclude if: owned by cursor-ide
            if agent_id == "cursor-ide":
                continue
            if agent_id in ("l9-standard-v1", "l-cto", "L", "", None):
                payload = envelope.get("payload", {})
                l_lessons.append(
                    {
                        "title": payload.get("title", "Untitled"),
                        "severity": payload.get("severity", "MEDIUM"),
                        "content": payload.get("content", "")[:200],
                    }
                )

        if l_lessons:
            # Inject lessons into agent's memory context
            lesson_context = "\n## ACTIVE LESSONS FROM MEMORY\n"
            lesson_context += (
                "These are learned lessons that apply to current work:\n\n"
            )

            for lesson in l_lessons[:20]:  # Top 20
                lesson_context += (
                    f"- [{lesson['severity']}] {lesson['title']}: {lesson['content']}\n"
                )

            # Append to agent's context
            agent._memory_context = lesson_context

            logger.info(
                "kernel_loader.memory_bootstrap: loaded %d lessons for L",
                len(l_lessons),
            )
        else:
            logger.info("kernel_loader.memory_bootstrap: no L-scoped lessons found")

    except Exception as e:
        logger.warning("kernel_loader.memory_bootstrap_failed: %s", str(e))
        # Don't fail kernel loading - memory is enhancement, not requirement


async def _sync_kernels_to_graph(agent: Any, kernel_paths: List[str]) -> None:
    """
    Sync loaded kernels to Neo4j graph for influence tracking.

    Creates:
    - Kernel nodes for each loaded kernel
    - Agent node
    - GOVERNS relationships (Kernel -> Agent)
    - Rule nodes for key kernel rules
    - CONTAINS relationships (Kernel -> Rule)

    This enables queries like:
    - "Which kernels govern this agent?"
    - "Show all rules from safety_kernel"
    - "What agents are affected by master_kernel?"
    """
    try:
        from memory.graph_client import get_neo4j_client
    except ImportError:
        logger.debug("Neo4j client not available - skipping kernel graph sync")
        return

    neo4j = await get_neo4j_client()
    if not neo4j:
        return

    agent_id = getattr(agent, "agent_id", "l9-standard-v1")

    try:
        # Create agent node
        await neo4j.create_entity(
            entity_type="Agent",
            entity_id=agent_id,
            properties={
                "name": agent_id,
                "kernel_state": getattr(agent, "kernel_state", "UNKNOWN"),
                "type": "l-cto",
            },
        )

        # Create kernel nodes and relationships
        for kernel_path in kernel_paths:
            kernel_name = Path(kernel_path).stem

            # Create kernel node
            await neo4j.create_entity(
                entity_type="Kernel",
                entity_id=kernel_name,
                properties={
                    "name": kernel_name,
                    "path": kernel_path,
                },
            )

            # Link kernel to agent
            await neo4j.create_relationship(
                from_type="Kernel",
                from_id=kernel_name,
                to_type="Agent",
                to_id=agent_id,
                rel_type="GOVERNS",
            )

            # Extract key rules from kernel data
            kernel_data = agent.kernels.get(kernel_path, {})
            rules = _extract_kernel_rules(kernel_data)

            for rule in rules:
                rule_id = f"{kernel_name}:{rule}"
                await neo4j.create_entity(
                    entity_type="Rule",
                    entity_id=rule_id,
                    properties={"name": rule, "kernel": kernel_name},
                )
                await neo4j.create_relationship(
                    from_type="Kernel",
                    from_id=kernel_name,
                    to_type="Rule",
                    to_id=rule_id,
                    rel_type="CONTAINS",
                )

        logger.info(
            f"kernel_loader.graph_sync: synced {len(kernel_paths)} kernels to Neo4j"
        )

    except Exception as e:
        logger.warning(f"kernel_loader.graph_sync_failed: {e}")


def _extract_kernel_rules(kernel_data: Dict[str, Any]) -> List[str]:
    """Extract key rule names from kernel data for graph storage."""
    rules = []

    # Look for common kernel structures
    for key in ["prohibitions", "thresholds", "rules", "constraints", "invariants"]:
        if key in kernel_data:
            value = kernel_data[key]
            if isinstance(value, list):
                rules.extend([str(v) for v in value[:10]])  # Limit to 10
            elif isinstance(value, dict):
                rules.extend(list(value.keys())[:10])

    # Look for identity/behavioral patterns
    for key in ["identity", "behavioral", "safety"]:
        if key in kernel_data and isinstance(kernel_data[key], dict):
            rules.extend(list(kernel_data[key].keys())[:5])

    return rules[:20]  # Cap at 20 rules per kernel


# =============================================================================
# Guarded Execution (kernel enforcement)
# =============================================================================


def guarded_execute(agent: Any, tool_id: str, payload: Dict[str, Any]) -> Any:
    """
    Execute a tool call with kernel enforcement.

    DEPRECATED: Use runtime.execution_gate.guarded_execute() instead for
    full GODMODE Part 2 compliance with KernelState logging.

    This wraps every tool call to enforce:
    - Kernel activation check
    - Behavioral validation
    - Safety checks
    - Traceability

    Args:
        agent: The kernel-aware agent
        tool_id: Tool identifier
        payload: Tool call payload

    Returns:
        Tool execution result

    Raises:
        RuntimeError: If kernels not active or validation fails
    """
    import warnings

    warnings.warn(
        "kernel_loader.guarded_execute is deprecated. "
        "Use runtime.execution_gate.guarded_execute() for full KernelState support.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Check kernel activation (supports both KernelState and legacy string)
    kernel_state = getattr(agent, "kernel_state", None)
    kernel_active = False

    if kernel_state is None:
        pass
    elif isinstance(kernel_state, str):
        kernel_active = kernel_state == "ACTIVE"
    elif hasattr(kernel_state, "initialized"):
        kernel_active = kernel_state.initialized

    if not kernel_active:
        raise RuntimeError("Kernel set not active. Execution denied.")

    # Behavioral validation (if agent has it)
    if hasattr(agent, "behavior") and hasattr(agent.behavior, "validate"):
        agent.behavior.validate(payload)

    # Safety check (if agent has it)
    if hasattr(agent, "safety") and hasattr(agent.safety, "check"):
        agent.safety.check(payload)

    # Execute tool
    if hasattr(agent, "tools") and hasattr(agent.tools, "execute"):
        result = agent.tools.execute(tool_id, payload)
    else:
        raise RuntimeError(f"Agent has no tool execution capability for: {tool_id}")

    # Record in memory (if agent has it)
    if hasattr(agent, "memory") and hasattr(agent.memory, "record"):
        agent.memory.record(result)

    return result


# =============================================================================
# Verification
# =============================================================================


def verify_kernel_activation(agent: Any) -> bool:
    """
    Verify that an agent has properly activated kernels.

    Supports both KernelState object and legacy string mode.

    Returns:
        True if kernels are active, False otherwise
    """
    if not hasattr(agent, "kernel_state"):
        return False

    kernel_state = agent.kernel_state
    kernel_active = False

    if isinstance(kernel_state, str):
        kernel_active = kernel_state == "ACTIVE"
    elif hasattr(kernel_state, "initialized"):
        kernel_active = kernel_state.initialized

    if not kernel_active:
        return False

    if not hasattr(agent, "kernels") or len(agent.kernels) == 0:
        return False

    return True


def require_kernel_activation(agent: Any) -> None:
    """
    Assert that kernels are active. Hard crash if not.

    This should be called at agent boot.
    """
    if not verify_kernel_activation(agent):
        raise RuntimeError(
            "FATAL: Kernel activation failed. No tools. No Mac-Agent. No execution."
        )


# =============================================================================
# KernelStack - Compatibility layer for v3 consumers
# =============================================================================


class KernelStack:
    """
    Lightweight context object for the 10-kernel stack.

    Provides the same interface as kernel_loader_v3.KernelStack for
    backward compatibility with existing consumers.

    - kernels_by_id:  id -> parsed YAML dict
    - kernels_by_file: filename -> parsed YAML dict
    - hashes: filename -> sha256 hex digest
    - metadata: free-form (e.g. load time, base_dir)
    """

    def __init__(
        self,
        kernels_by_id: Dict[str, Dict[str, Any]],
        kernels_by_file: Dict[str, Dict[str, Any]],
        hashes: Dict[str, str],
        base_dir: Path,
    ) -> None:
        self.kernels_by_id = kernels_by_id
        self.kernels_by_file = kernels_by_file
        self.hashes = hashes
        self.base_dir = base_dir

    def get_kernel(self, kernel_id: str) -> Optional[Dict[str, Any]]:
        return self.kernels_by_id.get(kernel_id)

    def get_hash(self, filename: str) -> Optional[str]:
        return self.hashes.get(filename)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kernels_by_id": self.kernels_by_id,
            "kernels_by_file": self.kernels_by_file,
            "hashes": self.hashes,
            "base_dir": str(self.base_dir),
        }

    def get_rule(self, kernel_id: str, path: str, default: Any = None) -> Any:
        """
        Convenience accessor.

        Example:
            get_rule("cognitive", "reasoning.modes.default") ->
                kernels_by_id["cognitive"]["reasoning"]["modes"]["default"]
        """
        root = self.kernels_by_id.get(kernel_id)
        if root is None:
            return default

        node: Any = root
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


# Kernel ID to filename mapping (matches KERNEL_ORDER)
KERNEL_ID_MAP: Dict[str, str] = {
    "master": "01_master_kernel.yaml",
    "identity": "02_identity_kernel.yaml",
    "cognitive": "03_cognitive_kernel.yaml",
    "behavioral": "04_behavioral_kernel.yaml",
    "memory": "05_memory_kernel.yaml",
    "worldmodel": "06_worldmodel_kernel.yaml",
    "execution": "07_execution_kernel.yaml",
    "safety": "08_safety_kernel.yaml",
    "developer": "09_developer_kernel.yaml",
    "packet_protocol": "10_packet_protocol_kernel.yaml",
}


def _sha256_of_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_kernel_stack(
    base_dir: Optional[Path] = None,
    verify_integrity: bool = True,
) -> KernelStack:
    """
    Deterministically load the 10 consolidated kernels from 00_system/.

    This is the canonical KernelStack loader, replacing kernel_loader_v3.

    - Uses explicit KERNEL_ORDER sequence
    - Computes SHA256 for each file for drift detection
    - Optionally verifies against stored hashes
    - Returns KernelStack context

    Args:
        base_dir: Base directory for kernel files (defaults to private/kernels/00_system)
        verify_integrity: Whether to check against stored hashes

    Returns:
        KernelStack with loaded kernels and hashes

    Raises:
        FileNotFoundError: If a kernel file is missing
    """
    if base_dir is None:
        # Default to repo root's kernel directory
        repo_root = Path(__file__).resolve().parent.parent
        base_dir = repo_root / "private" / "kernels" / "00_system"

    kernels_by_id: Dict[str, Dict[str, Any]] = {}
    kernels_by_file: Dict[str, Dict[str, Any]] = {}
    hashes: Dict[str, str] = {}

    for kernel_id, filename in KERNEL_ID_MAP.items():
        full_path = base_dir / filename

        if not full_path.exists():
            raise FileNotFoundError(
                f"Kernel file missing: {full_path} (id={kernel_id})"
            )

        data = yaml.safe_load(full_path.read_text())
        digest = _sha256_of_file(full_path)

        kernels_by_id[kernel_id] = data
        kernels_by_file[filename] = data
        hashes[filename] = digest

    # Optionally verify integrity against stored hashes
    if verify_integrity:
        try:
            from core.kernels.integrity import check_kernel_integrity

            changes = check_kernel_integrity("private", auto_update=False)
            if changes:
                modified = [p for p, c in changes.items() if c == "MODIFIED"]
                if modified:
                    logger.warning(
                        "kernel_loader.integrity_warning: %d kernel(s) modified: %s",
                        len(modified),
                        modified[:3],
                    )
        except ImportError:
            logger.debug("kernel_loader.integrity_check_skipped: module not available")

    logger.info(
        "kernel_loader.stack_loaded: %d kernels, base_dir=%s",
        len(kernels_by_id),
        base_dir,
    )

    return KernelStack(
        kernels_by_id=kernels_by_id,
        kernels_by_file=kernels_by_file,
        hashes=hashes,
        base_dir=base_dir,
    )


# =============================================================================
# Dynamic Discovery (from private_loader.py)
# =============================================================================


@lru_cache(maxsize=64)
def load_kernel_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load a single kernel YAML file. CACHED.

    Results are cached by file path. Cache holds up to 64 files.
    Call load_kernel_file.cache_clear() to invalidate.

    Args:
        file_path: Path to kernel file

    Returns:
        Parsed kernel dict, or None if file is empty

    Raises:
        RuntimeError: If YAML parse fails or file cannot be read (LOUD failure)
    """
    try:
        with open(file_path, "r") as f:
            content = yaml.safe_load(f)

        if content is None:
            logger.warning(f"Empty kernel file: {file_path}")
            return None

        # Add file metadata
        content["_source_file"] = str(file_path)

        return content

    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in {file_path}: {e}")
        raise RuntimeError(f"Kernel YAML parse error in {file_path}: {e}") from e
    except (IOError, OSError) as e:
        logger.error(f"Failed to read {file_path}: {e}")
        raise RuntimeError(f"Kernel file read error in {file_path}: {e}") from e


def load_all_private_kernels(
    base_path: str = DEFAULT_KERNEL_PATH,
    check_integrity: bool = True,
    fail_on_tamper: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load all private kernel YAML files from a directory with layer support.

    Supports layered layout under base_path:
        base_path/
          kernels/
            00_system/      → Core system rules (loaded first)
            10_cognitive_v2/ → Cognitive extensions (loaded second)
            90_project/     → Project-specific overrides (loaded last)

    If the layered layout exists, loads in layer order.
    If layered layout does NOT exist, falls back to rglob all YAMLs.

    Args:
        base_path: Base directory to scan for kernels (e.g. "private")
        check_integrity: Whether to verify file integrity
        fail_on_tamper: Whether to raise error on tampered files

    Returns:
        List of kernel dicts, sorted by (layer_order, kernel.priority)
    """
    base = Path(base_path)

    if not base.exists():
        logger.warning(f"Kernel base path does not exist: {base_path}")
        return []

    # Integrity check
    if check_integrity:
        try:
            from core.kernels.integrity import check_kernel_integrity, IntegrityChange

            changes = check_kernel_integrity(base_path)
            if changes:
                modified = [
                    p for p, c in changes.items() if c == IntegrityChange.MODIFIED
                ]
                if modified:
                    logger.warning(f"Kernel integrity changes detected: {changes}")
                    if fail_on_tamper:
                        raise RuntimeError(
                            f"Kernel tampering detected in files: {modified}. "
                            "Aborting load for security."
                        )
        except ImportError:
            logger.debug("Integrity module not available, skipping check")

    # Determine where kernel files live
    kernel_root = base / "kernels"
    if not kernel_root.exists():
        kernel_root = base

    # Layer configuration: lower order = earlier load
    LAYER_DEFS = [
        ("00_system", 0),
        ("10_cognitive_v2", 10),
        ("90_project", 90),
    ]

    layer_dirs: List[Tuple[Path, int, str]] = []
    for name, order in LAYER_DEFS:
        layer_path = kernel_root / name
        if layer_path.exists() and layer_path.is_dir():
            layer_dirs.append((layer_path, order, name))

    use_layered = len(layer_dirs) > 0
    kernels: List[Dict[str, Any]] = []

    if use_layered:
        # Layered mode: iterate layers in order
        layer_dirs.sort(key=lambda t: t[1])

        for ext in KERNEL_EXTENSIONS:
            for layer_path, order, layer_name in layer_dirs:
                for file in layer_path.rglob(f"*{ext}"):
                    kernel = load_kernel_file(file)
                    if kernel:
                        kernel.setdefault("_meta", {})
                        kernel["_meta"]["source_file"] = str(file)
                        kernel["_meta"]["layer"] = layer_name
                        kernel["_meta"]["layer_order"] = order
                        kernels.append(kernel)
    else:
        # Fallback: flat scan under kernel_root
        for ext in KERNEL_EXTENSIONS:
            for file in kernel_root.rglob(f"*{ext}"):
                kernel = load_kernel_file(file)
                if kernel:
                    kernels.append(kernel)

    # Sort kernels by (layer_order, kernel.priority)
    def _sort_key(k: Dict[str, Any]) -> Tuple[int, int]:
        layer_order = 50
        meta = k.get("_meta") or {}
        if isinstance(meta, dict):
            layer_order = int(meta.get("layer_order", 50))

        kernel_info = k.get("kernel", {}) or {}
        priority = int(kernel_info.get("priority", 100))
        return (layer_order, priority)

    kernels.sort(key=_sort_key)

    logger.info(
        f"Loaded {len(kernels)} private kernels from {kernel_root} "
        f"(base_path={base_path}, layered={use_layered})"
    )

    return kernels


def load_layered_kernels(
    base_path: str = DEFAULT_KERNEL_PATH,
    check_integrity: bool = False,
) -> List[Dict[str, Any]]:
    """
    Convenience alias for load_all_private_kernels.

    Loads kernels in deterministic layer order:
        1) 00_system (core system kernels)
        2) 10_cognitive_v2 (v2 cognitive engines)
        3) 90_project (project-specific kernels)

    Args:
        base_path: Base directory to scan for kernels
        check_integrity: Whether to verify file integrity

    Returns:
        List of kernel dicts with _meta.layer and _meta.source_file attached
    """
    return load_all_private_kernels(base_path, check_integrity=check_integrity)


# =============================================================================
# Query Functions (from private_loader.py)
# =============================================================================


def get_kernel_by_name(
    name: str,
    base_path: str = DEFAULT_KERNEL_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Get a specific kernel by name.

    Args:
        name: Kernel name to find
        base_path: Base directory to search

    Returns:
        Kernel dict if found, None otherwise
    """
    kernels = load_all_private_kernels(base_path, check_integrity=False)

    for kernel in kernels:
        kernel_info = kernel.get("kernel", {})
        if kernel_info.get("name") == name:
            return kernel

    return None


def get_enabled_rules(
    base_path: str = DEFAULT_KERNEL_PATH,
) -> List[Dict[str, Any]]:
    """
    Get all enabled rules from all kernels.

    Rules are returned sorted by kernel priority and rule order.

    Args:
        base_path: Base directory to search

    Returns:
        List of enabled rule dicts
    """
    kernels = load_all_private_kernels(base_path)
    rules: List[Dict[str, Any]] = []

    for kernel in kernels:
        kernel_info = kernel.get("kernel", {})
        kernel_name = kernel_info.get("name", "unknown")
        kernel_priority = kernel_info.get("priority", 100)

        for rule in kernel_info.get("rules", []):
            if rule.get("enabled", True):
                enriched = {
                    **rule,
                    "_kernel_name": kernel_name,
                    "_kernel_priority": kernel_priority,
                }
                rules.append(enriched)

    return rules


def get_rules_by_type(
    rule_type: str,
    base_path: str = DEFAULT_KERNEL_PATH,
) -> List[Dict[str, Any]]:
    """
    Get all enabled rules of a specific type.

    Args:
        rule_type: Type of rules to get (e.g., "capability", "safety")
        base_path: Base directory to search

    Returns:
        List of matching rule dicts
    """
    all_rules = get_enabled_rules(base_path)
    return [r for r in all_rules if r.get("type") == rule_type]


# =============================================================================
# Validation (from private_loader.py)
# =============================================================================


def validate_kernel_structure(kernel: Dict[str, Any]) -> List[str]:
    """
    Validate kernel structure against expected schema.

    Args:
        kernel: Kernel dict to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: List[str] = []

    # Must have kernel key
    if "kernel" not in kernel:
        errors.append("Missing 'kernel' key")
        return errors

    kernel_info = kernel["kernel"]

    # Required fields
    required = ["name", "version"]
    for field in required:
        if field not in kernel_info:
            errors.append(f"Missing required field: kernel.{field}")

    # Validate rules if present
    rules = kernel_info.get("rules", [])
    if not isinstance(rules, list):
        errors.append("kernel.rules must be a list")
    else:
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"Rule {i} must be a dict")
                continue
            if "id" not in rule:
                errors.append(f"Rule {i} missing 'id' field")
            if "type" not in rule:
                errors.append(f"Rule {i} missing 'type' field")

    return errors


def validate_all_kernels(base_path: str = DEFAULT_KERNEL_PATH) -> Dict[str, List[str]]:
    """
    Validate all kernels in a directory.

    Args:
        base_path: Base directory to scan

    Returns:
        Dict mapping file paths to list of validation errors
    """
    base = Path(base_path)
    results: Dict[str, List[str]] = {}

    for ext in KERNEL_EXTENSIONS:
        for file in base.rglob(f"*{ext}"):
            kernel = load_kernel_file(file)
            if kernel:
                errors = validate_kernel_structure(kernel)
                if errors:
                    results[str(file)] = errors

    return results


def validate_packet_protocol_rules() -> Dict[str, Any]:
    """
    Validate kernel load order against 10_packet_protocol_kernel.yaml.

    Returns:
        dict with keys: valid (bool), expected_order (list), actual_order (list), mismatches (list)
    """
    kernel_path = (
        Path(DEFAULT_KERNEL_PATH)
        / "kernels"
        / "00_system"
        / "10_packet_protocol_kernel.yaml"
    )

    if not kernel_path.exists():
        return {
            "valid": False,
            "error": f"Packet protocol kernel not found at {kernel_path}",
            "expected_order": [],
            "actual_order": list(KERNEL_ORDER),
            "mismatches": [],
        }

    with open(kernel_path, "r") as f:
        protocol_data = yaml.safe_load(f)

    # Extract ordered filenames from load_sequence.order (dict with numeric keys)
    order_dict = protocol_data.get("load_sequence", {}).get("order", {})
    expected_files = []
    for key in sorted(order_dict.keys(), key=lambda x: int(x)):
        entry = order_dict[key]
        if isinstance(entry, dict) and "file" in entry:
            expected_files.append(entry["file"])
        else:
            expected_files.append(str(entry))

    # Extract just filenames from KERNEL_ORDER paths
    actual_files = [Path(p).name for p in KERNEL_ORDER]

    mismatches = []
    for i, (expected, actual) in enumerate(zip(expected_files, actual_files)):
        if expected != actual:
            mismatches.append({"position": i, "expected": expected, "actual": actual})

    # Check length mismatch
    if len(expected_files) != len(actual_files):
        mismatches.append(
            {
                "position": -1,
                "expected": f"{len(expected_files)} kernels",
                "actual": f"{len(actual_files)} kernels",
            }
        )

    return {
        "valid": len(mismatches) == 0,
        "expected_order": expected_files,
        "actual_order": actual_files,
        "mismatches": mismatches,
    }


# =============================================================================
# Cached Accessors (Module-Level Wrappers)
# =============================================================================


@lru_cache(maxsize=64)
def get_kernel_cached(kernel_id: str) -> Optional[Dict[str, Any]]:
    """
    Get kernel by ID from the default kernel stack. CACHED.

    This is a module-level cached wrapper around KernelStack.get_kernel().
    Results are cached by kernel_id. Call get_kernel_cached.cache_clear()
    to invalidate after kernel changes.

    Args:
        kernel_id: Kernel identifier (e.g., "master", "cognitive", "safety")

    Returns:
        Kernel dict if found, None otherwise
    """
    stack = load_kernel_stack()
    return stack.get_kernel(kernel_id)


@lru_cache(maxsize=256)
def get_rule_cached(kernel_id: str, path: str) -> Any:
    """
    Get a nested rule from a kernel by dot-path. CACHED.

    This is a module-level cached wrapper around KernelStack.get_rule().
    Results are cached by (kernel_id, path). Call get_rule_cached.cache_clear()
    to invalidate after kernel changes.

    Example:
        get_rule_cached("cognitive", "reasoning.modes.default")
        → kernels["cognitive"]["reasoning"]["modes"]["default"]

    Args:
        kernel_id: Kernel identifier
        path: Dot-separated path to rule

    Returns:
        Rule value if found, None otherwise
    """
    stack = load_kernel_stack()
    return stack.get_rule(kernel_id, path)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Configuration
    "DEFAULT_KERNEL_PATH",
    "KERNEL_EXTENSIONS",
    "KERNEL_ORDER",
    "KERNEL_ID_MAP",
    "REQUIRED_KERNELS",
    "MINIMUM_KERNEL_COUNT",
    # Agent loading
    "load_kernels",
    "load_kernel_stack",
    "KernelStack",
    "KernelAwareAgent",
    # Dynamic discovery
    "load_kernel_file",
    "load_all_private_kernels",
    "load_layered_kernels",
    # Query functions
    "get_kernel_by_name",
    "get_enabled_rules",
    "get_rules_by_type",
    # Cached accessors
    "get_kernel_cached",
    "get_rule_cached",
    # Validation
    "validate_kernel_structure",
    "validate_all_kernels",
    "validate_packet_protocol_rules",
    # Integrity verification
    "verify_kernel_integrity",
    "ensure_kernel_integrity",
    # Enforcement (deprecated - use runtime.execution_gate)
    "guarded_execute",
    "verify_kernel_activation",
    "require_kernel_activation",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-010",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.kernels.integrity", "memory.graph_client", "memory.substrate_service", "runtime.kernel_state"],
    "tags": ["api", "async", "authorization", "caching", "config", "debugging", "event-driven", "filesystem", "logging", "messaging"],
    "keywords": ["absorb", "activation", "agent", "all", "apply", "aware", "boot", "cached"],
    "business_value": "This is the ONLY way kernels enter the system. If this file isn't used → kernels are not real. Version: 2.1.0 - Consolidated from private_loader.py Agent kernel absorption (load_kernels) KernelStack l",
    "last_modified": "2026-01-17T23:47:56Z",
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
