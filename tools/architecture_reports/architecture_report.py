from __future__ import annotations



from typing import TYPE_CHECKING

from .filesystem import open_report

if TYPE_CHECKING:
    from pathlib import Path

    from .config import RepoLayout


def generate_architecture(layout: RepoLayout) -> None:
    """Generate a high-level architecture outline into architecture.txt."""
    output = layout.reports_dir / "architecture.txt"
    with open_report(output) as f:
        f.write("L9 Architecture Overview\n")
        f.write("========================\n\n")
        f.write(f"Repo root: {layout.root}\n\n")

        sections: list[tuple[str, Path]] = [
            ("CORE", layout.root / "core"),
            ("SERVICES", layout.root / "services"),
            ("ORCHESTRATORS", layout.root / "orchestrators"),
            ("API", layout.root / "api"),
            ("WORKERS", layout.root / "workers"),
            ("MEMORY", layout.root / "memory"),
            ("WORLD MODEL", layout.root / "world_model"),
            ("IR ENGINE", layout.root / "ir_engine"),
            ("GRAPH ADAPTER", layout.root / "graph_adapter"),
            ("DOMAIN TENSOR BRIDGE", layout.root / "domain_bridge"),
        ]

        for title, base in sections:
            f.write(f"[{title}]\n")
            if not base.exists():
                f.write(f"  (missing: {base})\n\n")
                continue
            for path in sorted(base.rglob("*.py")):
                rel = path.relative_to(layout.root)
                f.write(f"  {rel}\n")
            f.write("\n")


# Runtime execution trace - updated automatically on every execution
