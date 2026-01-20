"""
L9 Kernel Protocols - Core Abstractions
========================================

Frontier-grade protocol definitions for kernel subsystem following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready abstractions for kernel operations.

Features:
- ✅ Protocol-based abstractions for all kernel operations
- ✅ Type-safe interfaces with comprehensive type hints
- ✅ Enables dependency injection and testing
- ✅ Zero runtime overhead (protocols are compile-time only)
- ✅ Supports hot-swapping implementations

Protocols:
- KernelValidator: Validates kernel YAML against schema
- KernelDiscovery: Discovers kernel files from configuration
- IntegrityVerifier: Verifies kernel file integrity
- KernelActivator: Activates kernels with context injection
- KernelStateManager: Manages kernel lifecycle state

Version: 1.0.0
GMP: di-dip-phase1-abstractions
Author: Top Frontier AI Lab
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Kernel Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "kernel_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.kernels.kernelloader",
            "core.di.container",
            "tests.unit.test_kernel_protocols",
        ],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from core.kernels.schemas import (
    KernelActivationResult,
    KernelManifest,
    KernelState,
    KernelValidationResult,
)


@runtime_checkable
class KernelValidator(Protocol):
    """
    Protocol for kernel YAML validation.

    Implementations must validate kernel data against schema and return
    structured validation results.

    Example implementations:
    - PydanticKernelValidator: Uses Pydantic models for validation
    - StrictKernelValidator: Enhanced validation with custom rules
    - MockKernelValidator: Test double for unit testing
    """

    def validate(self, data: Dict[str, Any], file_path: str) -> KernelValidationResult:
        """
        Validate kernel data against schema.

        Args:
            data: Parsed YAML data as dictionary
            file_path: Path to kernel file (for error reporting)

        Returns:
            KernelValidationResult with validation status and errors

        Raises:
            ValidationError: If validation fails critically
        """
        ...

    def validate_manifest(self, manifest: KernelManifest) -> bool:
        """
        Validate a kernel manifest object.

        Args:
            manifest: Parsed KernelManifest instance

        Returns:
            True if valid, False otherwise
        """
        ...


@runtime_checkable
class KernelDiscovery(Protocol):
    """
    Protocol for kernel file discovery.

    Implementations must discover kernel files based on configuration
    and return ordered list of paths.

    Example implementations:
    - OrderedKernelDiscovery: Fixed order from configuration
    - GlobKernelDiscovery: Pattern-based discovery
    - DynamicKernelDiscovery: Runtime-determined order
    """

    def discover_kernels(self, base_path: Path) -> List[Path]:
        """
        Discover kernel files from base path.

        Args:
            base_path: Root directory to search for kernels

        Returns:
            Ordered list of kernel file paths

        Raises:
            FileNotFoundError: If base path doesn't exist
            ValueError: If no kernels found
        """
        ...

    def get_kernel_order(self) -> List[str]:
        """
        Get the configured kernel loading order.

        Returns:
            List of kernel identifiers in load order
        """
        ...


@runtime_checkable
class IntegrityVerifier(Protocol):
    """
    Protocol for kernel file integrity verification.

    Implementations must compute and verify file hashes to ensure
    kernel files haven't been tampered with.

    Example implementations:
    - SHA256IntegrityVerifier: SHA-256 based verification
    - MD5IntegrityVerifier: MD5 based verification (legacy)
    - NoOpIntegrityVerifier: Bypass verification (testing only)
    """

    def compute_hash(self, path: Path) -> str:
        """
        Compute hash of kernel file.

        Args:
            path: Path to kernel file

        Returns:
            Hex-encoded hash string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file can't be read
        """
        ...

    def verify_integrity(self, path: Path, stored_hash: str) -> bool:
        """
        Verify kernel file integrity against stored hash.

        Args:
            path: Path to kernel file
            stored_hash: Previously computed hash

        Returns:
            True if hashes match, False otherwise
        """
        ...

    def get_algorithm(self) -> str:
        """
        Get the hash algorithm name.

        Returns:
            Algorithm name (e.g., "sha256", "md5")
        """
        ...


@runtime_checkable
class KernelActivator(Protocol):
    """
    Protocol for kernel activation operations.

    Implementations must handle kernel activation with context injection
    and state management.

    Example implementations:
    - StandardKernelActivator: Default activation logic
    - TracedKernelActivator: Activation with observability
    - MockKernelActivator: Test double for activation
    """

    def activate(
        self,
        manifest: KernelManifest,
        agent: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> KernelActivationResult:
        """
        Activate a kernel with context injection.

        Args:
            manifest: Validated kernel manifest
            agent: Agent instance to activate
            context: Optional activation context

        Returns:
            KernelActivationResult with activation status

        Raises:
            ActivationError: If activation fails
        """
        ...

    def deactivate(self, agent: Any) -> bool:
        """
        Deactivate a kernel.

        Args:
            agent: Agent instance to deactivate

        Returns:
            True if deactivation successful
        """
        ...


@runtime_checkable
class KernelStateManager(Protocol):
    """
    Protocol for kernel lifecycle state management.

    Implementations must track kernel state transitions and provide
    state query capabilities.

    Example implementations:
    - InMemoryStateManager: State stored in memory
    - PersistentStateManager: State persisted to storage
    - DistributedStateManager: State shared across instances
    """

    def get_state(self, kernel_id: str) -> Optional[KernelState]:
        """
        Get current state of a kernel.

        Args:
            kernel_id: Unique kernel identifier

        Returns:
            Current KernelState or None if not found
        """
        ...

    def set_state(self, kernel_id: str, state: KernelState) -> None:
        """
        Set state of a kernel.

        Args:
            kernel_id: Unique kernel identifier
            state: New kernel state
        """
        ...

    def transition_state(
        self, kernel_id: str, from_state: KernelState, to_state: KernelState
    ) -> bool:
        """
        Transition kernel state with validation.

        Args:
            kernel_id: Unique kernel identifier
            from_state: Expected current state
            to_state: Target state

        Returns:
            True if transition successful, False if current state doesn't match
        """
        ...

    def get_all_states(self) -> Dict[str, KernelState]:
        """
        Get states of all tracked kernels.

        Returns:
            Dictionary mapping kernel IDs to states
        """
        ...


@runtime_checkable
class KernelAwareAgent(Protocol):
    """
    Protocol for agents that can be kernel-activated.

    This replaces hasattr() checks with formal protocol adherence.

    Example implementations:
    - BaseAgent: Standard agent base class
    - CustomAgent: User-defined agent implementations
    """

    def kernel_activate(
        self, manifest: KernelManifest, context: Optional[Dict[str, Any]] = None
    ) -> KernelActivationResult:
        """
        Activate agent with kernel manifest.

        Args:
            manifest: Kernel manifest to activate
            context: Optional activation context

        Returns:
            KernelActivationResult indicating success/failure
        """
        ...

    def kernel_deactivate(self) -> bool:
        """
        Deactivate kernel from agent.

        Returns:
            True if deactivation successful
        """
        ...

    def get_kernel_state(self) -> Optional[KernelState]:
        """
        Get current kernel state.

        Returns:
            Current KernelState or None if not activated
        """
        ...


# Type aliases for common use cases
KernelProtocols = (
    KernelValidator
    | KernelDiscovery
    | IntegrityVerifier
    | KernelActivator
    | KernelStateManager
)


__all__ = [
    "KernelValidator",
    "KernelDiscovery",
    "IntegrityVerifier",
    "KernelActivator",
    "KernelStateManager",
    "KernelAwareAgent",
    "KernelProtocols",
]
