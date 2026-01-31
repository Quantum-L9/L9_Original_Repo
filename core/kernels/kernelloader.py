"""
L9 Kernel Loader - Two-Phase Activation
========================================

Frontier-grade kernel loading with:
- Phase 1: LOAD - Parse YAML, validate schema, compute hashes
- Phase 2: ACTIVATE - Inject context, set state, verify activation

This is the ONLY way kernels enter the system.
If this file isn't used → kernels are not real.

Version: 2.0.0
GMP: kernel_boot_frontier_phase1

Features:
- Two-phase activation (LOAD → ACTIVATE)
- Pydantic schema validation
- SHA256 integrity verification
- Structured observability spans
- Explicit failure semantics (no silent degradation)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Two-Phase Activation",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "kernelloader",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "api.server",
            "core.agents.kernel_registry",
            "tests.integration.test_kernel_hot_reload",
            "tests.unit.test_kernel_loader_activation",
            "tests.unit.test_kernel_observability",
            "tests.unit.test_lcto_bootstrap",
        ],
    },
}
# ============================================================================

import hashlib
from pathlib import Path
from typing import Any, Protocol

import structlog
import yaml

from core.kernels.schemas import (
    KernelActivationResult,
    KernelManifest,
    KernelState,
    KernelValidationResult,
    ValidationError,
)

# Optional: Observability spans (v3.4+ / GMP-KERNEL-BOOT)
try:
    from core.observability.models import (
        KernelLifecycleSpan,
        SpanKind,
        SpanStatus,
        TraceContext,
    )
    from core.observability.service import get_observability_service

    _has_observability = True
except ImportError:
    _has_observability = False

logger = structlog.get_logger(__name__)


# =============================================================================
# Observability Helpers
# =============================================================================


def _create_kernel_span(
    name: str,
    kernel_id: str,
    phase: str,
    trace_context: Any | None = None,
    **attributes: Any,
) -> Any | None:
    """Create a kernel lifecycle span if observability is available."""
    if not _has_observability:
        return None

    try:
        trace_id = trace_context.trace_id if trace_context else None
        parent_span_id = trace_context.span_id if trace_context else None

        if trace_id is None:
            # Create a new trace context
            ctx = TraceContext()
            trace_id = ctx.trace_id

        return KernelLifecycleSpan.start(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            kind=(
                SpanKind.KERNEL_LOAD if phase == "load" else SpanKind.KERNEL_ACTIVATION
            ),
            kernel_id=kernel_id,
            phase=phase,
            **attributes,
        )
    except Exception as e:
        logger.debug("kernel_loader.span_creation_failed", error=str(e))
        return None


def _finish_span(
    span: Any | None,
    status: str = "OK",
    error: str | None = None,
) -> None:
    """Finish a span if it exists."""
    if span is None or not _has_observability:
        return

    try:
        span_status = SpanStatus.OK if status == "OK" else SpanStatus.ERROR
        span.finish(status=span_status, error=error)

        # Try to emit the span
        try:
            obs_service = get_observability_service()
            if obs_service:
                obs_service.emit_span(span)
        except Exception as e:
            logger.debug(
                "kernel_loader.span_emission_failed", error=str(e)
            )  # Best-effort emission
    except Exception as e:
        logger.debug("kernel_loader.span_finish_failed", error=str(e))


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_KERNEL_PATH = "private"
KERNEL_EXTENSIONS = (".yaml", ".yml")

# Kernel Load Order (explicit sequence - MUST match 10_packet_protocol_kernel.yaml)
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

# Kernel ID to filename mapping
KERNEL_ID_MAP: dict[str, str] = {
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

# Required kernel count for valid activation
REQUIRED_KERNEL_COUNT = 10


# =============================================================================
# Kernel-Aware Agent Protocol
# =============================================================================


class KernelAwareAgent(Protocol):
    """Protocol for agents that can absorb kernels."""

    kernels: dict[str, dict[str, Any]]
    kernel_state: str

    def absorb_kernel(self, kernel_data: dict[str, Any]) -> None:
        """Absorb a kernel into the agent's configuration."""
        ...

    def set_system_context(self, context: str) -> None:
        """Set the agent's system context after kernel activation."""
        ...


