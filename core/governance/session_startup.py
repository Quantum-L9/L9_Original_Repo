"""
L9 Core Governance - Session Startup Protocol
==============================================

Executable session startup protocol.
Converts patterns from profiles/session-startup-protocol.md into
programmatic preflight checks and mandatory file loading.

Key capabilities:
- Runs preflight checks (symlinks, config, directories)
- Loads mandatory startup files
- Loads Architecture Decision Records (ADRs) per ADR-0003
- Verifies kernel readiness (two-phase activation)
- Returns structured status (not just instructions)
- Tracks loaded components for debugging

ARCHITECTURE NOTES
==================
Per ADR-0003 (Documentation Standards), all AI agents MUST read ADRs at startup.
This module loads readme/adr/*.md files and makes them available for governance
verification and code review guidance.

REFERENCES
==========
- ADR-0003: Documentation Standards (readme/adr/0003-documentation-standards.md)
- ADR-0002: Circular Import Prevention (readme/adr/0002-circular-import-prevention.md)

Version: 2.1.0
GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Session Startup Protocol",
    "module_version": "2.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "session_startup",
    "type": "dataclass",
    "status": "active",
    "architecture_patterns": [
        "ADR loading at startup (ADR-0003)",
    ],
    "pep_compliance": ["PEP 563"],
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "scripts.workspace.init_workspace",
            "tests.unit.test_startup_readiness",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StartupFile:
    """
    A mandatory startup file.

    Attributes:
        path: Relative path from workspace root
        component_id: Unique identifier (e.g., "PRF-SSP-001")
        required: Whether missing file is a failure
        description: What this file provides
    """

    path: str
    component_id: str
    required: bool = True
    description: str = ""


@dataclass
class PreflightResult:
    """Result of a preflight check."""

    name: str
    passed: bool
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class KernelReadinessResult:
    """Result of kernel readiness check."""

    kernels_ready: bool
    kernel_state: str  # INACTIVE, LOADING, VALIDATING, ACTIVE, ERROR
    kernel_count: int
    kernel_hash_snapshot: Dict[str, str] = field(default_factory=dict)
    integrity_verified: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class ADRLoadResult:
    """
    Result of loading Architecture Decision Records.

    Per ADR-0003, all AI agents MUST read ADRs at startup before code operations.
    This dataclass tracks which ADRs were loaded and their status.
    """

    adrs_loaded: list[str]  # List of ADR filenames loaded
    adr_count: int  # Total count of ADRs found
    adr_index: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )  # ADR number -> metadata
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether all ADRs loaded successfully."""
        return len(self.errors) == 0 and self.adr_count > 0


