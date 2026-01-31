from __future__ import annotations

from pathlib import Path
from typing import TextIO


def ensure_reports_dir(path: Path) -> None:
    """
    Ensures that the reports directory exists at the specified path to facilitate report file creation.
    Args:
        path: Path object representing the directory where reports should be stored.
    """
    path.mkdir(parents=True, exist_ok=True)


def open_report(path: Path) -> TextIO:
    """
    Performs setup and opens a report file for writing within the filesystem report management context.

    Args:
        path: Path to the report file to be created or overwritten.

    Returns:
        A writable text stream for the specified report file.

    Raises:
        OSError: If the directory creation or file opening fails.
    """
    ensure_reports_dir(path.parent)
    # Overwrite atomically via write-then-replace if needed; here we keep simple.
    return path.open("w", encoding="utf-8")
