from __future__ import annotations

from .config import RepoLayout
from .filesystem import open_report

_CONFIG_EXT = {".yml", ".yaml", ".toml", ".ini", ".json", ".env", ".cfg"}


def generate_config_files(layout: RepoLayout) -> None:
    """Generate config_files.txt listing config-like files and their paths."""
    output = layout.reports_dir / "config_files.txt"

    entries: list[str] = []

    for base in layout.config_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in _CONFIG_EXT:
                entries.append(path.relative_to(layout.root).as_posix())

    # top-level configs
    for name in (
        "pyproject.toml",
        "pytest.ini",
        "codecov.yml",
        "sonar-project.properties",
    ):
        path = layout.root / name
        if path.is_file():
            entries.append(path.relative_to(layout.root).as_posix())

    entries.sort()

    with open_report(output) as f:
        for rel in entries:
            f.write(f"{rel}\n")
