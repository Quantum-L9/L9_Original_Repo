#!/usr/bin/env python3
"""
Cursor Mistake Checker — Leverages L9's MistakePrevention Engine
================================================================

This script allows Cursor to check content against L9's mistake prevention
rules before execution.

Usage:
    python scripts/cursor_check_mistakes.py "content to check"
    python scripts/cursor_check_mistakes.py --file path/to/file.py
    echo "content" | python scripts/cursor_check_mistakes.py --stdin

Examples:
    python scripts/cursor_check_mistakes.py "/Users/ib-mac/Library/Application"
    python scripts/cursor_check_mistakes.py --file generated/api/client.py

Exit codes:
    0 — No violations found
    1 — Violations found but not blocking
    2 — CRITICAL violations found (would be blocked)
"""

import sys
import argparse
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

# Add L9 root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.governance.mistake_prevention import create_mistake_prevention, Violation


def format_violation(v: Violation) -> str:
    """Format a violation for display."""
    icon = "🚫" if v.blocked else "⚠️"
    return f"""
{icon} [{v.severity.upper()}] {v.name} (Rule: {v.rule_id})
   Match: "{v.match}"
   Prevention: {v.prevention}
   Blocked: {"YES" if v.blocked else "no"}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Check content against L9 mistake prevention rules"
    )
    parser.add_argument(
        "content",
        nargs="?",
        help="Content to check (inline)",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="File to check",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read content from stdin",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show rule statistics",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all rules",
    )
    
    args = parser.parse_args()
    
    engine = create_mistake_prevention()
    
    # List rules mode
    if args.list_rules:
        logger.info("L9 Mistake Prevention Rules:")
        logger.info("-" * 60)
        for rule in engine.rules:
            logger.info(f"  {rule.id}: {rule.name} [{rule.severity.value.upper()}]")
            logger.info(f"       Pattern: {rule.pattern[:50]}...")
            logger.info(f"       Prevention: {rule.prevention}")
            logger.info()
        return 0
    
    # Stats mode
    if args.stats:
        stats = engine.get_stats()
        logger.info("L9 Mistake Prevention Statistics:")
        logger.info(f"  Total rules: {stats['total_rules']}")
        logger.info(f"  Rules triggered: {stats['rules_triggered']}")
        logger.info(f"  Total occurrences: {stats['total_occurrences']}")
        if stats['top_violations']:
            logger.info("  Top violations:")
            for rule_id, name, count in stats['top_violations']:
                logger.info(f"    - {rule_id}: {name} ({count}x)")
        return 0
    
    # Get content to check
    content = ""
    if args.stdin:
        content = sys.stdin.read()
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.info(f"❌ File not found: {args.file}", file=sys.stderr)
            return 1
        content = file_path.read_text()
    elif args.content:
        content = args.content
    else:
        parser.print_help()
        return 1
    
    # Check content
    allowed, violations = engine.enforce(content)
    
    if not violations:
        logger.info("✅ No mistake patterns detected")
        return 0
    
    # Report violations
    logger.info(f"\n{'=' * 60}")
    logger.info(f"L9 MISTAKE CHECK — {len(violations)} violation(s) found")
    logger.info(f"{'=' * 60}")
    
    for v in violations:
        logger.info(format_violation(v))
    
    logger.info(f"{'=' * 60}")
    if not allowed:
        logger.info("🚫 BLOCKED: Critical violations would prevent execution")
        return 2
    else:
        logger.info("⚠️  WARNINGS: Non-blocking violations detected")
        return 1


if __name__ == "__main__":
    sys.exit(main())