# =============================================================================
# Phase 1: LOAD
# =============================================================================


def _sha256_of_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _validate_kernel_yaml(
    data: dict[str, Any], file_path: str
) -> KernelValidationResult:
    """
    Validate kernel YAML against Pydantic schema.

    Args:
        data: Parsed YAML data
        file_path: Source file path for error reporting

    Returns:
        KernelValidationResult with validation status
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Check for kernel key
    if "kernel" not in data:
        # Some kernels use different top-level structure
        # Try to infer kernel info from file name
        file_name = Path(file_path).stem
        data["kernel"] = {
            "name": file_name,
            "version": "1.0.0",
            "priority": 100,
        }
        warnings.append(
            ValidationError(
                field="kernel",
                message=f"Missing 'kernel' key, inferred from filename: {file_name}",
                severity="WARNING",
            )
        )

    try:
        manifest = KernelManifest.model_validate(data)
        kernel_type = manifest.get_kernel_type()

        return KernelValidationResult(
            valid=True,
            kernel_name=manifest.kernel.name,
            kernel_type=kernel_type,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        errors.append(
            ValidationError(
                field="schema",
                message=f"Schema validation failed: {e!s}",
                severity="ERROR",
            )
        )
        return KernelValidationResult(
            valid=False,
            kernel_name=data.get("kernel", {}).get("name"),
            errors=errors,
            warnings=warnings,
        )


def load_kernels_phase1(
    base_path: Path | None = None,
    validate_schema: bool = True,
    verify_integrity: bool = True,
    trace_context: Any | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[ValidationError]]:
    """
    Phase 1: LOAD - Parse YAML, validate schema, compute hashes.

    This phase does NOT activate kernels. It only loads and validates.

    Args:
        base_path: Base path for kernel files (defaults to repo root)
        validate_schema: Whether to validate against Pydantic schema
        verify_integrity: Whether to compute and verify file hashes
        trace_context: Optional trace context for observability spans

    Returns:
        Tuple of:
        - kernels_by_path: Dict mapping file path to parsed kernel data
        - hashes: Dict mapping file path to SHA256 hash
        - errors: List of validation errors (empty if all valid)

    Raises:
        RuntimeError: If required kernel files are missing
    """
    if base_path is None:
        # Default to repo root (core/kernels/ is two levels down from root)
        base_path = Path(__file__).resolve().parent.parent.parent

    # Create root span for Phase 1
    phase1_span = _create_kernel_span(
        name="kernel_loader.phase1",
        kernel_id="all",
        phase="load",
        trace_context=trace_context,
        kernel_count=len(KERNEL_ORDER),
    )

    logger.info(
        "kernel_loader.phase1_start",
        base_path=str(base_path),
        kernel_count=len(KERNEL_ORDER),
    )

    # Validate kernel paths exist (fail-fast on missing kernels)
    missing_kernels: list[str] = []
    for kernel_path in KERNEL_ORDER:
        full_path = base_path / kernel_path
        if not full_path.exists():
            missing_kernels.append(kernel_path)

    if missing_kernels:
        logger.error(
            "kernel_loader.phase1_missing_kernels",
            missing_count=len(missing_kernels),
            missing=missing_kernels[:3],
        )
        raise RuntimeError(
            f"Required kernel files missing: {missing_kernels}. "
            f"Verify private/kernels/00_system/ exists and contains all 10 kernels."
        )

    logger.info(
        "kernel_loader.phase1_paths_validated",
        kernel_count=len(KERNEL_ORDER),
    )

    # Load and validate each kernel
    kernels_by_path: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    all_errors: list[ValidationError] = []

    for kernel_path in KERNEL_ORDER:
        full_path = base_path / kernel_path

        try:
            # Parse YAML
            data = yaml.safe_load(full_path.read_text())
            if data is None:
                all_errors.append(
                    ValidationError(
                        field=kernel_path,
                        message="Empty kernel file",
                        severity="ERROR",
                    )
                )
                continue

            # Compute hash
            if verify_integrity:
                file_hash = _sha256_of_file(full_path)
                hashes[kernel_path] = file_hash

            # Validate schema
            if validate_schema:
                result = _validate_kernel_yaml(data, kernel_path)
                if not result.valid:
                    all_errors.extend(result.errors)
                    logger.warning(
                        "kernel_loader.phase1_validation_failed",
                        kernel_path=kernel_path,
                        errors=[e.message for e in result.errors],
                    )
                    # Continue loading even with validation errors
                    # (errors are collected, not fatal)

            # Store kernel data
            kernels_by_path[kernel_path] = data
            logger.debug(
                "kernel_loader.phase1_loaded",
                kernel_path=kernel_path,
                hash=hashes.get(kernel_path, "")[:12],
            )

        except yaml.YAMLError as e:
            all_errors.append(
                ValidationError(
                    field=kernel_path,
                    message=f"YAML parse error: {e!s}",
                    severity="ERROR",
                )
            )
            logger.error(
                "kernel_loader.phase1_yaml_error",
                kernel_path=kernel_path,
                error=str(e),
            )

        except Exception as e:
            all_errors.append(
                ValidationError(
                    field=kernel_path,
                    message=f"Load error: {e!s}",
                    severity="ERROR",
                )
            )
            logger.error(
                "kernel_loader.phase1_load_error",
                kernel_path=kernel_path,
                error=str(e),
            )

    # Verify minimum kernel count
    if len(kernels_by_path) < REQUIRED_KERNEL_COUNT:
        all_errors.append(
            ValidationError(
                field="kernel_count",
                message=f"Insufficient kernels: {len(kernels_by_path)}/{REQUIRED_KERNEL_COUNT}",
                severity="ERROR",
            )
        )

    logger.info(
        "kernel_loader.phase1_complete",
        loaded_count=len(kernels_by_path),
        hash_count=len(hashes),
        error_count=len(all_errors),
    )

    # Finish Phase 1 span
    if phase1_span:
        phase1_span.attributes["loaded_count"] = len(kernels_by_path)
        phase1_span.attributes["hash_count"] = len(hashes)
        phase1_span.attributes["error_count"] = len(all_errors)
        _finish_span(
            phase1_span,
            status="OK" if len(all_errors) == 0 else "ERROR",
            error=(
                "; ".join([e.message for e in all_errors[:3]]) if all_errors else None
            ),
        )

    return kernels_by_path, hashes, all_errors


# =============================================================================
# Phase 2: ACTIVATE
# =============================================================================


def _build_activation_context() -> str:
    """
    Build the activation context that makes L aware of kernels.

    This is the moment L "wakes up" - without this, kernels exist
    but aren't cognitively referenced.
    """
    return """
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


