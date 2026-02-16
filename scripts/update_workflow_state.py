#!/usr/bin/env python3
"""
update_workflow_state.py — Append GMP completion entry to workflow_state.md
==========================================================================

Single responsibility: insert a dated entry into the "Recent Changes (digest)"
section of workflow_state.md.  No regex gymnastics — finds the marker line,
inserts after it, writes back.

Usage:
    python scripts/update_workflow_state.py \
        --gmp-id 142 \
        --task "DRY Config Migration" \
        --summary "Migrated 8 files to config_constants.py" \
        --files "core/config_constants.py,memory/governance_gate.py"

    # Or pipe from generate_gmp_report.py:
    python scripts/update_workflow_state.py --from-report reports/GMP-Report-142-Foo.md
"""

__dora_meta__ = {
    "component_name": "Update Workflow State",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-13T19:00:00Z",
    "updated_at": "2026-02-13T19:00:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "update_workflow_state",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.gmp.nodes.core"],
    },
}

import argparse
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(os.getenv("L9_REPO_ROOT", Path(__file__).parent.parent))
WORKFLOW_STATE = REPO_ROOT / "workflow_state.md"
MARKER = "## Recent Changes (digest)"


def build_entry(
    gmp_id: int | str,
    task: str,
    summary: str,
    files: list[str] | None = None,
    report_path: str | None = None,
) -> str:
    """Build a single workflow_state entry line."""
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    gmp_label = f"GMP-{int(gmp_id):03d}" if str(gmp_id).isdigit() else str(gmp_id)

    entry = f"- [{date_str}] **{gmp_label}: {task}**"

    if summary:
        entry += f" — {summary.rstrip('.')}"

    if files:
        short = ", ".join(Path(f).name for f in files[:4])
        if len(files) > 4:
            short += f" (+{len(files) - 4} more)"
        entry += f". Files: {short}"

    if report_path:
        entry += f". Report: `{Path(report_path).name}`"

    return entry


def extract_from_report(report_path: Path) -> dict:
    """Extract GMP metadata from a generated report file."""
    content = report_path.read_text(encoding="utf-8")

    gmp_id = ""
    task = ""
    summary = ""
    files: list[str] = []

    # Try header patterns
    id_match = re.search(r"\*\*(?:GMP )?ID:\*\*\s*GMP-(\d+)", content)
    if id_match:
        gmp_id = id_match.group(1)

    task_match = re.search(r"\*\*(?:Title|Task):\*\*\s*(.+?)(?:\s*\||\n)", content)
    if task_match:
        task = task_match.group(1).strip()

    # Fallback: extract from filename
    if not gmp_id:
        fname_match = re.match(r"GMP-Report-(\d+)-(.+)\.md", report_path.name)
        if fname_match:
            gmp_id = fname_match.group(1)
            if not task:
                task = fname_match.group(2).replace("-", " ")

    # Extract files from "Files Modified" section
    for m in re.finditer(r"`([a-zA-Z_/]+\.py)`", content):
        f = m.group(1)
        if f not in files and "/" in f:
            files.append(f)

    return {
        "gmp_id": gmp_id or "???",
        "task": task or "Unknown task",
        "summary": summary,
        "files": files[:6],
        "report_path": str(report_path),
    }


def update(entry: str) -> bool:
    """Insert entry into workflow_state.md after the Recent Changes marker."""
    if not WORKFLOW_STATE.exists():
        logger.error("workflow_state_not_found", path=str(WORKFLOW_STATE))
        return False

    lines = WORKFLOW_STATE.read_text(encoding="utf-8").splitlines()

    # Find the marker line
    marker_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith(MARKER):
            marker_idx = i
            break

    if marker_idx is None:
        logger.error("marker_not_found", marker=MARKER)
        return False

    # Insert after marker + any blank line
    insert_at = marker_idx + 1
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    lines.insert(insert_at, entry)

    WORKFLOW_STATE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("workflow_state_updated", entry=entry[:80])
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append GMP entry to workflow_state.md"
    )
    parser.add_argument("--gmp-id", help="GMP ID (number or string)")
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--summary", default="", help="One-line summary")
    parser.add_argument("--files", default="", help="Comma-separated file list")
    parser.add_argument("--report", help="Report file path")
    parser.add_argument(
        "--from-report",
        type=Path,
        help="Extract all fields from a generated report",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print entry only")

    args = parser.parse_args()

    if args.from_report:
        data = extract_from_report(args.from_report)
        entry = build_entry(
            gmp_id=data["gmp_id"],
            task=data["task"],
            summary=data["summary"],
            files=data["files"],
            report_path=data["report_path"],
        )
    elif args.gmp_id and args.task:
        file_list = [f.strip() for f in args.files.split(",") if f.strip()]
        entry = build_entry(
            gmp_id=args.gmp_id,
            task=args.task,
            summary=args.summary,
            files=file_list,
            report_path=args.report,
        )
    else:
        parser.error("Provide --gmp-id + --task, or --from-report")
        return 1

    if args.dry_run:
        print(entry)
        return 0

    return 0 if update(entry) else 1


if __name__ == "__main__":
    sys.exit(main())
