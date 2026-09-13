from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class RepoLayout:
    """
    Represents the layout configuration of a repository, including key directory paths.

    Args:
        root: The root directory of the repository.
        src_dirs: Tuple of source code directories within the repo.
        api_dirs: Tuple of API directories in the repo.
        config_dirs: Tuple of configuration directories.
        reports_dir: Directory designated for reports.
    """

    root: Path
    src_dirs: tuple[Path, ...]
    api_dirs: tuple[Path, ...]
    config_dirs: tuple[Path, ...]
    reports_dir: Path


def detect_root(start: Path | None = None) -> Path:
    """Resolve repo root as the directory containing pyproject.toml.

    Raises:
        RuntimeError: if pyproject.toml is not found walking upwards.
    """
    current = (start or Path(__file__)).resolve()
    for parent in (current, *tuple(current.parents)):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Unable to locate repo root (pyproject.toml not found).")


def default_layout() -> RepoLayout:
    """
    Returns the default project layout based on the detected root directory.


    Returns:
        A RepoLayout object representing the standard directory structure for the repository.
    """
    root = detect_root()
    src_dirs: tuple[Path, ...] = (
        root / "core",
        root / "services",
        root / "orchestrators",
        root / "api",
        root / "workers",
        root / "memory",
        root / "world_model",
        root / "ir_engine",
        root / "graph_adapter",
        root / "domain_bridge",
    )
    api_dirs: tuple[Path, ...] = (root / "api",)
    config_dirs: tuple[Path, ...] = (
        root / "config",
        root / "deploy",
        root / "docker",
    )
    reports_dir = root / "reports" / "architecture"
    return RepoLayout(
        root=root,
        src_dirs=src_dirs,
        api_dirs=api_dirs,
        config_dirs=config_dirs,
        reports_dir=reports_dir,
    )


def iter_python_files(dirs: Iterable[Path]) -> Iterable[Path]:
    """Yield all .py files under the given directories, excluding __pycache__."""
    for base in dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


# Runtime execution trace - updated automatically on every execution
