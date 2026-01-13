#!/usr/bin/env python3
"""
L9 Dead Code Audit - Phase 4: GMP Action File Generator
========================================================

Auto-generates a canonical GMP-Action file from categorized dead code findings.

Output:
- reports/GMP_Action_DeadCode_Remediation.md (canonical GMP format)

This file can be used directly with `/gmp @reports/GMP_Action_DeadCode_Remediation.md`

Version: 2.0.0
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class GMPTodoItem:
    """A single GMP TODO item in canonical format."""
    id: str
    file: str
    target_symbol: str
    lines: str
    action: str  # Replace, Insert, Delete, Wrap
    change: str
    reason: str
    confidence: float
    gate: str = "None"
    imports: str = "NONE"
    risk_level: str = "medium"
    auto_fix: bool = False

    def to_canonical_format(self) -> str:
        """Generate canonical TODO format for GMP-Action file."""
        lines = [
            f"- [{self.id}] File: `{self.file}`",
            f"       Lines: {self.lines}",
            f"       Action: {self.action}",
            f"       Target: `{self.target_symbol}`",
            f"       Change: {self.change}",
            f"       Gate: {self.gate}",
            f"       Imports: {self.imports}",
        ]
        return "\n".join(lines)


@dataclass
class GMPActionPlan:
    """Complete GMP Action file."""
    gmp_id: str
    task_name: str
    risk_level: str
    generated_at: str
    todos: list[GMPTodoItem] = field(default_factory=list)
    auto_fixable_count: int = 0
    manual_review_count: int = 0

    def to_canonical_gmp_action(self) -> str:
        """Generate canonical GMP-Action-Prompt format."""
        lines = [
            "=" * 76,
            "GOD-MODE CURSOR PROMPT — L9 GMP (DEAD CODE REMEDIATION)",
            "=" * 76,
            "",
            "PURPOSE:",
            "• Remediate dead code findings from automated audit",
            "• Eliminate unused imports, functions, classes, and variables",
            "• Wire up unused config fields or delete if truly dead",
            "• Execute in deterministic phases with validation",
            "",
            "=" * 76,
            "",
            "VARIABLE BINDINGS:",
            f"  TASK_NAME: {self.task_name}",
            f"  GMP_ID: {self.gmp_id}",
            f"  RISK_LEVEL: {self.risk_level}",
            f"  GENERATED: {self.generated_at}",
            f"  TOTAL_TODOS: {len(self.todos)}",
            f"  AUTO_FIXABLE: {self.auto_fixable_count}",
            f"  MANUAL_REVIEW: {self.manual_review_count}",
            "",
            "=" * 76,
            "",
            "ROLE:",
            "You are a constrained execution agent operating inside the L9 Secure AI OS",
            "repository at `/Users/ib-mac/Projects/L9/`.",
            "Execute instructions exactly as written. No freelancing.",
            "",
            "=" * 76,
            "",
            "PHASE 0 — TODO PLAN (LOCKED)",
            "",
            "Each TODO item includes:",
            "- Unique TODO ID",
            "- Absolute file path under /Users/ib-mac/Projects/L9/",
            "- Line number or range",
            "- Action verb (Replace | Insert | Delete | Wrap)",
            "- Target structure (function/class/variable)",
            "- Expected change",
            "- Gate and imports",
            "",
            "---",
            "",
        ]
        
        # Group TODOs by action type
        by_action: dict[str, list[GMPTodoItem]] = {}
        for todo in self.todos:
            if todo.action not in by_action:
                by_action[todo.action] = []
            by_action[todo.action].append(todo)
        
        # Output order: Delete first (safest), then Replace, then Insert
        action_order = ["Delete", "Replace", "Insert", "Wrap"]
        action_emoji = {
            "Delete": "🗑️",
            "Replace": "🔄",
            "Insert": "➕",
            "Wrap": "📦",
        }
        
        for action in action_order:
            if action not in by_action:
                continue
            
            todos = by_action[action]
            emoji = action_emoji.get(action, "📋")
            lines.append(f"### {emoji} {action.upper()} ({len(todos)} items)")
            lines.append("")
            
            for todo in todos:
                lines.append(todo.to_canonical_format())
                lines.append("")
        
        # Add remaining phases
        lines.extend([
            "---",
            "",
            "=" * 76,
            "",
            "PHASE 1 — BASELINE CONFIRMATION",
            "",
            "Before making changes:",
            "- [ ] Open each file referenced by TODOs",
            "- [ ] Confirm line anchors exist and match described structures",
            "- [ ] Confirm required symbols are present",
            "",
            "=" * 76,
            "",
            "PHASE 2 — IMPLEMENTATION",
            "",
            "Execute TODO items in order:",
            "- [ ] Modify only the described files and line ranges",
            "- [ ] Make minimal edits required for the change",
            "- [ ] Do not touch unrelated code",
            "",
            "For AUTO_FIX items, run: `ruff check --fix <file>`",
            "",
            "=" * 76,
            "",
            "PHASE 3 — ENFORCEMENT",
            "",
            "- [ ] Add guards/tests only if TODO requires it",
            "- [ ] No invented enforcement",
            "",
            "=" * 76,
            "",
            "PHASE 4 — VALIDATION",
            "",
            "Run validations:",
            "- [ ] `python -m py_compile <file>` for each modified file",
            "- [ ] `ruff check <file>` for each modified file",
            "- [ ] `pytest tests/` for any tests affected",
            "",
            "=" * 76,
            "",
            "PHASE 5 — RECURSIVE VERIFICATION",
            "",
            "- [ ] Every TODO ID maps to a verified code change",
            "- [ ] No unauthorized diffs exist",
            "- [ ] No assumptions used",
            "",
            "=" * 76,
            "",
            "PHASE 6 — FINAL AUDIT",
            "",
            f"- [ ] Report written to `/Users/ib-mac/Projects/L9/reports/GMP_Report_{self.gmp_id}_DeadCode.md`",
            "- [ ] All required sections exist",
            "- [ ] No placeholders",
            "",
            "=" * 76,
            "",
            "FINAL DECLARATION:",
            "",
            "> All phases (0–6) complete. No assumptions. No drift. Scope locked.",
            f"> Output: `/Users/ib-mac/Projects/L9/reports/GMP_Report_{self.gmp_id}_DeadCode.md`",
            "> No further changes are permitted.",
            "",
            "=" * 76,
        ])
        
        return "\n".join(lines)


# =============================================================================
# GENERATION LOGIC
# =============================================================================

def map_action_to_verb(action: str) -> str:
    """Map audit action to GMP action verb."""
    mapping = {
        "WIRE_UP": "Insert",
        "DELETE": "Delete",
        "AUTO_FIX": "Replace",
        "NOQA": "Insert",  # Insert noqa comment
        "REVIEW": "Replace",
    }
    return mapping.get(action, "Replace")


def generate_todo_id(index: int, section: str) -> str:
    """Generate a unique TODO ID."""
    return f"{section}.{index}"


def generate_gmp_action(
    categorized_file: Path,
    repo_root: Path = REPO_ROOT,
    gmp_id: str = "GMP-DC",
    output_file: Path | None = None,
) -> GMPActionPlan:
    """
    Generate GMP Action file from categorized findings.
    
    Args:
        categorized_file: Path to Phase 3 JSON output
        repo_root: Repository root path
        gmp_id: GMP identifier
        output_file: Output path for GMP Action file
    
    Returns:
        GMPActionPlan
    """
    logger.info(f"Loading categorized findings from {categorized_file}...")
    
    with open(categorized_file) as f:
        categorized_data = json.load(f)
    
    # Collect all findings
    all_findings = []
    for risk in ["high_risk", "medium_risk", "low_risk"]:
        for finding in categorized_data.get(risk, []):
            finding["_risk_level"] = risk.replace("_risk", "")
            all_findings.append(finding)
    
    logger.info(f"Processing {len(all_findings)} findings...")
    
    plan = GMPActionPlan(
        gmp_id=gmp_id,
        task_name="dead_code_remediation",
        risk_level="Medium",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M EST"),
    )
    
    # Group by action for section numbering
    by_action: dict[str, list] = {}
    for finding in all_findings:
        action = finding.get("action", "REVIEW")
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(finding)
    
    # Section mapping
    section_map = {
        "DELETE": "D",
        "WIRE_UP": "W",
        "AUTO_FIX": "A",
        "NOQA": "N",
        "REVIEW": "R",
    }
    
    for action, findings in by_action.items():
        section = section_map.get(action, "X")
        
        for i, finding in enumerate(findings, 1):
            auto_fix = finding.get("auto_fixable", False)
            gmp_action = map_action_to_verb(action)
            
            # Generate change description
            if action == "DELETE":
                change = f"Delete unused {finding.get('symbol_type', 'symbol')} `{finding.get('symbol', '')}`"
            elif action == "WIRE_UP":
                change = f"Wire up unused config field or add usage"
            elif action == "AUTO_FIX":
                change = f"Run `ruff check --fix` to auto-remove"
            elif action == "NOQA":
                change = f"Add `# noqa: F401` if intentionally unused"
            else:
                change = finding.get("proposed_fix", "Review and fix manually")
            
            todo = GMPTodoItem(
                id=generate_todo_id(i, section),
                file=finding.get("file", ""),
                target_symbol=finding.get("symbol", ""),
                lines=str(finding.get("line", 0)),
                action=gmp_action,
                change=change,
                reason=finding.get("action_reason", finding.get("message", "")),
                confidence=finding.get("confidence", 0.5),
                gate="py_compile" if gmp_action != "Delete" else "None",
                imports="NONE",
                risk_level=finding.get("_risk_level", "medium"),
                auto_fix=auto_fix,
            )
            
            plan.todos.append(todo)
            
            if auto_fix:
                plan.auto_fixable_count += 1
            if action == "REVIEW":
                plan.manual_review_count += 1
    
    # Sort TODOs: Delete first, then others by confidence
    action_priority = {"Delete": 0, "Replace": 1, "Insert": 2, "Wrap": 3}
    plan.todos.sort(key=lambda t: (action_priority.get(t.action, 5), -t.confidence))
    
    logger.info(f"Generated {len(plan.todos)} TODOs")
    
    # Output GMP Action file
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(plan.to_canonical_gmp_action())
        logger.info(f"GMP Action file written to {output_file}")
    
    return plan


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="L9 Dead Code Audit - Phase 4: GMP Action Generator"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="reports/dead_code_risk_matrix.json",
        help="Input file from Phase 3",
    )
    parser.add_argument(
        "--gmp-id",
        type=str,
        default="GMP-DC",
        help="GMP identifier (default: GMP-DC)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/GMP_Action_DeadCode_Remediation.md",
        help="Output GMP Action file path",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(0),
        )
    
    input_file = REPO_ROOT / args.input
    output_file = REPO_ROOT / args.output
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Run Phase 3 first: python scripts/audit/categorize_dead_code.py")
        return 1
    
    plan = generate_gmp_action(
        categorized_file=input_file,
        repo_root=REPO_ROOT,
        gmp_id=args.gmp_id,
        output_file=output_file,
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("DEAD CODE AUDIT - PHASE 4 GMP ACTION GENERATOR")
    print("=" * 60)
    print(f"GMP ID: {plan.gmp_id}")
    print(f"Total TODOs: {len(plan.todos)}")
    print(f"✅ Auto-fixable: {plan.auto_fixable_count}")
    print(f"👀 Manual review: {plan.manual_review_count}")
    
    # Breakdown by action
    by_action: dict[str, int] = {}
    for todo in plan.todos:
        by_action[todo.action] = by_action.get(todo.action, 0) + 1
    
    print("\nTODOs by action:")
    for action, count in sorted(by_action.items(), key=lambda x: -x[1]):
        print(f"  {action}: {count}")
    
    print(f"\n📄 GMP Action file: {output_file}")
    print(f"\n💡 Use with: /gmp @{output_file.relative_to(REPO_ROOT)}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