def activate_kernels_phase2(
    agent: Any,
    kernels_by_path: dict[str, dict[str, Any]],
    hashes: dict[str, str],
    trace_context: Any | None = None,
) -> KernelActivationResult:
    """
    Phase 2: ACTIVATE - Inject context, set state, verify activation.

    This phase activates kernels on the agent after Phase 1 loading.

    Args:
        agent: Agent instance with absorb_kernel() method
        kernels_by_path: Kernels loaded in Phase 1
        hashes: File hashes from Phase 1
        trace_context: Optional trace context for observability spans

    Returns:
        KernelActivationResult with activation status

    Raises:
        RuntimeError: If activation fails critically
    """
    # Create root span for Phase 2
    phase2_span = _create_kernel_span(
        name="kernel_loader.phase2",
        kernel_id="all",
        phase="activate",
        trace_context=trace_context,
        kernel_count=len(kernels_by_path),
        agent_id=getattr(agent, "agent_id", "unknown"),
    )

    logger.info(
        "kernel_loader.phase2_start",
        kernel_count=len(kernels_by_path),
    )

    errors: list[ValidationError] = []

    # Initialize kernel storage on agent
    agent.kernels = {}
    agent.kernel_state = KernelState.LOADING.value

    # Absorb each kernel in order
    absorbed_count = 0
    for kernel_path in KERNEL_ORDER:
        if kernel_path not in kernels_by_path:
            continue

        data = kernels_by_path[kernel_path]

        try:
            agent.absorb_kernel(data)
            agent.kernels[kernel_path] = data
            absorbed_count += 1
            logger.debug(
                "kernel_loader.phase2_absorbed",
                kernel_path=kernel_path,
            )

        except Exception as e:
            errors.append(
                ValidationError(
                    field=kernel_path,
                    message=f"Absorption failed: {e!s}",
                    severity="ERROR",
                )
            )
            logger.error(
                "kernel_loader.phase2_absorption_error",
                kernel_path=kernel_path,
                error=str(e),
            )

    # Verify minimum absorption
    if absorbed_count < REQUIRED_KERNEL_COUNT:
        agent.kernel_state = KernelState.ERROR.value
        errors.append(
            ValidationError(
                field="absorption",
                message=f"Insufficient kernels absorbed: {absorbed_count}/{REQUIRED_KERNEL_COUNT}",
                severity="ERROR",
            )
        )
        logger.error(
            "kernel_loader.phase2_insufficient_kernels",
            absorbed=absorbed_count,
            required=REQUIRED_KERNEL_COUNT,
        )

        # Finish Phase 2 span with error
        if phase2_span:
            phase2_span.attributes["absorbed_count"] = absorbed_count
            phase2_span.attributes["final_state"] = KernelState.ERROR.value
            _finish_span(
                phase2_span,
                status="ERROR",
                error=f"Insufficient kernels absorbed: {absorbed_count}/{REQUIRED_KERNEL_COUNT}",
            )

        return KernelActivationResult(
            phase="ACTIVATE",
            success=False,
            kernels_loaded=len(kernels_by_path),
            kernels_activated=absorbed_count,
            integrity_verified=len(hashes) == len(kernels_by_path),
            validation_errors=errors,
            activation_context_set=False,
            state=KernelState.ERROR,
        )

    # Transition to VALIDATING state
    agent.kernel_state = KernelState.VALIDATING.value

    # Store hashes on agent for later integrity checks
    if hasattr(agent, "kernel_hashes"):
        agent.kernel_hashes = hashes
    else:
        agent._kernel_hashes = hashes

    # Inject activation context
    activation_context = _build_activation_context()
    context_set = False

    if hasattr(agent, "set_system_context"):
        agent.set_system_context(activation_context)
        context_set = True
    elif hasattr(agent, "system_context"):
        agent.system_context = activation_context
        context_set = True
    elif hasattr(agent, "_system_prompt"):
        agent._system_prompt = activation_context
        context_set = True
    else:
        # Fallback: store as attribute
        agent.activation_context = activation_context
        context_set = True

    # Mark kernel state as ACTIVE
    agent.kernel_state = KernelState.ACTIVE.value

    logger.info(
        "kernel_loader.phase2_complete",
        absorbed_count=absorbed_count,
        context_set=context_set,
        state=agent.kernel_state,
    )

    # Finish Phase 2 span
    if phase2_span:
        phase2_span.attributes["absorbed_count"] = absorbed_count
        phase2_span.attributes["context_set"] = context_set
        phase2_span.attributes["final_state"] = agent.kernel_state
        _finish_span(phase2_span, status="OK")

    return KernelActivationResult(
        phase="ACTIVATE",
        success=True,
        kernels_loaded=len(kernels_by_path),
        kernels_activated=absorbed_count,
        integrity_verified=len(hashes) == len(kernels_by_path),
        validation_errors=errors,
        activation_context_set=context_set,
        state=KernelState.ACTIVE,
    )


