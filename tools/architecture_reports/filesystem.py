from __future__ import annotations

from pathlib import Path
from typing import TextIO


def ensure_reports_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def open_report(path: Path) -> TextIO:
    ensure_reports_dir(path.parent)
    # Overwrite atomically via write-then-replace if needed; here we keep simple.
    return path.open("w", encoding="utf-8")
