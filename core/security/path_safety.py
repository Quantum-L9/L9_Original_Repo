"""
Path safety utilities for sandboxed filesystem access.

Provides allowlist-rooted path resolution with normalization, traversal
defenses, and async-compatible helpers for auditability.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Path Safety",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-12T22:08:42Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "path_safety",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.routes.factory",
            "scripts.research.factory_extract",
            "tests.core.security.test_path_safety",
        ],
    },
}
# ============================================================================

import os
import re
import stat
import unicodedata
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from core.decorators import must_stay_async

_ABSOLUTE_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_UNC_PREFIXES = ("\\\\", "//")


@dataclass
class PathSafetyError(ValueError):
    """Raised when a user-controlled path fails safety validation."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        return f"{self.code}: {self.message}"


def resolve_base_dir(
    env_var: str = "L9_RESEARCH_FACTORY_BASE_DIR",
    fallback_subdir: str = "generated",
) -> Path:
    """Resolve a base directory from env or fall back to app data."""
    env_value = os.getenv(env_var)
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path.home() / ".l9" / fallback_subdir).resolve()


def safe_resolve_path(
    root: Path,
    user_path: str,
    *,
    follow_symlinks: bool = False,
    allow_abs: bool = False,
    max_length: int = 4096,
    max_parts: int = 128,
) -> Path:
    """Resolve a user-supplied path under a sandbox root.

    This rejects absolute paths, traversal tokens, UNC/drive prefixes,
    percent-encoded separators, NUL bytes, and surrogate code points.
    """
    normalized = _normalize_user_path(user_path, max_length=max_length)
    if _is_absolute_like(normalized) and not allow_abs:
        raise PathSafetyError("absolute_path", "Absolute paths are not allowed")

    parts = _split_parts(normalized)
    if not parts:
        raise PathSafetyError("empty_path", "Path must not be empty")
    if len(parts) > max_parts:
        raise PathSafetyError("too_many_segments", "Path has too many segments")
    if _has_traversal(parts):
        raise PathSafetyError("path_traversal", "Traversal segments are not allowed")
    if _contains_tilde(parts):
        raise PathSafetyError("tilde_path", "Tilde expansion is not allowed")

    root_resolved = root.resolve()
    candidate = _join_candidate(root_resolved, normalized, parts, allow_abs=allow_abs)
    rel_parts = parts
    if candidate.is_absolute():
        try:
            rel_parts = candidate.relative_to(root_resolved).parts
        except ValueError as exc:
            raise PathSafetyError(
                "path_escape", "Resolved path escapes sandbox root"
            ) from exc

    if not follow_symlinks:
        _ensure_no_symlink(root_resolved, rel_parts)

    resolved = candidate.resolve(strict=False) if follow_symlinks else candidate
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSafetyError(
            "path_escape", "Resolved path escapes sandbox root"
        ) from exc
    return resolved


@must_stay_async("callers use await")
async def safe_resolve_path_async(
    root: Path,
    user_path: str,
    *,
    follow_symlinks: bool = False,
    allow_abs: bool = False,
    max_length: int = 4096,
    max_parts: int = 128,
) -> Path:
    """Async-compatible wrapper for safe_resolve_path."""
    return safe_resolve_path(
        root,
        user_path,
        follow_symlinks=follow_symlinks,
        allow_abs=allow_abs,
        max_length=max_length,
        max_parts=max_parts,
    )


def validate_filename(
    name: str,
    *,
    max_length: int = 255,
    allow_dotfiles: bool = False,
) -> str:
    """Validate a filename-only input (no separators, no traversal)."""
    normalized = _normalize_user_path(name, max_length=max_length)
    if _is_absolute_like(normalized):
        raise PathSafetyError("absolute_path", "Absolute paths are not allowed")
    if "/" in normalized or "\\" in normalized:
        raise PathSafetyError("path_separator", "Path separators are not allowed")
    if normalized in {".", "..", ""}:
        raise PathSafetyError("empty_path", "Filename must not be empty")
    if not allow_dotfiles and normalized.startswith("."):
        raise PathSafetyError("dotfile", "Dotfiles are not allowed")
    if normalized != normalized.rstrip(" ."):
        raise PathSafetyError("trailing_chars", "Trailing dots/spaces are not allowed")
    if _has_control_chars(normalized):
        raise PathSafetyError("control_chars", "Control characters are not allowed")
    if _is_windows_reserved(normalized):
        raise PathSafetyError("reserved_name", "Reserved Windows name is not allowed")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
        raise PathSafetyError("invalid_chars", "Filename contains invalid characters")
    return normalized