# =============================================================================
# Unified Two-Phase Loader
# =============================================================================


def load_kernels(
    agent: Any,
    base_path: Path | None = None,
    validate_schema: bool = True,
    verify_integrity: bool = True,
) -> Any:
    """
    Load all kernels into an agent using two-phase activation.

    Phase 1: LOAD - Parse YAML, validate schema, compute hashes
    Phase 2: ACTIVATE - Inject context, set state, verify activation

    This is the ONLY entry point for kernel loading.

    Args:
        agent: Agent instance with absorb_kernel() method
        base_path: Base path for kernel files (defaults to repo root)
        validate_schema: Whether to validate against Pydantic schema
        verify_integrity: Whether to compute and verify file hashes

    Returns:
        The agent with kernels loaded and activated

    Raises:
        RuntimeError: If kernel loading or activation fails
    """
    logger.info("kernel_loader.two_phase_start")

    # Phase 1: LOAD
    kernels_by_path, hashes, phase1_errors = load_kernels_phase1(
        base_path=base_path,
        validate_schema=validate_schema,
        verify_integrity=verify_integrity,
    )

    # Check for fatal Phase 1 errors
    fatal_errors = [e for e in phase1_errors if e.severity == "ERROR"]
    if len(kernels_by_path) == 0 or len(fatal_errors) > 0:
        error_msg = "; ".join([e.message for e in fatal_errors[:3]])
        raise RuntimeError(f"Kernel loading failed (Phase 1): {error_msg}")

    # Phase 2: ACTIVATE
    result = activate_kernels_phase2(agent, kernels_by_path, hashes)

    if not result.success:
        error_msg = "; ".join([e.message for e in result.validation_errors[:3]])
        raise RuntimeError(f"Kernel activation failed (Phase 2): {error_msg}")

    # Final validation
    if not verify_kernel_activation(agent):
        raise RuntimeError(
            "FATAL: Kernel activation verification failed. "
            f"State: {agent.kernel_state}, Kernels: {len(agent.kernels)}"
        )

    logger.info(
        "kernel_loader.two_phase_complete",
        kernels=result.kernels_activated,
        state=result.state.value,
    )

    return agent