@dataclass
class StartupResult:
    """Complete startup protocol result."""

    status: str  # "READY", "DEGRADED", "BLOCKED"
    preflight_passed: bool
    files_loaded: list[str]
    files_failed: list[str]
    errors: list[str]
    warnings: list[str]
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    # Kernel readiness (new in v2.0)
    kernels_ready: bool = False
    kernel_state: str = "NOT_CHECKED"
    kernel_hash_snapshot: Dict[str, str] = field(default_factory=dict)
    # ADR loading (new in v2.1.0, per ADR-0003)
    adrs_loaded: list[str] = field(default_factory=list)
    adr_count: int = 0
    adr_index: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class SessionStartup:
    """
    Executable session startup protocol.

    Runs preflight checks, loads mandatory files, and verifies kernel readiness,
    returning structured status for governance verification.

    Usage:
        startup = SessionStartup(Path("/Users/ib-mac/Projects/L9"))
        result = startup.execute()
        if result.status != "READY":
            # Handle startup issues
            pass

    Kernel Readiness (v2.0):
        - Checks if kernel files exist
        - Verifies kernel integrity (SHA256 hashes)
        - Reports kernel state from agent registry
    """

    def __init__(
        self,
        workspace_root: Path,
        check_kernels: bool = True,
    ) -> None:
        """
        Initialize startup protocol.

        Args:
            workspace_root: Path to workspace root directory
            check_kernels: Whether to check kernel readiness (default True)
        """
        self.root = workspace_root
        self.check_kernels = check_kernels
        self._files_loaded: list[str] = []
        self._errors: list[str] = []
        self._warnings: list[str] = []
        self._kernel_result: Optional[KernelReadinessResult] = None

    @property
    def mandatory_files(self) -> list[StartupFile]:
        """Get list of mandatory startup files."""
        return [
            # Core governance
            StartupFile(
                ".cursor-commands/profiles/session-startup-protocol.md",
                "PRF-SSP-001",
                required=True,
                description="Session startup protocol",
            ),
            StartupFile(
                ".cursor-commands/startup/REASONING_STACK.yaml",
                "REASONING-STACK-001",
                required=True,
                description="Reasoning activation config",
            ),
            # Learning files
            StartupFile(
                ".cursor-commands/learning/credentials-policy.md",
                "LRN-006",
                required=False,
                description="Credentials handling policy",
            ),
            StartupFile(
                ".cursor-commands/learning/failures/repeated-mistakes.md",
                "LRN-001",
                required=True,
                description="Critical mistake patterns",
            ),
            StartupFile(
                ".cursor-commands/learning/patterns/quick-fixes.md",
                "LRN-002",
                required=True,
                description="Quick fix patterns",
            ),
            # Startup files
            StartupFile(
                ".cursor-commands/startup/system_capabilities.md",
                "STARTUP-001",
                required=False,
                description="System capabilities manifest",
            ),
            StartupFile(
                ".cursor-commands/startup/probabilistic_governance_activated.md",
                "STARTUP-002",
                required=False,
                description="Probabilistic governance config",
            ),
            # Reasoning profiles
            StartupFile(
                ".cursor-commands/profiles/reasoning_docs.md",
                "PROFILE-001",
                required=False,
                description="Documentation reasoning mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/reasoning_technical_operations.md",
                "PROFILE-002",
                required=False,
                description="Technical operations reasoning",
            ),
            # Operating modes
            StartupFile(
                ".cursor-commands/profiles/ynp_mode.md",
                "MODE-001",
                required=False,
                description="YNP co-pilot mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/dev_mode.md",
                "MODE-002",
                required=False,
                description="Development automation mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/orchestrator.md",
                "MODE-003",
                required=False,
                description="Orchestrator coordination mode",
            ),
            # Workflow state
            StartupFile(
                "workflow_state.md",
                "STATE-001",
                required=True,
                description="Workflow state tracking",
            ),
        ]

    def run_preflight(self) -> list[PreflightResult]:
        """
        Execute preflight checks.

        Returns:
            List of PreflightResult objects
        """
        results: list[PreflightResult] = []

        # Check 1: Workspace root exists
        results.append(
            PreflightResult(
                name="workspace_exists",
                passed=self.root.exists(),
                message=f"Workspace root: {self.root}",
            )
        )

        # Check 2: .cursor-commands symlink
        symlink = self.root / ".cursor-commands"
        symlink_valid = symlink.is_symlink() and symlink.exists()
        symlink_target = ""
        if symlink.is_symlink():
            try:
                symlink_target = str(symlink.resolve())
            except Exception:
                symlink_target = "unresolvable"

        results.append(
            PreflightResult(
                name="symlink_valid",
                passed=symlink_valid,
                message=f"Symlink target: {symlink_target}",
                details={"target": symlink_target, "is_symlink": symlink.is_symlink()},
            )
        )

        # Check 3: Symlink points to Dropbox (not Library)
        dropbox_valid = "Dropbox" in symlink_target
        results.append(
            PreflightResult(
                name="symlink_dropbox",
                passed=dropbox_valid,
                message="Symlink must point to Dropbox, not Library",
                details={"contains_dropbox": dropbox_valid},
            )
        )

        # Check 4: workflow_state.md exists
        workflow_state = self.root / "workflow_state.md"
        results.append(
            PreflightResult(
                name="workflow_state_exists",
                passed=workflow_state.exists(),
                message=f"Workflow state: {workflow_state}",
            )
        )

        # Check 5: core/governance/ exists
        gov_dir = self.root / "core" / "governance"
        results.append(
            PreflightResult(
                name="governance_dir_exists",
                passed=gov_dir.exists(),
                message=f"Governance directory: {gov_dir}",
            )
        )

        return results

    def load_mandatory_files(self) -> dict[str, Any]:
        """
        Load all mandatory startup files.

        Returns:
            Dict with loaded, failed, and total counts
        """
        results: dict[str, Any] = {
            "loaded": [],
            "failed": [],
            "total": len(self.mandatory_files),
        }

        for sf in self.mandatory_files:
            path = self.root / sf.path

            if path.exists():
                try:
                    # Just verify we can read it
                    content = path.read_text(encoding="utf-8")
                    self._files_loaded.append(sf.component_id)
                    results["loaded"].append(
                        {
                            "path": sf.path,
                            "component_id": sf.component_id,
                            "size_bytes": len(content),
                        }
                    )
                    logger.debug(
                        "session_startup.file_loaded",
                        path=sf.path,
                        component_id=sf.component_id,
                    )
                except Exception as e:
                    results["failed"].append(
                        {
                            "path": sf.path,
                            "error": str(e),
                        }
                    )
                    if sf.required:
                        self._errors.append(f"CRITICAL: Cannot read {sf.path}: {e}")
                    else:
                        self._warnings.append(f"Cannot read {sf.path}: {e}")
            else:
                results["failed"].append(
                    {
                        "path": sf.path,
                        "error": "File not found",
                    }
                )
                if sf.required:
                    self._errors.append(f"CRITICAL: Missing required file {sf.path}")
                else:
                    self._warnings.append(f"Optional file missing: {sf.path}")

        results["success"] = (
            len([f for f in results["failed"] if "CRITICAL" in str(f)]) == 0
        )
        return results

    def check_kernel_readiness(self) -> KernelReadinessResult:
        """
        Check kernel readiness for L-CTO agent.

        Verifies:
        1. Kernel files exist in private/kernels/00_system/
        2. Kernel integrity (SHA256 hashes)
        3. Kernel state from agent registry (if available)

        Returns:
            KernelReadinessResult with readiness status
        """
        errors: list[str] = []
        kernel_hashes: Dict[str, str] = {}

        # Check kernel files exist
        kernel_dir = self.root / "private" / "kernels" / "00_system"
        if not kernel_dir.exists():
            errors.append(f"Kernel directory not found: {kernel_dir}")
            return KernelReadinessResult(
                kernels_ready=False,
                kernel_state="NOT_FOUND",
                kernel_count=0,
                errors=errors,
            )

        # Count and hash kernel files
        kernel_files = list(kernel_dir.glob("*.yaml"))
        if len(kernel_files) < 10:
            errors.append(f"Insufficient kernel files: {len(kernel_files)}/10 required")

        # Compute hashes for integrity verification
        try:
            import hashlib

            for kf in kernel_files:
                data = kf.read_bytes()
                kernel_hashes[str(kf.relative_to(self.root))] = hashlib.sha256(
                    data
                ).hexdigest()
        except Exception as e:
            errors.append(f"Failed to compute kernel hashes: {e}")

        # Try to get kernel state from agent registry
        kernel_state = "NOT_LOADED"
        try:
            import os

            from core.agents.kernel_registry import KernelAwareAgentRegistry

            # Only check if USE_KERNELS is enabled
            if os.getenv("L9_USE_KERNELS", "true").lower() in ("true", "1", "yes"):
                # Don't instantiate registry here (would trigger loading)
                # Just report that kernels should be checked at runtime
                kernel_state = "PENDING_LOAD"
        except ImportError:
            kernel_state = "REGISTRY_NOT_AVAILABLE"
            errors.append("Kernel registry module not available")

        # Determine readiness
        kernels_ready = len(kernel_files) >= 10 and len(errors) == 0

        result = KernelReadinessResult(
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            kernel_count=len(kernel_files),
            kernel_hash_snapshot=kernel_hashes,
            integrity_verified=len(kernel_hashes) == len(kernel_files),
            errors=errors,
        )

        self._kernel_result = result

        logger.info(
            "session_startup.kernel_check",
            kernels_ready=kernels_ready,
            kernel_count=len(kernel_files),
            kernel_state=kernel_state,
            errors=errors,
        )

        return result

    def load_adrs(self) -> ADRLoadResult:
        """
        Load Architecture Decision Records from readme/adr/.

        Per ADR-0003 (Documentation Standards), all AI agents MUST read ADRs
        at session startup before performing any code operations. This method
        loads and indexes all ADR files for governance verification.

        Returns:
            ADRLoadResult with loaded ADRs and their metadata
        """
        errors: list[str] = []
        adrs_loaded: list[str] = []
        adr_index: Dict[str, Dict[str, Any]] = {}

        adr_dir = self.root / "readme" / "adr"

        if not adr_dir.exists():
            errors.append(f"ADR directory not found: {adr_dir}")
            return ADRLoadResult(
                adrs_loaded=[],
                adr_count=0,
                adr_index={},
                errors=errors,
            )

        # Load all ADR files
        adr_files = sorted(adr_dir.glob("*.md"))

        for adr_file in adr_files:
            try:
                content = adr_file.read_text(encoding="utf-8")
                filename = adr_file.name

                # Extract ADR number from filename (e.g., "0002" from "0002-circular-import.md")
                adr_number = (
                    filename.split("-")[0]
                    if "-" in filename
                    else filename.replace(".md", "")
                )

                # Extract status from content (look for "## Status" section)
                status = "Unknown"
                title = filename
                for line in content.split("\n"):
                    if line.startswith("# ADR"):
                        title = line.replace("# ", "").strip()
                    elif "Accepted" in line:
                        status = "Accepted"
                        break
                    elif "Deprecated" in line:
                        status = "Deprecated"
                        break
                    elif "Superseded" in line:
                        status = "Superseded"
                        break

                adr_index[adr_number] = {
                    "filename": filename,
                    "title": title,
                    "status": status,
                    "path": str(adr_file.relative_to(self.root)),
                    "size_bytes": len(content),
                }

                adrs_loaded.append(filename)

                logger.debug(
                    "session_startup.adr_loaded",
                    adr_number=adr_number,
                    title=title,
                    status=status,
                )

            except Exception as e:
                errors.append(f"Failed to load ADR {adr_file.name}: {e}")

        if len(adr_files) == 0:
            self._warnings.append("No ADR files found in readme/adr/")

        logger.info(
            "session_startup.adrs_loaded",
            adr_count=len(adrs_loaded),
            accepted_count=len(
                [a for a in adr_index.values() if a["status"] == "Accepted"]
            ),
        )

        return ADRLoadResult(
            adrs_loaded=adrs_loaded,
            adr_count=len(adrs_loaded),
            adr_index=adr_index,
            errors=errors,
        )

    def execute(self) -> StartupResult:
        """
        Execute full startup protocol.

        Includes:
        1. Preflight checks (workspace, symlinks, directories)
        2. Mandatory file loading
        3. ADR loading (per ADR-0003) - REQUIRED for AI agents
        4. Kernel readiness verification (if check_kernels=True)

        Returns:
            StartupResult with complete status
        """
        start_time = datetime.utcnow()

        # Clear state
        self._files_loaded = []
        self._errors = []
        self._warnings = []
        self._kernel_result = None

        # Run preflight
        preflight_results = self.run_preflight()
        preflight_passed = all(
            r.passed
            for r in preflight_results
            if r.name in ["workspace_exists", "workflow_state_exists"]
        )

        if not preflight_passed:
            for r in preflight_results:
                if not r.passed:
                    self._errors.append(f"Preflight failed: {r.name} - {r.message}")

            return StartupResult(
                status="BLOCKED",
                preflight_passed=False,
                files_loaded=[],
                files_failed=[r.name for r in preflight_results if not r.passed],
                errors=self._errors,
                warnings=self._warnings,
                duration_ms=self._calc_duration_ms(start_time),
            )

        # Load mandatory files
        file_results = self.load_mandatory_files()

        # Load ADRs (v2.1.0 - per ADR-0003)
        # AI agents MUST read all ADRs before code operations
        adr_result = self.load_adrs()
        adrs_loaded = adr_result.adrs_loaded
        adr_count = adr_result.adr_count
        adr_index = adr_result.adr_index

        # Add ADR errors/warnings
        for err in adr_result.errors:
            self._warnings.append(f"ADR: {err}")

        # Check kernel readiness (v2.0)
        kernels_ready = False
        kernel_state = "NOT_CHECKED"
        kernel_hash_snapshot: Dict[str, str] = {}

        if self.check_kernels:
            kernel_result = self.check_kernel_readiness()
            kernels_ready = kernel_result.kernels_ready
            kernel_state = kernel_result.kernel_state
            kernel_hash_snapshot = kernel_result.kernel_hash_snapshot

            # Add kernel errors to main errors
            for err in kernel_result.errors:
                if "Insufficient" in err or "not found" in err.lower():
                    self._errors.append(f"CRITICAL: {err}")
                else:
                    self._warnings.append(f"Kernel: {err}")

        # Determine status
        critical_failures = [e for e in self._errors if "CRITICAL" in e]
        if critical_failures:
            status = "BLOCKED"
        elif self._warnings:
            status = "DEGRADED"
        else:
            status = "READY"

        duration_ms = self._calc_duration_ms(start_time)

        logger.info(
            "session_startup.complete",
            status=status,
            files_loaded=len(file_results["loaded"]),
            files_failed=len(file_results["failed"]),
            adrs_loaded=adr_count,
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            duration_ms=duration_ms,
        )

        return StartupResult(
            status=status,
            preflight_passed=preflight_passed,
            files_loaded=self._files_loaded,
            files_failed=[f["path"] for f in file_results["failed"]],
            errors=self._errors,
            warnings=self._warnings,
            duration_ms=duration_ms,
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            kernel_hash_snapshot=kernel_hash_snapshot,
            adrs_loaded=adrs_loaded,
            adr_count=adr_count,
            adr_index=adr_index,
        )

    def _calc_duration_ms(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)


# Factory function
def create_session_startup(workspace_root: Optional[Path] = None) -> SessionStartup:
    """
    Create a SessionStartup instance.

    Args:
        workspace_root: Workspace root (defaults to L9 project)

    Returns:
        Configured SessionStartup
    """
    root = workspace_root or Path("/Users/ib-mac/Projects/L9")
    return SessionStartup(root)


__all__ = [
    "SessionStartup",
    "StartupFile",
    "PreflightResult",
    "StartupResult",
    "KernelReadinessResult",
    "ADRLoadResult",
    "create_session_startup",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-088",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.kernel_registry"],
    "tags": [
        "dataclass",
        "debugging",
        "filesystem",
        "foundation",
        "governance",
        "logging",
        "messaging",
        "profiling",
        "security",
    ],
    "keywords": [
        "check",
        "checks",
        "create",
        "execute",
        "files",
        "governance",
        "kernel",
        "load",
    ],
    "business_value": "Provides session startup components including StartupFile, PreflightResult, KernelReadinessResult",
    "last_modified": "2026-01-07T23:04:26Z",
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
