#!/usr/bin/env python3
"""
Workflow State Updater — Automated workflow_state.md injection.

Usage:
    python scripts/workflow/update_workflow_state.py pr-start --pr 50 --title "Remove Anti-Pattern Violations"
    python scripts/workflow/update_workflow_state.py pr-complete --pr 50 --gmp 115 --adopted 5 --skipped 3 --realigned 2
    python scripts/workflow/update_workflow_state.py gmp-start --gmp 115 --title "PR #50 Analysis"
    python scripts/workflow/update_workflow_state.py gmp-complete --gmp 115 --status pass

Part of /pr and /gmp slash command automation.
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

__dora_meta__ = {
    "module_id": "scripts.workflow.update_workflow_state",
    "stability": "stable",
    "api_version": "1.0.0",
}


WORKFLOW_STATE_PATH = Path(__file__).parent.parent.parent / "workflow_state.md"


def get_current_date() -> str:
    """Get current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def read_workflow_state() -> str:
    """Read current workflow_state.md content."""
    if not WORKFLOW_STATE_PATH.exists():
        raise FileNotFoundError(f"workflow_state.md not found at {WORKFLOW_STATE_PATH}")
    return WORKFLOW_STATE_PATH.read_text()


def write_workflow_state(content: str) -> None:
    """Write updated content to workflow_state.md."""
    WORKFLOW_STATE_PATH.write_text(content)
    print(f"✅ Updated: {WORKFLOW_STATE_PATH}")


def inject_recent_change(content: str, entry: str) -> str:
    """
    Inject an entry into the 'Recent Changes (digest)' section.
    Entries are added at the TOP of the section (newest first).
    """
    marker = "## Recent Changes (digest)"

    if marker not in content:
        print(f"⚠️  Section '{marker}' not found")
        return content

    # Find position after marker and after "Full history:" line
    marker_pos = content.find(marker)
    after_marker = content[marker_pos:]

    # Find the first actual entry line (starts with "- [")
    lines = after_marker.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("- ["):
            insert_idx = i
            break

    if insert_idx is None:
        # No existing entries, add after marker + empty line
        insert_idx = 2

    # Insert new entry
    lines.insert(insert_idx, entry)

    # Reconstruct content
    new_after_marker = "\n".join(lines)
    return content[:marker_pos] + new_after_marker


def inject_next_steps_pr(
    content: str, pr_num: int, title: str, status: str = "ANALYZING"
) -> str:
    """
    Inject or update a PR entry in 'Next Steps (Current Session)' section.
    """
    marker = "## Next Steps (Current Session)"

    if marker not in content:
        print(f"⚠️  Section '{marker}' not found")
        return content

    get_current_date()

    # Check if PR already has an entry
    pr_pattern = rf"### .* PR #{pr_num}\b"
    if re.search(pr_pattern, content):
        # Update existing entry status
        content = re.sub(
            rf"(### .* PR #{pr_num}.*?)(\n###|\n##|\Z)",
            lambda m: m.group(1)
            .replace("ANALYZING", status)
            .replace("🟡", "🟢" if status == "COMPLETED" else "🟡")
            + m.group(2),
            content,
            flags=re.DOTALL,
        )
    else:
        # Add new entry
        entry = f"""
### 🟡 ANALYZING: PR #{pr_num} — {title}
**Status:** Phase 0 TODO — Awaiting user confirmation
**Report:** `reports/GMP-Report-XXX-PR{pr_num}-{title.replace(" ", "-")}.md` (pending)
**Action:** Review YNP analysis, confirm or modify, then proceed
"""
        # Find marker position
        marker_pos = content.find(marker)
        # Find next section or end
        after_marker = content[marker_pos + len(marker) :]
        next_section = re.search(r"\n## ", after_marker)

        if next_section:
            insert_pos = marker_pos + len(marker) + next_section.start()
        else:
            insert_pos = len(content)

        content = content[:insert_pos] + entry + content[insert_pos:]

    return content


def inject_recent_session(content: str, entry: str) -> str:
    """
    Inject an entry into 'Recent Sessions (7-day window)'.
    Entries are added at the TOP (newest first).
    """
    marker = "**Recent Sessions (7-day window):**"

    if marker not in content:
        print(f"⚠️  Section '{marker}' not found")
        return content

    marker_pos = content.find(marker)
    after_marker = content[marker_pos + len(marker) :]

    # Find first "- " line
    lines = after_marker.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("- "):
            insert_idx = i
            break

    if insert_idx is None:
        insert_idx = 1  # After marker

    lines.insert(insert_idx, entry)

    new_after_marker = "\n".join(lines)
    return content[: marker_pos + len(marker)] + new_after_marker


def mark_session_complete(content: str, pr_num: int) -> str:
    """Mark a PR session entry as complete with ✅."""
    # Find the session entry for this PR
    pattern = rf"(- \d{{4}}-\d{{2}}-\d{{2}}: .*PR #{pr_num}.*)"
    match = re.search(pattern, content)

    if match and not match.group(1).startswith("- ✅"):
        content = content.replace(
            match.group(1), match.group(1).replace("- ", "- ✅ ", 1)
        )

    return content


