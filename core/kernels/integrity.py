"""
L9 Core Kernels - Integrity Verification
=========================================

Kernel hashing and tamper detection for L9 private kernels.

Features:
- SHA256 hashing of kernel YAML files
- Stored hash comparison for tamper detection
- Automatic hash updates on authorized changes
- Detailed change reporting (NEW, MODIFIED, DELETED)

Usage:
    from core.kernels.integrity import check_kernel_integrity

    changes = check_kernel_integrity("private")
    if changes:
        logger.info(f"Kernel files changed: {changes}")

Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import structlog
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

KERNEL_HASH_FILE = Path("private/kernel_hashes.json")
HASH_ALGORITHM = "sha256"
KERNEL_EXTENSIONS = (".yaml", ".yml")


# =============================================================================
# Hash Functions
# =============================================================================


def hash_file(path: Path) -> str:
    """
    Compute SHA256 hash of a file.

    Args:
        path: Path to file

    Returns:
        Hexadecimal hash string
    """
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (IOError, OSError) as e:
        logger.error(f"Failed to hash file {path}: {e}")
        raise


def compute_kernel_hashes(base_path: str = "private") -> Dict[str, str]:
    """
    Compute hashes for all kernel YAML files in a directory tree.

    Args:
        base_path: Base directory to scan

    Returns:
        Dict mapping file paths (relative) to their hashes
    """
    base = Path(base_path)
    hashes: Dict[str, str] = {}

    if not base.exists():
        logger.warning(f"Kernel base path does not exist: {base}")
        return hashes

    for ext in KERNEL_EXTENSIONS:
        for file in base.rglob(f"*{ext}"):
            try:
                relative_path = str(file.relative_to(Path.cwd()))
                hashes[relative_path] = hash_file(file)
            except Exception as e:
                logger.warning(f"Failed to hash {file}: {e}")

    logger.debug(f"Computed {len(hashes)} kernel hashes from {base_path}")
    return hashes


# =============================================================================
# Hash Storage
# =============================================================================


@lru_cache(maxsize=8)
def _load_kernel_hashes_cached(hash_file: Path) -> Dict[str, str]:
    """Internal cached implementation."""
    if not hash_file.exists():
        logger.info(f"No stored kernel hashes found at {hash_file}")
        return {}

    try:
        data = json.loads(hash_file.read_text())
        return data.get("hashes", {})
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load kernel hashes: {e}")
        return {}


def load_kernel_hashes(hash_file: Optional[Path] = None) -> Dict[str, str]:
    """
    Load stored kernel hashes from file. CACHED.

    Results are cached by file path. Call _load_kernel_hashes_cached.cache_clear()
    to invalidate after hash file updates.

    Args:
        hash_file: Path to hash file (defaults to KERNEL_HASH_FILE)

    Returns:
        Dict of stored hashes, empty dict if file doesn't exist
    """
    return _load_kernel_hashes_cached(hash_file or KERNEL_HASH_FILE)


def save_kernel_hashes(
    hashes: Dict[str, str],
    hash_file: Optional[Path] = None,
) -> None:
    """
    Save kernel hashes to file.

    Args:
        hashes: Dict of file paths to hashes
        hash_file: Path to hash file (defaults to KERNEL_HASH_FILE)
    """
    hash_file = hash_file or KERNEL_HASH_FILE

    # Ensure parent directory exists
    hash_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0.0",
        "algorithm": HASH_ALGORITHM,
        "updated_at": datetime.utcnow().isoformat(),
        "hashes": hashes,
    }

    try:
        hash_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved {len(hashes)} kernel hashes to {hash_file}")
    except (IOError, OSError) as e:
        logger.error(f"Failed to save kernel hashes: {e}")
        raise


# =============================================================================
# Integrity Checking
# =============================================================================


class IntegrityChange:
    """Represents a detected integrity change."""

    NEW = "NEW"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"

    def __init__(
        self,
        path: str,
        change_type: str,
        old_hash: Optional[str] = None,
        new_hash: Optional[str] = None,
    ):
        self.path = path
        self.change_type = change_type
        self.old_hash = old_hash
        self.new_hash = new_hash

    def __repr__(self) -> str:
        return f"IntegrityChange({self.path!r}, {self.change_type!r})"


def check_kernel_integrity(
    base_path: str = "private",
    auto_update: bool = True,
) -> Dict[str, str]:
    """
    Check integrity of kernel files against stored hashes.

    Compares current file hashes against stored hashes and reports:
    - NEW: Files that weren't in the stored hashes
    - MODIFIED: Files whose hash has changed
    - DELETED: Files that were in stored hashes but no longer exist

    Args:
        base_path: Base directory containing kernel files
        auto_update: Whether to automatically update stored hashes

    Returns:
        Dict mapping file paths to change type (NEW, MODIFIED, DELETED)
    """
    existing = load_kernel_hashes()
    current = compute_kernel_hashes(base_path)

    changes: Dict[str, str] = {}

    # Check for new and modified files
    for path, current_hash in current.items():
        if path not in existing:
            changes[path] = IntegrityChange.NEW
            logger.info(f"New kernel file detected: {path}")
        elif existing[path] != current_hash:
            changes[path] = IntegrityChange.MODIFIED
            logger.warning(f"Kernel file modified: {path}")

    # Check for deleted files
    for path in existing:
        if path not in current:
            changes[path] = IntegrityChange.DELETED
            logger.warning(f"Kernel file deleted: {path}")

    # Log summary
    if changes:
        new_count = sum(1 for c in changes.values() if c == IntegrityChange.NEW)
        mod_count = sum(1 for c in changes.values() if c == IntegrityChange.MODIFIED)
        del_count = sum(1 for c in changes.values() if c == IntegrityChange.DELETED)

        logger.info(
            f"Kernel integrity check: {new_count} new, "
            f"{mod_count} modified, {del_count} deleted"
        )

        # Update stored hashes if auto_update enabled
        if auto_update:
            save_kernel_hashes(current)
    else:
        logger.debug("Kernel integrity check passed: no changes detected")

    return changes


def get_detailed_changes(base_path: str = "private") -> List[IntegrityChange]:
    """
    Get detailed change information for kernel files.

    Args:
        base_path: Base directory containing kernel files

    Returns:
        List of IntegrityChange objects with full details
    """
    existing = load_kernel_hashes()
    current = compute_kernel_hashes(base_path)

    changes: List[IntegrityChange] = []

    # Check for new and modified files
    for path, current_hash in current.items():
        if path not in existing:
            changes.append(
                IntegrityChange(
                    path=path,
                    change_type=IntegrityChange.NEW,
                    old_hash=None,
                    new_hash=current_hash,
                )
            )
        elif existing[path] != current_hash:
            changes.append(
                IntegrityChange(
                    path=path,
                    change_type=IntegrityChange.MODIFIED,
                    old_hash=existing[path],
                    new_hash=current_hash,
                )
            )

    # Check for deleted files
    for path in existing:
        if path not in current:
            changes.append(
                IntegrityChange(
                    path=path,
                    change_type=IntegrityChange.DELETED,
                    old_hash=existing[path],
                    new_hash=None,
                )
            )

    return changes


def verify_specific_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Verify a specific kernel file against stored hash.

    Args:
        file_path: Path to file to verify

    Returns:
        Tuple of (is_valid, reason)
        - is_valid: True if file matches stored hash
        - reason: Description of result or mismatch
    """
    path = Path(file_path)

    if not path.exists():
        return False, "File does not exist"

    existing = load_kernel_hashes()
    relative_path = (
        str(path.relative_to(Path.cwd())) if path.is_absolute() else file_path
    )

    if relative_path not in existing:
        return False, "File not in stored hashes (may be new)"

    current_hash = hash_file(path)
    stored_hash = existing[relative_path]

    if current_hash == stored_hash:
        return True, "Hash matches"
    else:
        return (
            False,
            f"Hash mismatch: expected {stored_hash[:16]}..., got {current_hash[:16]}...",
        )


# =============================================================================
# Initialization
# =============================================================================


def initialize_kernel_hashes(base_path: str = "private", force: bool = False) -> int:
    """
    Initialize kernel hash file from current state.

    Use this to bootstrap the hash file on first setup or after
    authorized bulk changes.

    Args:
        base_path: Base directory containing kernel files
        force: Overwrite existing hashes even if file exists

    Returns:
        Number of files hashed
    """
    if KERNEL_HASH_FILE.exists() and not force:
        logger.warning(
            f"Hash file already exists at {KERNEL_HASH_FILE}. "
            f"Use force=True to overwrite."
        )
        return 0

    hashes = compute_kernel_hashes(base_path)
    save_kernel_hashes(hashes)

    logger.info(f"Initialized kernel hashes for {len(hashes)} files")
    return len(hashes)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "hash_file",
    "compute_kernel_hashes",
    "load_kernel_hashes",
    "save_kernel_hashes",
    "check_kernel_integrity",
    "get_detailed_changes",
    "verify_specific_file",
    "initialize_kernel_hashes",
    "IntegrityChange",
    "KERNEL_HASH_FILE",
]
