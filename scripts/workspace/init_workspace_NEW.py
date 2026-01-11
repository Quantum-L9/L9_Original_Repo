#!/usr/bin/env python3
"""
start-new-workspace.py — Initialize or upgrade a Cursor Governance workspace.

Reference:
- setup-new-workspace.yaml (Suite 6 v9.0.0 orchestrator)
- README.md (Cursor Governance System Status Report)
- Audit-Notes-Cursor.md (orphan vs active inventory)

Version: 9.0.0 (Suite 6)
Created: 2026-01-04
Modified: 2026-01-04
Author: Spaces Pack (Igor / Governance Pack)

Purpose:
    - Ensure `.cursor-commands` points at the Governance GlobalCommands pack
      (symlink model).
    - Run env-manager to create/refresh `.suite6-config.json`.
    - Invoke `setup-new-workspace.yaml` to perform phased initialization:
        Phase 1: Python governance (core/governance, env-manager, etc.)
        Phase 2: workflow_state / STATESYNC
        Phase 3: REASONINGSTACK.yaml / reasoning activation
        Phase 4: Reference files, profiles, commands, features

This script is intended to be part of the Spaces pack and used as the
primary entrypoint when starting a new or upgraded workspace.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Utility: Logging (simple stdout logger; in-governance code will use
# governance_logger, but this script must also be usable standalone).
# ---------------------------------------------------------------------------

def _log(msg: str, *, level: str = "INFO", verbose: bool = True) -> None:
    if not verbose and level == "INFO":
        return
    logger.info(f"[{level}] {msg}")


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def ensure_cursor_commands_symlink(
    *,
    workspace_root: Path,
    global_commands_env: str = "CURSOR_GOV_GLOBAL_COMMANDS",
    dry_run: bool,
    verbose: bool,
    force_resymlink: bool,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Ensure `.cursor-commands` is a symlink pointing to the GlobalCommands pack.

    Resolution order for target:
        1. $CURSOR_GOV_GLOBAL_COMMANDS (absolute or ~-relative path)
        2. ~/Dropbox/Cursor Governance/GlobalCommands (legacy default)
        3. ./GlobalCommands under workspace_root (fallback for Spaces pack)

    Returns:
        (success, data, error)
    """
    cwd = workspace_root
    link_path = cwd / ".cursor-commands"

    # Resolve target root
    env_target = os.environ.get(global_commands_env, "").strip()
    candidates = []

    if env_target:
        candidates.append(Path(env_target).expanduser())

    # Legacy default from audit: Dropbox/Cursor Governance/GlobalCommands
    candidates.append(
        Path.home()
        / "Dropbox"
        / "Cursor Governance"
        / "GlobalCommands"
    )

    # Fallback: a GlobalCommands directory inside workspace
    candidates.append(cwd / "GlobalCommands")

    target: Path | None = None
    for cand in candidates:
        if cand.exists():
            target = cand
            break

    if target is None:
        msg = (
            "Could not locate GlobalCommands pack. "
            f"Tried: {[str(c) for c in candidates]}"
        )
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg

    _log(f"Resolved GlobalCommands target: {target}", verbose=verbose)

    # Check existing link / directory
    if link_path.exists() or link_path.is_symlink():
        # Already correct?
        if link_path.is_symlink():
            try:
                current_target = link_path.resolve()
            except Exception:
                current_target = None

            if current_target == target and not force_resymlink:
                _log(
                    f".cursor-commands already points to {current_target}, "
                    "keeping existing symlink.",
                    verbose=verbose,
                )
                return True, {"link": str(link_path), "target": str(target)}, ""
        # Need to remove and recreate?
        if dry_run:
            _log(
                f"[DRY RUN] Would remove existing {link_path} and re-create "
                f"symlink -> {target}",
                verbose=verbose,
            )
            return True, {"link": str(link_path), "target": str(target)}, ""
        else:
            if link_path.is_dir() and not link_path.is_symlink():
                _log(
                    f"Removing existing directory at {link_path} "
                    "to replace with symlink.",
                    verbose=verbose,
                )
            else:
                _log(
                    f"Removing existing entry at {link_path} "
                    "to replace with symlink.",
                    verbose=verbose,
                )
            if link_path.is_dir() and not link_path.is_symlink():
                # Remove directory contents cautiously
                for child in link_path.iterdir():
                    _log(
                        f"Refusing to delete contents of existing directory "
                        f"{link_path}. Please clean up manually.",
                        level="ERROR",
                        verbose=verbose,
                    )
                    return False, {}, (
                        f"Existing non-symlink directory {link_path} detected. "
                        "Clean or move it before running this script."
                    )
                # After manual cleanup, remove dir
                link_path.rmdir()
            else:
                link_path.unlink()

    # Create new symlink
    if dry_run:
        _log(
            f"[DRY RUN] Would create symlink {link_path} -> {target}",
            verbose=verbose,
        )
        return True, {"link": str(link_path), "target": str(target)}, ""
    else:
        _log(f"Creating symlink {link_path} -> {target}", verbose=verbose)
        link_path.symlink_to(target, target_is_directory=True)
        return True, {"link": str(link_path), "target": str(target)}, ""