def _normalize_user_path(raw: str, *, max_length: int) -> str:
    if not isinstance(raw, str):
        raise PathSafetyError("invalid_type", "Path must be a string")
    if "\x00" in raw:
        raise PathSafetyError("nul_byte", "NUL bytes are not allowed")
    if len(raw) > max_length:
        raise PathSafetyError("too_long", "Path exceeds maximum length")

    stripped = _strip_zero_width(raw)
    decoded = unquote(stripped)
    normalized = unicodedata.normalize("NFC", decoded)
    if _contains_surrogates(normalized):
        raise PathSafetyError("surrogate", "Surrogate code points are not allowed")
    if _has_control_chars(normalized):
        raise PathSafetyError("control_chars", "Control characters are not allowed")
    return normalized


def _contains_surrogates(value: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)


def _is_absolute_like(value: str) -> bool:
    if value.startswith(("/", "\\")):
        return True
    if value.startswith(_UNC_PREFIXES):
        return True
    return _ABSOLUTE_DRIVE_RE.match(value) is not None


def _split_parts(value: str) -> list[str]:
    return [part for part in re.split(r"[\\/]+", value) if part != ""]


def _has_traversal(parts: Iterable[str]) -> bool:
    return any(part in {".", ".."} for part in parts)


def _contains_tilde(parts: Iterable[str]) -> bool:
    return any(part.startswith("~") for part in parts)


def _join_candidate(
    root: Path, normalized: str, parts: list[str], *, allow_abs: bool
) -> Path:
    if _is_absolute_like(normalized):
        candidate = Path(normalized)
        if not allow_abs:
            raise PathSafetyError("absolute_path", "Absolute paths are not allowed")
        return candidate
    return root.joinpath(*parts)


def _strip_zero_width(value: str) -> str:
    return re.sub(r"[\u200B-\u200D\uFEFF]", "", value)


def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 for ch in value)


def _is_windows_reserved(value: str) -> bool:
    stem = value.split(".", 1)[0]
    if not stem:
        return False
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    return stem.upper() in reserved


def _ensure_no_symlink(root: Path, parts: Iterable[str]) -> None:
    if _has_dir_fd_support():
        _ensure_no_symlink_dirfd(root, parts)
        return
    _ensure_no_symlink_fallback(root, parts)


def _has_dir_fd_support() -> bool:
    if not (hasattr(os, "open") and hasattr(os, "stat") and hasattr(os, "O_RDONLY")):
        return False
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    return os.stat in supports_dir_fd and os.open in supports_dir_fd


def _ensure_no_symlink_dirfd(root: Path, parts: Iterable[str]) -> None:
    try:
        with _open_dir_fd(root) as root_fd:
            current_fd = root_fd
            try:
                for part in parts:
                    try:
                        stat_result = os.stat(
                            part, dir_fd=current_fd, follow_symlinks=False
                        )
                    except FileNotFoundError:
                        return
                    if stat.S_ISLNK(stat_result.st_mode):
                        raise PathSafetyError("symlink", "Symlinks are not permitted")
                    if not stat.S_ISDIR(stat_result.st_mode):
                        return
                    next_fd = os.open(part, _dir_open_flags(), dir_fd=current_fd)
                    if current_fd != root_fd:
                        os.close(current_fd)
                    current_fd = next_fd
            finally:
                if current_fd != root_fd:
                    os.close(current_fd)
    except (NotImplementedError, OSError, AttributeError):
        _ensure_no_symlink_fallback(root, parts)


def _ensure_no_symlink_fallback(root: Path, parts: Iterable[str]) -> None:
    current = root
    for part in parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PathSafetyError("symlink", "Symlinks are not permitted")


@contextmanager
def _open_dir_fd(path: Path) -> Iterator[int]:
    fd = os.open(path, _dir_open_flags())
    try:
        yield fd
    finally:
        os.close(fd)


def _dir_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-026",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "audit-tool",
        "core",
        "dataclass",
        "filesystem",
        "foundation",
        "messaging",
    ],
    "keywords": ["async", "dir", "filename", "resolve", "safe", "safety", "validate"],
    "business_value": "Provides allowlist-rooted path resolution with normalization, traversal defenses, and async-compatible helpers for auditability.",
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
