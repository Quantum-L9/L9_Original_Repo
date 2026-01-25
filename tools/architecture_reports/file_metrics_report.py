from __future__ import annotations

from dataclasses import dataclass

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


@dataclass
class FileMetrics:
    rel_path: str
    loc: int
    complexity: int


def _compute_loc(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def _compute_complexity(text: str) -> int:
    """Very rough cyclomatic complexity heuristic."""
    keywords = ("if ", "for ", "while ", "and ", "or ", "elif ", "except ", "with ")
    complexity = 1
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        complexity += sum(1 for kw in keywords if kw in stripped)
    return complexity


def generate_file_metrics(layout: RepoLayout) -> None:
    """Generate file_metrics.txt with LOC and complexity per Python file."""
    output = layout.reports_dir / "file_metrics.txt"
    metrics: list[FileMetrics] = []

    for path in iter_python_files(layout.src_dirs):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        loc = _compute_loc(text)
        complexity = _compute_complexity(text)
        rel = path.relative_to(layout.root).as_posix()
        metrics.append(FileMetrics(rel, loc, complexity))

    metrics.sort(key=lambda m: m.loc, reverse=True)

    with open_report(output) as f:
        for m in metrics:
            f.write(f"{m.rel_path}  LOC={m.loc}  complexity={m.complexity}\n")