# =============================================================================
# Verification
# =============================================================================


def verify_kernel_activation(agent: Any) -> bool:
    """
    Verify that an agent has properly activated kernels.

    Returns:
        True if kernels are active, False otherwise
    """
    if not hasattr(agent, "kernel_state"):
        return False

    if agent.kernel_state != KernelState.ACTIVE.value:
        return False

    if not hasattr(agent, "kernels") or len(agent.kernels) == 0:
        return False

    return not len(agent.kernels) < REQUIRED_KERNEL_COUNT


def require_kernel_activation(agent: Any) -> None:
    """
    Assert that kernels are active. Hard crash if not.

    This should be called at agent boot.
    """
    if not verify_kernel_activation(agent):
        raise RuntimeError(
            "FATAL: Kernel activation failed. No tools. No Mac-Agent. No execution. "
            f"State: {getattr(agent, 'kernel_state', 'UNKNOWN')}, "
            f"Kernels: {len(getattr(agent, 'kernels', {}))}"
        )


# =============================================================================
# Integrity Verification
# =============================================================================


def verify_kernel_integrity(
    agent: Any,
    base_path: Path | None = None,
) -> dict[str, str]:
    """
    Verify kernel file integrity against stored hashes.

    Args:
        agent: Agent with loaded kernels
        base_path: Base path for kernel files

    Returns:
        Dict mapping kernel path to change status:
        - "OK": Hash matches
        - "MODIFIED": Hash differs
        - "MISSING": File not found
        - "NEW": File exists but no stored hash
    """
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent

    # Get stored hashes
    stored_hashes = getattr(agent, "kernel_hashes", None) or getattr(
        agent, "_kernel_hashes", {}
    )

    results: dict[str, str] = {}

    for kernel_path in KERNEL_ORDER:
        full_path = base_path / kernel_path

        if not full_path.exists():
            results[kernel_path] = "MISSING"
            continue

        current_hash = _sha256_of_file(full_path)
        stored_hash = stored_hashes.get(kernel_path)

        if stored_hash is None:
            results[kernel_path] = "NEW"
        elif current_hash == stored_hash:
            results[kernel_path] = "OK"
        else:
            results[kernel_path] = "MODIFIED"

    return results


