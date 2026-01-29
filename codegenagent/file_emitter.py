"""
CodeGenAgent File Emitter
=========================

Writes generated code files to the L9 repository with proper wiring.

Key Features:
- Write generated Python files to target paths
- Auto-wire routes into api/server.py
- Update registries (AgentRegistry, ToolGraph)
- Track all changes for potential rollback
- Dry-run mode for preview

Uses patterns from Module-Prompt-CURSOR-v2.0.yaml:
- Phase 3: Write code files
- Phase 6: Wire server.py
- Phase 7: Verification gates

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "File Emitter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "codegenagent",
    "module_name": "file_emitter",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from ir_engine.compile_meta_to_ir import ModuleIR, WiringSpec

logger = structlog.get_logger(__name__)


# =============================================================================
# FILE TRACKING
# =============================================================================


class FileChange:
    """Tracks a single file change for rollback."""

    def __init__(
        self,
        path: str,
        action: str,  # create, modify, delete
        old_content: str | None = None,
        new_content: str | None = None,
    ):
        self.path = path
        self.action = action
        self.old_content = old_content
        self.new_content = new_content
        self.timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"FileChange({self.action}: {self.path})"


class EmissionResult:
    """Result of file emission operation."""

    def __init__(self):
        self.created_files: list[str] = []
        self.modified_files: list[str] = []
        self.skipped_files: list[str] = []
        self.errors: list[tuple[str, str]] = []
        self.changes: list[FileChange] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def file_count(self) -> int:
        return len(self.created_files) + len(self.modified_files)

    def to_summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "created": len(self.created_files),
            "modified": len(self.modified_files),
            "skipped": len(self.skipped_files),
            "errors": len(self.errors),
            "created_files": self.created_files,
            "modified_files": self.modified_files,
        }


# =============================================================================
# FILE EMITTER
# =============================================================================


class FileEmitter:
    """
    Writes generated code files to the repository.

    Handles:
    - Creating new files with proper directories
    - Modifying existing files (with backup)
    - Auto-wiring routes into server.py
    - Tracking changes for rollback
    """

    def __init__(
        self,
        repo_root: str = "/Users/ib-mac/Projects/L9",
        dry_run: bool = False,
    ):
        """
        Initialize file emitter.

        Args:
            repo_root: Root path of the repository
            dry_run: If True, don't actually write files
        """
        self.repo_root = Path(repo_root)
        self.dry_run = dry_run
        self._changes: list[FileChange] = []

        logger.info(
            "file_emitter_initialized",
            repo_root=str(self.repo_root),
            dry_run=dry_run,
        )

    def emit(
        self,
        files: dict[str, str],
        wiring: WiringSpec | None = None,
    ) -> EmissionResult:
        """
        Emit generated files to the repository.

        Args:
            files: Dictionary mapping file paths to content
            wiring: Optional wiring specification for server.py

        Returns:
            EmissionResult with details of what was done
        """
        result = EmissionResult()

        logger.info(
            "emitting_files",
            file_count=len(files),
            dry_run=self.dry_run,
        )

        # Phase 1: Create directories
        self._ensure_directories(files.keys())

        # Phase 2: Write code files
        for path, content in files.items():
            try:
                self._write_file(path, content, result)
            except Exception as e:
                result.errors.append((path, str(e)))
                logger.error("file_write_failed", path=path, error=str(e))

        # Phase 3: Wire into server.py if needed
        if wiring and wiring.router_include:
            try:
                self._wire_server(wiring, result)
            except Exception as e:
                result.errors.append(("api/server.py", str(e)))
                logger.error("server_wiring_failed", error=str(e))

        # Track all changes
        result.changes = self._changes.copy()

        logger.info(
            "emission_complete",
            **result.to_summary(),
        )

        return result

    def emit_from_ir(
        self, ir: ModuleIR, generated_files: dict[str, str]
    ) -> EmissionResult:
        """
        Emit files from a ModuleIR and generated code.

        Args:
            ir: ModuleIR with wiring specification
            generated_files: Dictionary of file path to content

        Returns:
            EmissionResult with details
        """
        return self.emit(generated_files, ir.wiring)

    def rollback(self) -> int:
        """
        Rollback all changes made by this emitter.

        Returns:
            Number of files rolled back
        """
        if self.dry_run:
            logger.info("rollback_skipped_dry_run")
            return 0

        rolled_back = 0

        for change in reversed(self._changes):
            try:
                full_path = self.repo_root / change.path

                if change.action == "create":
                    # Remove created file
                    if full_path.exists():
                        full_path.unlink()
                        rolled_back += 1

                elif change.action == "modify":
                    # Restore original content
                    if change.old_content is not None:
                        full_path.write_text(change.old_content, encoding="utf-8")
                        rolled_back += 1

            except Exception as e:
                logger.error(
                    "rollback_failed",
                    path=change.path,
                    error=str(e),
                )

        self._changes.clear()

        logger.info("rollback_complete", rolled_back=rolled_back)
        return rolled_back

    def preview(self, files: dict[str, str]) -> dict[str, Any]:
        """
        Preview what would be written without actually writing.

        Args:
            files: Dictionary mapping file paths to content

        Returns:
            Preview information
        """
        preview = {
            "new_files": [],
            "modified_files": [],
            "directories_to_create": [],
        }

        # Check directories
        dirs_needed = set()
        for path in files:
            full_path = self.repo_root / path
            parent = full_path.parent
            if not parent.exists():
                dirs_needed.add(str(parent.relative_to(self.repo_root)))

        preview["directories_to_create"] = sorted(dirs_needed)

        # Check files
        for path, content in files.items():
            full_path = self.repo_root / path
            if full_path.exists():
                preview["modified_files"].append(
                    {
                        "path": path,
                        "current_size": full_path.stat().st_size,
                        "new_size": len(content.encode("utf-8")),
                    }
                )
            else:
                preview["new_files"].append(
                    {
                        "path": path,
                        "size": len(content.encode("utf-8")),
                        "lines": content.count("\n"),
                    }
                )

        return preview

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _ensure_directories(self, paths: list[str]) -> None:
        """Ensure all parent directories exist."""
        if self.dry_run:
            return

        for path in paths:
            full_path = self.repo_root / path
            parent = full_path.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
                logger.debug("directory_created", path=str(parent))

    def _write_file(
        self,
        path: str,
        content: str,
        result: EmissionResult,
    ) -> None:
        """Write a single file."""
        full_path = self.repo_root / path

        # Track old content if file exists
        old_content = None
        if full_path.exists():
            old_content = full_path.read_text(encoding="utf-8")
            action = "modify"
        else:
            action = "create"

        # Record change
        self._changes.append(
            FileChange(
                path=path,
                action=action,
                old_content=old_content,
                new_content=content,
            )
        )

        # Write file (unless dry run)
        if not self.dry_run:
            full_path.write_text(content, encoding="utf-8")

        # Update result
        if action == "create":
            result.created_files.append(path)
        else:
            result.modified_files.append(path)

        logger.debug(
            "file_written",
            path=path,
            action=action,
            dry_run=self.dry_run,
        )

    def _wire_server(
        self,
        wiring: WiringSpec,
        result: EmissionResult,
    ) -> None:
        """Wire module into api/server.py."""
        server_path = self.repo_root / "api" / "server.py"

        if not server_path.exists():
            logger.warning("server_py_not_found", path=str(server_path))
            return

        # Read current content
        content = server_path.read_text(encoding="utf-8")
        old_content = content

        # Extract module name from router_include
        module_name = wiring.router_include.replace("_router", "")

        # Check if already wired
        if f"from api.routes.{module_name}" in content:
            result.skipped_files.append("api/server.py")
            logger.debug("server_already_wired", module=module_name)
            return

        # Generate wiring code
        import_line = (
            f"from api.routes.{module_name} import router as {module_name}_router"
        )
        include_line = f"app.include_router({module_name}_router)"

        # Find insertion points
        modified = False

        # Add import (after other route imports)
        import_pattern = r"(from api\.routes\.\w+ import router as \w+_router)"
        import_match = re.search(import_pattern, content)
        if import_match:
            # Insert after last route import
            last_match = None
            for match in re.finditer(import_pattern, content):
                last_match = match
            if last_match:
                insert_pos = last_match.end()
                content = (
                    content[:insert_pos] + f"\n{import_line}" + content[insert_pos:]
                )
                modified = True

        # Add router include
        include_pattern = r"(app\.include_router\(\w+_router\))"
        include_match = re.search(include_pattern, content)
        if include_match:
            last_match = None
            for match in re.finditer(include_pattern, content):
                last_match = match
            if last_match:
                insert_pos = last_match.end()
                content = (
                    content[:insert_pos] + f"\n{include_line}" + content[insert_pos:]
                )
                modified = True

        if modified:
            # Record change
            self._changes.append(
                FileChange(
                    path="api/server.py",
                    action="modify",
                    old_content=old_content,
                    new_content=content,
                )
            )

            # Write file
            if not self.dry_run:
                server_path.write_text(content, encoding="utf-8")

            result.modified_files.append("api/server.py")
            logger.info("server_wired", module=module_name)
        else:
            result.skipped_files.append("api/server.py")
            logger.warning("server_wiring_pattern_not_found", module=module_name)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def emit_files(
    files: dict[str, str],
    repo_root: str = "/Users/ib-mac/Projects/L9",
    dry_run: bool = False,
) -> EmissionResult:
    """
    Emit generated files to repository.

    Args:
        files: Dictionary mapping file paths to content
        repo_root: Root path of repository
        dry_run: If True, don't write files

    Returns:
        EmissionResult
    """
    emitter = FileEmitter(repo_root=repo_root, dry_run=dry_run)
    return emitter.emit(files)


def preview_emission(
    files: dict[str, str],
    repo_root: str = "/Users/ib-mac/Projects/L9",
) -> dict[str, Any]:
    """
    Preview what would be written.

    Args:
        files: Dictionary mapping file paths to content
        repo_root: Root path of repository

    Returns:
        Preview information
    """
    emitter = FileEmitter(repo_root=repo_root, dry_run=True)
    return emitter.preview(files)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "codegenagent",
        "debugging",
        "filesystem",
        "logging",
        "operations",
        "rest-api",
        "utility",
    ],
    "keywords": [
        "change",
        "count",
        "emission",
        "emit",
        "emitter",
        "files",
        "generated",
        "module",
    ],
    "business_value": "Provides file emitter components including FileChange, EmissionResult, FileEmitter",
    "last_modified": "2026-01-25T14:49:28Z",
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
