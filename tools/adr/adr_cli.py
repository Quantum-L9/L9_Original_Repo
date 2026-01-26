"""
ADR CLI - Command-line interface for managing Architecture Decision Records

Usage:
    python -m tools.adr new "Decision Title"
    python -m tools.adr list [--status STATUS] [--category CATEGORY]
    python -m tools.adr show ADR_ID
    python -m tools.adr update-status ADR_ID STATUS
    python -m tools.adr deprecate ADR_ID [--superseded-by ADR_ID]
    python -m tools.adr search QUERY
    python -m tools.adr validate
    python -m tools.adr reindex
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.adr.adr_generator import generate_adr
from tools.adr.adr_indexer import build_index, get_next_adr_number
from tools.adr.adr_validator import validate_all_adrs


def get_adr_dir() -> Path:
    """Get the ADR directory path."""
    return Path(__file__).parent.parent.parent / "docs" / "adr"


def get_index_path() -> Path:
    """Get the ADR index file path."""
    return get_adr_dir() / "index.json"


def load_index() -> dict:
    """Load the ADR index."""
    index_path = get_index_path()
    if not index_path.exists():
        return {"version": "1.0.0", "adrs": []}

    with open(index_path) as f:
        return json.load(f)


def cmd_new(args: argparse.Namespace) -> int:
    """Create a new ADR."""
    adr_dir = get_adr_dir()
    next_number = get_next_adr_number(adr_dir)

    adr_file = generate_adr(
        adr_dir=adr_dir,
        number=next_number,
        title=args.title,
        author=args.author or "unknown",
        category=args.category or "architecture",
        tier=args.tier or "t2",
    )

    print(f"Created: {adr_file}")
    print("\nNext steps:")
    print(f"1. Edit {adr_file} and fill in all sections")
    print("2. Run 'python -m tools.adr validate' to check the ADR")
    print("3. Run 'python -m tools.adr reindex' to update the index")
    print("4. Submit a PR with the new ADR")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all ADRs."""
    index = load_index()
    adrs = index.get("adrs", [])

    # Filter by status
    if args.status:
        adrs = [adr for adr in adrs if adr["status"] == args.status]

    # Filter by category
    if args.category:
        adrs = [adr for adr in adrs if adr["category"] == args.category]

    # Filter by tier
    if args.tier:
        adrs = [adr for adr in adrs if adr["tier"] == args.tier]

    if not adrs:
        print("No ADRs found.")
        return 0

    print(f"Found {len(adrs)} ADR(s):\n")
    for adr in adrs:
        status_emoji = {
            "proposed": "🟡",
            "accepted": "✅",
            "deprecated": "❌",
            "superseded": "🔄",
        }.get(adr["status"], "❓")

        tier_emoji = {
            "t1": "🟢",
            "t2": "🟡",
            "t3": "🔴",
        }.get(adr["tier"], "❓")

        print(f"{status_emoji} {tier_emoji} ADR-{adr['id']}: {adr['title']}")
        print(
            f"   Status: {adr['status']} | Category: {adr['category']} | Tier: {adr['tier'].upper()}"
        )
        print(f"   Author: {adr['author']} | Date: {adr['date']}")
        print()

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show ADR details."""
    adr_id = args.adr_id.zfill(4)
    adr_dir = get_adr_dir()

    # Find ADR file
    adr_files = list(adr_dir.glob(f"{adr_id}-*.md"))
    if not adr_files:
        print(f"Error: ADR-{adr_id} not found.")
        return 1

    adr_file = adr_files[0]

    # Read and display ADR content
    with open(adr_file) as f:
        content = f.read()

    print(content)
    return 0


def cmd_update_status(args: argparse.Namespace) -> int:
    """Update ADR status."""
    adr_id = args.adr_id.zfill(4)
    new_status = args.status.lower()

    valid_statuses = ["proposed", "accepted", "deprecated", "superseded"]
    if new_status not in valid_statuses:
        print(
            f"Error: Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
        )
        return 1

    adr_dir = get_adr_dir()
    adr_files = list(adr_dir.glob(f"{adr_id}-*.md"))
    if not adr_files:
        print(f"Error: ADR-{adr_id} not found.")
        return 1

    adr_file = adr_files[0]

    # Read ADR content
    with open(adr_file) as f:
        lines = f.readlines()

    # Update status line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("**Status:**"):
            lines[i] = f"**Status:** {new_status.capitalize()}  \n"
            updated = True
            break

    if not updated:
        print(f"Error: Could not find status line in {adr_file}")
        return 1

    # Write updated content
    with open(adr_file, "w") as f:
        f.writelines(lines)

    print(f"Updated ADR-{adr_id} status to '{new_status}'")
    print("\nNext steps:")
    print("1. Run 'python -m tools.adr reindex' to update the index")
    print("2. Submit a PR with the status change")

    return 0


def cmd_deprecate(args: argparse.Namespace) -> int:
    """Deprecate an ADR."""
    adr_id = args.adr_id.zfill(4)
    superseded_by = args.superseded_by

    adr_dir = get_adr_dir()
    adr_files = list(adr_dir.glob(f"{adr_id}-*.md"))
    if not adr_files:
        print(f"Error: ADR-{adr_id} not found.")
        return 1

    adr_file = adr_files[0]

    # Read ADR content
    with open(adr_file) as f:
        lines = f.readlines()

    # Update status and superseded_by lines
    for i, line in enumerate(lines):
        if line.startswith("**Status:**"):
            if superseded_by:
                lines[i] = "**Status:** Superseded  \n"
            else:
                lines[i] = "**Status:** Deprecated  \n"
        elif line.startswith("**Superseded by:**") and superseded_by:
            lines[i] = f"**Superseded by:** ADR-{superseded_by.zfill(4)}  \n"

    # Write updated content
    with open(adr_file, "w") as f:
        f.writelines(lines)

    status = "superseded" if superseded_by else "deprecated"
    print(f"Marked ADR-{adr_id} as {status}")
    if superseded_by:
        print(f"Superseded by: ADR-{superseded_by.zfill(4)}")

    print("\nNext steps:")
    print("1. Run 'python -m tools.adr reindex' to update the index")
    print("2. Submit a PR with the deprecation")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search ADRs by keyword."""
    query = args.query.lower()
    index = load_index()
    adrs = index.get("adrs", [])

    # Search in title, tags, and content
    matches = []
    for adr in adrs:
        if query in adr["title"].lower() or any(
            query in tag.lower() for tag in adr.get("tags", [])
        ):
            matches.append(adr)

    if not matches:
        print(f"No ADRs found matching '{query}'")
        return 0

    print(f"Found {len(matches)} ADR(s) matching '{query}':\n")
    for adr in matches:
        print(f"ADR-{adr['id']}: {adr['title']}")
        print(
            f"   Status: {adr['status']} | Category: {adr['category']} | Tier: {adr['tier'].upper()}"
        )
        print(f"   Tags: {', '.join(adr.get('tags', []))}")
        print()

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate all ADRs."""
    adr_dir = get_adr_dir()
    results = validate_all_adrs(adr_dir)

    if not results:
        print("No ADRs found to validate.")
        return 0

    errors = 0
    for adr_file, issues in results.items():
        if issues:
            print(f"❌ {adr_file.name}: {len(issues)} issue(s)")
            for issue in issues:
                print(f"   - {issue}")
            errors += 1
        else:
            print(f"✅ {adr_file.name}: Valid")

    print(f"\nValidation complete: {len(results) - errors}/{len(results)} ADRs valid")

    return 1 if errors > 0 else 0


def cmd_reindex(args: argparse.Namespace) -> int:
    """Rebuild the ADR index."""
    adr_dir = get_adr_dir()
    index_path = get_index_path()

    index = build_index(adr_dir)

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    adr_count = len(index.get("adrs", []))
    print(f"Indexed {adr_count} ADR(s)")
    print(f"Index saved to: {index_path}")

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="L9 ADR (Architecture Decision Records) CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # new command
    new_parser = subparsers.add_parser("new", help="Create a new ADR")
    new_parser.add_argument("title", help="ADR title")
    new_parser.add_argument("--author", help="ADR author")
    new_parser.add_argument(
        "--category",
        choices=["architecture", "infrastructure", "process", "tooling"],
        help="ADR category",
    )
    new_parser.add_argument("--tier", choices=["t1", "t2", "t3"], help="ADR tier")

    # list command
    list_parser = subparsers.add_parser("list", help="List all ADRs")
    list_parser.add_argument(
        "--status",
        choices=["proposed", "accepted", "deprecated", "superseded"],
        help="Filter by status",
    )
    list_parser.add_argument(
        "--category",
        choices=["architecture", "infrastructure", "process", "tooling"],
        help="Filter by category",
    )
    list_parser.add_argument(
        "--tier", choices=["t1", "t2", "t3"], help="Filter by tier"
    )

    # show command
    show_parser = subparsers.add_parser("show", help="Show ADR details")
    show_parser.add_argument("adr_id", help="ADR ID (e.g., 0042 or 42)")

    # update-status command
    update_status_parser = subparsers.add_parser(
        "update-status", help="Update ADR status"
    )
    update_status_parser.add_argument("adr_id", help="ADR ID (e.g., 0042 or 42)")
    update_status_parser.add_argument(
        "status",
        choices=["proposed", "accepted", "deprecated", "superseded"],
        help="New status",
    )

    # deprecate command
    deprecate_parser = subparsers.add_parser("deprecate", help="Deprecate an ADR")
    deprecate_parser.add_argument("adr_id", help="ADR ID (e.g., 0042 or 42)")
    deprecate_parser.add_argument(
        "--superseded-by", help="ADR ID that supersedes this one"
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search ADRs by keyword")
    search_parser.add_argument("query", help="Search query")

    # validate command
    subparsers.add_parser("validate", help="Validate all ADRs")

    # reindex command
    subparsers.add_parser("reindex", help="Rebuild the ADR index")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    commands = {
        "new": cmd_new,
        "list": cmd_list,
        "show": cmd_show,
        "update-status": cmd_update_status,
        "deprecate": cmd_deprecate,
        "search": cmd_search,
        "validate": cmd_validate,
        "reindex": cmd_reindex,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