# =============================================================================
# Hot Reload (v3.4+ / GMP-KERNEL-BOOT)
# =============================================================================


class KernelReloadResult:
    """Result of a kernel hot-reload operation."""

    def __init__(
        self,
        success: bool,
        kernels_reloaded: int,
        modified_kernels: list[str],
        errors: list[str],
        previous_hashes: dict[str, str],
        new_hashes: dict[str, str],
    ):
        """
        Initializes a KernelReloadResult object representing the outcome of a kernel hot-reload operation within the L9 Kernel Loader.

        Args:
            success: Indicates if the reload was successful.
            kernels_reloaded: Number of kernels reloaded during the operation.
            modified_kernels: List of kernel identifiers that were modified.
            errors: List of error messages encountered during reload.
            previous_hashes: Mapping of kernel identifiers to their hashes before reload.
            new_hashes: Mapping of kernel identifiers to their hashes after reload.
        """
        self.success = success
        self.kernels_reloaded = kernels_reloaded
        self.modified_kernels = modified_kernels
        self.errors = errors
        self.previous_hashes = previous_hashes
        self.new_hashes = new_hashes


def reload_kernels(
    agent: Any,
    base_path: Path | None = None,
    force: bool = False,
) -> KernelReloadResult:
    """
    Hot-reload kernels without restarting the process.

    This function:
    1. Checks which kernels have been modified
    2. Re-loads only modified kernels (or all if force=True)
    3. Re-activates the agent with new kernel data
    4. Logs evolution to memory substrate

    Args:
        agent: Agent with existing kernels
        base_path: Base path for kernel files
        force: If True, reload all kernels regardless of changes

    Returns:
        KernelReloadResult with reload status

    Note:
        This is a potentially disruptive operation. Use with caution.
        The agent's kernel_state will briefly transition to RELOADING.
    """
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent

    # Create reload span
    reload_span = _create_kernel_span(
        name="kernel_loader.reload",
        kernel_id="all",
        phase="reload",
        force=force,
        agent_id=getattr(agent, "agent_id", "unknown"),
    )

    logger.info(
        "kernel_loader.reload_start",
        force=force,
        agent_id=getattr(agent, "agent_id", "unknown"),
    )

    errors: list[str] = []

    # Get previous hashes
    previous_hashes = getattr(agent, "kernel_hashes", None) or getattr(
        agent, "_kernel_hashes", {}
    )

    # Check integrity to find modified kernels
    integrity_status = verify_kernel_integrity(agent, base_path)
    modified_kernels = [
        path
        for path, status in integrity_status.items()
        if status in ("MODIFIED", "NEW") or force
    ]

    if not modified_kernels and not force:
        logger.info("kernel_loader.reload_skipped", reason="no_changes")
        _finish_span(reload_span, status="OK")
        return KernelReloadResult(
            success=True,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=[],
            previous_hashes=previous_hashes,
            new_hashes=previous_hashes,
        )

    logger.info(
        "kernel_loader.reload_modified_detected",
        modified_count=len(modified_kernels),
        modified=modified_kernels[:3],
    )

    # Transition to RELOADING state
    agent.kernel_state = "RELOADING"

    try:
        # Phase 1: Re-load kernels
        kernels_by_path, new_hashes, phase1_errors = load_kernels_phase1(
            base_path=base_path,
            validate_schema=True,
            verify_integrity=True,
        )

        if phase1_errors:
            for err in phase1_errors:
                if err.severity == "ERROR":
                    errors.append(err.message)

        if len(kernels_by_path) < REQUIRED_KERNEL_COUNT:
            errors.append(
                f"Insufficient kernels after reload: {len(kernels_by_path)}/{REQUIRED_KERNEL_COUNT}"
            )
            agent.kernel_state = KernelState.ERROR.value
            _finish_span(reload_span, status="ERROR", error="; ".join(errors[:3]))
            return KernelReloadResult(
                success=False,
                kernels_reloaded=0,
                modified_kernels=modified_kernels,
                errors=errors,
                previous_hashes=previous_hashes,
                new_hashes=new_hashes,
            )

        # Phase 2: Re-activate with new kernels
        result = activate_kernels_phase2(agent, kernels_by_path, new_hashes)

        if not result.success:
            for err in result.validation_errors:
                errors.append(err.message)
            _finish_span(reload_span, status="ERROR", error="; ".join(errors[:3]))
            return KernelReloadResult(
                success=False,
                kernels_reloaded=0,
                modified_kernels=modified_kernels,
                errors=errors,
                previous_hashes=previous_hashes,
                new_hashes=new_hashes,
            )

        # Final verification
        if not verify_kernel_activation(agent):
            errors.append("Kernel activation verification failed after reload")
            _finish_span(reload_span, status="ERROR", error=errors[-1])
            return KernelReloadResult(
                success=False,
                kernels_reloaded=0,
                modified_kernels=modified_kernels,
                errors=errors,
                previous_hashes=previous_hashes,
                new_hashes=new_hashes,
            )

        logger.info(
            "kernel_loader.reload_complete",
            kernels_reloaded=result.kernels_activated,
            modified_count=len(modified_kernels),
        )

        _finish_span(reload_span, status="OK")
        return KernelReloadResult(
            success=True,
            kernels_reloaded=result.kernels_activated,
            modified_kernels=modified_kernels,
            errors=errors,
            previous_hashes=previous_hashes,
            new_hashes=new_hashes,
        )

    except Exception as e:
        errors.append(f"Reload failed with exception: {e!s}")
        logger.error("kernel_loader.reload_exception", error=str(e), exc_info=True)
        agent.kernel_state = KernelState.ERROR.value
        _finish_span(reload_span, status="ERROR", error=str(e))
        return KernelReloadResult(
            success=False,
            kernels_reloaded=0,
            modified_kernels=modified_kernels,
            errors=errors,
            previous_hashes=previous_hashes,
            new_hashes={},
        )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Configuration
    "DEFAULT_KERNEL_PATH",
    "KERNEL_EXTENSIONS",
    "KERNEL_ID_MAP",
    "KERNEL_ORDER",
    "REQUIRED_KERNEL_COUNT",
    # Protocol
    "KernelAwareAgent",
    "KernelReloadResult",
    "activate_kernels_phase2",
    "load_kernels",
    # Two-phase loading
    "load_kernels_phase1",
    # Hot reload
    "reload_kernels",
    "require_kernel_activation",
    # Verification
    "verify_kernel_activation",
    "verify_kernel_integrity",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-003",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.kernels.schemas",
        "core.observability.models",
        "core.observability.service",
    ],
    "tags": [
        "api",
        "authorization",
        "config",
        "core",
        "debugging",
        "filesystem",
        "foundation",
        "logging",
        "messaging",
        "rest-api",
    ],
    "keywords": [
        "absorb",
        "activate",
        "activation",
        "agent",
        "aware",
        "integrity",
        "kernel",
        "kernels",
    ],
    "business_value": "This is the ONLY way kernels enter the system. If this file isn't used → kernels are not real. Version: 2.0.0 GMP: kernel_boot_frontier_phase1 Two-phase activation (LOAD → ACTIVATE) Pydantic schema va",
    "last_modified": "2026-01-14T15:03:00Z",
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