def run_env_manager(
    *,
    workspace_root: Path,
    dry_run: bool,
    verbose: bool,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Run environment/env-manager.py to sync workspace configuration and
    ensure `.suite6-config.json` is created or updated.

    Assumes env-manager.py lives in `.cursor-commands/environment/env-manager.py`
    once the symlink is in place.
    """
    env_manager_path = workspace_root / ".cursor-commands" / "environment" / "env-manager.py"

    if not env_manager_path.exists():
        msg = f"env-manager.py not found at {env_manager_path}"
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg

    cmd = [sys.executable, str(env_manager_path), "sync"]
    _log(f"Prepared env-manager command: {' '.join(cmd)}", verbose=verbose)

    if dry_run:
        _log("[DRY RUN] Would execute env-manager sync.", verbose=verbose)
        return True, {"command": cmd}, ""
    else:
        try:
            _log("Running env-manager sync...", verbose=verbose)
            result = subprocess.run(
                cmd,
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                msg = (
                    "env-manager sync failed with exit code "
                    f"{result.returncode}: {result.stderr.strip()}"
                )
                _log(msg, level="ERROR", verbose=verbose)
                return False, {"stdout": result.stdout, "stderr": result.stderr}, msg
            _log("env-manager sync completed successfully.", verbose=verbose)
            return True, {"stdout": result.stdout}, ""
        except Exception as e:
            msg = f"Error running env-manager: {e}"
            _log(msg, level="ERROR", verbose=verbose)
            return False, {}, msg


def run_setup_new_workspace_yaml(
    *,
    workspace_root: Path,
    yaml_path: Path | None,
    dry_run: bool,
    verbose: bool,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Invoke `setup-new-workspace.yaml` orchestrator to perform phased
    initialization / upgrade.

    The YAML defines phases:
        Phase 1: Python governance (core/governance, env-manager, etc.)
        Phase 2: workflow_state / STATESYNC
        Phase 3: REASONINGSTACK.yaml
        Phase 4: Reference files, profiles, commands, features

    This function assumes:
        - YAML is executed via the existing governance tooling (e.g., a
          runner script or `gmp` / `rules` command).
    """
    if yaml_path is None:
        yaml_path = workspace_root / ".cursor-commands" / "setup-new-workspace.yaml"

    if not yaml_path.exists():
        msg = f"setup-new-workspace.yaml not found at {yaml_path}"
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg

    # Preferred execution: via existing `rules` / `gmp` tooling if present.
    # Fallback: call a generic runner script if one exists.
    # Here we provide a conservative default: call `python -m yaml_runner`-style,
    # but keep it DRY-RUN safe so it can be wired to the actual runner later.

    cmd_hint = f"[MANUAL STEP] Execute governance orchestrator for {yaml_path}"
    if dry_run:
        _log(
            f"[DRY RUN] Would invoke workspace orchestrator for {yaml_path}. "
            f"{cmd_hint}",
            verbose=verbose,
        )
        return True, {"yaml": str(yaml_path), "hint": cmd_hint}, ""
    else:
        # If you have a concrete runner (e.g., `.cursor-commands/ops/scripts/workspace-orchestrator.py`),
        # replace this block with a real subprocess call.
        _log(
            "No automatic YAML runner is wired in this script to avoid "
            "guesswork. Please execute the configured orchestrator "
            f"for {yaml_path} (e.g., via `/rules` or `gmp`).",
            level="WARNING",
            verbose=verbose,
        )
        return True, {"yaml": str(yaml_path), "hint": cmd_hint}, ""


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def start_new_workspace(
    *,
    workspace_root: Path,
    dry_run: bool,
    verbose: bool,
    force_resymlink: bool,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    High-level entrypoint:
        1. Ensure `.cursor-commands` symlink to GlobalCommands.
        2. Run env-manager to sync `.suite6-config.json`.
        3. Invoke `setup-new-workspace.yaml` orchestrator.

    Returns:
        (success, data, error)
    """
    data: Dict[str, Any] = {}

    _log(
        f"Starting new/updated workspace initialization at {workspace_root}",
        verbose=verbose,
    )

    # Step 1: Symlink
    ok, d, err = ensure_cursor_commands_symlink(
        workspace_root=workspace_root,
        dry_run=dry_run,
        verbose=verbose,
        force_resymlink=force_resymlink,
    )
    data["symlink"] = d
    if not ok:
        return False, data, err

    # Step 2: env-manager
    ok, d, err = run_env_manager(
        workspace_root=workspace_root,
        dry_run=dry_run,
        verbose=verbose,
    )
    data["env_manager"] = d
    if not ok:
        return False, data, err

    # Step 3: setup-new-workspace.yaml
    ok, d, err = run_setup_new_workspace_yaml(
        workspace_root=workspace_root,
        yaml_path=None,
        dry_run=dry_run,
        verbose=verbose,
    )
    data["setup_new_workspace"] = d
    if not ok:
        return False, data, err

    _log("Workspace initialization sequence completed (or staged in dry-run).", verbose=verbose)
    return True, data, ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Start or upgrade a Cursor Governance workspace by wiring the "
            ".cursor-commands symlink, syncing configuration, and invoking "
            "setup-new-workspace.yaml phases."
        )
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Workspace root directory (default: current directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )
    parser.add_argument(
        "--force-resymlink",
        action="store_true",
        help="Force re-creation of .cursor-commands symlink even if it exists.",
    )

    args = parser.parse_args()
    workspace_root = Path(args.root).resolve()

    logger.info("=" * 70)
    logger.info("Cursor Governance — start-new-workspace")
    logger.info("Suite 6 v9.0.0 — Spaces Pack EntryPoint")
    logger.info("=" * 70)
    logger.info(f"Workspace root: {workspace_root}")
    if args.dry_run:
        logger.info("MODE: DRY RUN (no changes will be written)")
    logger.info("")

    success, data, error = start_new_workspace(
        workspace_root=workspace_root,
        dry_run=bool(args.dry_run),
        verbose=bool(args.verbose or args.dry_run),
        force_resymlink=bool(args.force_resymlink),
    )

    if success:
        _log("start-new-workspace completed successfully.", verbose=True)
        if args.verbose:
            _log(f"Details: {data}", verbose=True)
        return 0
    else:
        _log(f"start-new-workspace FAILED: {error}", level="ERROR", verbose=True)
        if args.verbose and data:
            _log(f"Partial data: {data}", level="ERROR", verbose=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
