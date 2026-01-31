"""
L9 CA Governance - Diff Generator
==================================
Generates clean, reviewable diffs for code changes proposed by CA (Coding Agent).

Part of the DevLayer governance system that ensures all code changes are:
- Tracked with full diffs
- Reviewable by humans
- Compliant with file editing constraints

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

import difflib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FileDiff:
    """Represents a diff for a single file."""

    file_path: str
    diff: str
    lines_added: int
    lines_removed: int
    is_new_file: bool
    is_deleted: bool = False
    similarity_ratio: float = 1.0


@dataclass
class BatchDiff:
    """Represents diffs for multiple files."""

    diffs: list[FileDiff]
    summary: dict[str, int]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DiffGenerator:
    """Generate diffs for code changes."""

    def __init__(self, repo_root: Path | None = None):
        """
        Initialize diff generator.

        Args:
            repo_root: Root directory of the repository (defaults to current dir)
        """
        self.repo_root = repo_root or Path.cwd()

    def generate_diff(self, file_path: str, original: str, modified: str) -> FileDiff:
        """
        Generate a unified diff for a single file.

        Args:
            file_path: Path to the file (relative to repo root)
            original: Original file content
            modified: Modified file content

        Returns:
            FileDiff object with diff and metadata
        """
        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm="",
            )
        )

        # Count additions and deletions
        lines_added = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        lines_removed = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        # Check if file is new
        full_path = self.repo_root / file_path
        is_new_file = not full_path.exists()

        # Calculate similarity ratio (for detecting file recreation)
        similarity_ratio = difflib.SequenceMatcher(None, original, modified).ratio()

        # Check if file is being deleted
        is_deleted = len(modified.strip()) == 0 and len(original.strip()) > 0

        return FileDiff(
            file_path=file_path,
            diff="".join(diff_lines),
            lines_added=lines_added,
            lines_removed=lines_removed,
            is_new_file=is_new_file,
            is_deleted=is_deleted,
            similarity_ratio=similarity_ratio,
        )

    def generate_batch_diff(self, changes: list[dict]) -> BatchDiff:
        """
        Generate diffs for multiple file changes.

        Args:
            changes: List of dicts with keys: file_path, original, modified

        Returns:
            BatchDiff object with all diffs and summary
        """
        diffs = []
        total_added = 0
        total_removed = 0
        new_files = 0
        deleted_files = 0

        for change in changes:
            diff = self.generate_diff(
                change["file_path"],
                change.get("original", ""),
                change.get("modified", ""),
            )
            diffs.append(diff)
            total_added += diff.lines_added
            total_removed += diff.lines_removed
            if diff.is_new_file:
                new_files += 1
            if diff.is_deleted:
                deleted_files += 1

        summary = {
            "files_changed": len(diffs),
            "total_lines_added": total_added,
            "total_lines_removed": total_removed,
            "new_files": new_files,
            "deleted_files": deleted_files,
        }

        return BatchDiff(diffs=diffs, summary=summary)

    def format_for_review(self, batch_diff: BatchDiff) -> str:
        """
        Format batch diff as markdown for human review.

        Args:
            batch_diff: BatchDiff object

        Returns:
            Markdown-formatted diff
        """
        output = ["# Code Change Review\n"]
        output.append(f"**Generated:** {batch_diff.timestamp}\n\n")
        output.append("## Summary\n")
        output.append(f"- **Files Changed:** {batch_diff.summary['files_changed']}\n")
        output.append(
            f"- **Lines Added:** +{batch_diff.summary['total_lines_added']}\n"
        )
        output.append(
            f"- **Lines Removed:** -{batch_diff.summary['total_lines_removed']}\n"
        )

        if batch_diff.summary["new_files"] > 0:
            output.append(f"- **New Files:** {batch_diff.summary['new_files']}\n")
        if batch_diff.summary["deleted_files"] > 0:
            output.append(
                f"- **Deleted Files:** {batch_diff.summary['deleted_files']}\n"
            )

        output.append("\n---\n\n")

        # Add individual file diffs
        for diff in batch_diff.diffs:
            status = (
                "NEW"
                if diff.is_new_file
                else "DELETED"
                if diff.is_deleted
                else "MODIFIED"
            )
            output.append(f"## {diff.file_path} [{status}]\n")

            if diff.similarity_ratio < 0.3:
                output.append(
                    "⚠️ **Warning:** File appears to be recreated (low similarity)\n\n"
                )

            output.append("```diff\n")
            output.append(diff.diff)
            output.append("\n```\n\n")

        return "".join(output)

    def format_for_git(self, batch_diff: BatchDiff) -> str:
        """
        Format batch diff as git-compatible patch.

        Args:
            batch_diff: BatchDiff object

        Returns:
            Git patch format
        """
        output = []
        for diff in batch_diff.diffs:
            output.append(diff.diff)
            output.append("\n")
        return "".join(output)

    def save_diff(self, batch_diff: BatchDiff, output_path: Path):
        """
        Save diff to file.

        Args:
            batch_diff: BatchDiff object
            output_path: Path to save the diff
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.format_for_review(batch_diff))