def cmd_pr_start(args):
    """Handle /pr command start — inject Phase 0 TODO entry."""
    content = read_workflow_state()
    date = get_current_date()

    # 1. Add to Recent Changes
    change_entry = f"- [{date}] **PR #{args.pr} Analysis Started** — `/pr` Phase 0 TODO: {args.title}. Awaiting user confirmation."
    content = inject_recent_change(content, change_entry)

    # 2. Add to Next Steps
    content = inject_next_steps_pr(content, args.pr, args.title, "ANALYZING")

    # 3. Add to Recent Sessions
    session_entry = f"- {date}: **PR #{args.pr} Analysis** — `/pr` initiated. Phase 0 TODO pending user YNP confirmation."
    content = inject_recent_session(content, session_entry)

    write_workflow_state(content)
    print(f"📝 PR #{args.pr} analysis entry added to workflow_state.md")


def cmd_pr_complete(args):
    """Handle /pr command completion — update entries with results."""
    content = read_workflow_state()
    date = get_current_date()

    # 1. Update Recent Changes with completion
    change_entry = f"- [{date}] **GMP-{args.gmp}: PR #{args.pr} Analysis Complete** — Adopted: {args.adopted}, Skipped: {args.skipped}, Realigned: {args.realigned}. Report: `reports/GMP-Report-{args.gmp}-PR{args.pr}-*.md`"
    content = inject_recent_change(content, change_entry)

    # 2. Update Next Steps status
    content = inject_next_steps_pr(content, args.pr, "", "COMPLETED")

    # 3. Mark session as complete
    content = mark_session_complete(content, args.pr)

    write_workflow_state(content)
    print(f"✅ PR #{args.pr} marked complete in workflow_state.md")


def cmd_gmp_start(args):
    """Handle /gmp command start."""
    content = read_workflow_state()
    date = get_current_date()

    change_entry = f"- [{date}] **GMP-{args.gmp} Started** — {args.title}"
    content = inject_recent_change(content, change_entry)

    write_workflow_state(content)
    print(f"📝 GMP-{args.gmp} start entry added")


def cmd_gmp_complete(args):
    """Handle /gmp command completion."""
    content = read_workflow_state()
    date = get_current_date()

    status_icon = "✅" if args.status == "pass" else "❌"
    change_entry = f"- [{date}] **{status_icon} GMP-{args.gmp} Complete** — Status: {args.status.upper()}. Report: `reports/GMP-Report-{args.gmp}-*.md`"
    content = inject_recent_change(content, change_entry)

    write_workflow_state(content)
    print(f"✅ GMP-{args.gmp} completion entry added")


def main():
    """
    Performs command-line argument parsing for the Workflow State Updater tool, setting up subcommands and options for managing workflow states.



    Raises:
        argparse.ArgumentError: If argument parsing encounters invalid input.
    """
    parser = argparse.ArgumentParser(description="Workflow State Updater")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # pr-start command
    pr_start = subparsers.add_parser("pr-start", help="Start PR analysis")
    pr_start.add_argument("--pr", type=int, required=True, help="PR number")
    pr_start.add_argument("--title", required=True, help="PR title")

    # pr-complete command
    pr_complete = subparsers.add_parser("pr-complete", help="Complete PR analysis")
    pr_complete.add_argument("--pr", type=int, required=True, help="PR number")
    pr_complete.add_argument("--gmp", type=int, required=True, help="GMP report number")
    pr_complete.add_argument("--adopted", type=int, default=0, help="Files adopted")
    pr_complete.add_argument("--skipped", type=int, default=0, help="Files skipped")
    pr_complete.add_argument("--realigned", type=int, default=0, help="Files realigned")

    # gmp-start command
    gmp_start = subparsers.add_parser("gmp-start", help="Start GMP execution")
    gmp_start.add_argument("--gmp", type=int, required=True, help="GMP number")
    gmp_start.add_argument("--title", required=True, help="GMP title")

    # gmp-complete command
    gmp_complete = subparsers.add_parser("gmp-complete", help="Complete GMP execution")
    gmp_complete.add_argument("--gmp", type=int, required=True, help="GMP number")
    gmp_complete.add_argument(
        "--status", choices=["pass", "fail"], default="pass", help="GMP status"
    )

    args = parser.parse_args()

    if args.command == "pr-start":
        cmd_pr_start(args)
    elif args.command == "pr-complete":
        cmd_pr_complete(args)
    elif args.command == "gmp-start":
        cmd_gmp_start(args)
    elif args.command == "gmp-complete":
        cmd_gmp_complete(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-081",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["cli", "filesystem", "operations", "scripts"],
    "keywords": [
        "change",
        "cmd",
        "complete",
        "current",
        "date",
        "gmp",
        "inject",
        "mark",
    ],
    "business_value": "Utility module for update workflow state",
    "last_modified": "2026-01-31T22:21:56Z",
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
