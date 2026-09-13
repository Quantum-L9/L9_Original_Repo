#!/usr/bin/env python3
"""
Generate AI collaboration report for each PR.

Shows:
  1. Which subsystems are being touched
  2. Which scopes are AI-allowed vs restricted
  3. Warnings if protected surfaces are involved
  4. AI collaboration rules for the PR context
"""


import subprocess
import sys
from pathlib import Path

import yaml


def get_changed_files() -> set[str]:
    """Get files changed in current PR."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],  # noqa: S607 — trusted system command
            capture_output=True,
            text=True,
            check=True,
        )
        return (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )
    except subprocess.CalledProcessError:
        return set()


def load_code_map() -> dict:
    """Load CODE-MAP.yaml."""
    code_map_path = Path("docs/CODE-MAP.yaml")
    if not code_map_path.exists():
        return {}
    with open(code_map_path) as f:
        return yaml.safe_load(f) or {}


def analyze_pr(changed_files: set[str], code_map: dict) -> dict[str, list[str]]:
    """Map changed files to subsystems and AI scopes."""
    analysis = {
        "allowed": [],
        "restricted": [],
        "protected": [],
        "untouched_subsystems": [],
    }

    touched_subsystems = set()

    for changed_file in changed_files:
        if not changed_file or changed_file == "":
            continue

        # Check each subsystem
        for subsystem_name, subsystem_info in code_map.get("subsystems", {}).items():
            touched_subsystems.add(subsystem_name)

            # Check if file is in allowed patterns
            allowed = subsystem_info.get("ai_allowed_patterns", [])
            forbidden = subsystem_info.get("ai_forbidden_patterns", [])

            if any(pattern_match(changed_file, p) for p in allowed):
                analysis["allowed"].append(f"{changed_file} ({subsystem_name})")
                break

            if any(pattern_match(changed_file, p) for p in forbidden):
                analysis["protected"].append(f"{changed_file} ({subsystem_name})")
                break

            if changed_file.startswith(subsystem_info["path"]):
                analysis["restricted"].append(f"{changed_file} ({subsystem_name})")
                break

    # Find untouched subsystems
    all_subsystems = set(code_map.get("subsystems", {}).keys())
    analysis["untouched_subsystems"] = list(all_subsystems - touched_subsystems)

    return analysis


def pattern_match(path: str, pattern: str) -> bool:
    """Simple glob-style pattern matching."""
    from fnmatch import fnmatch

    return fnmatch(path, pattern)


def format_report(analysis: dict, changed_files: set[str]) -> str:
    """Format markdown report."""
    lines = [
        "### 📋 AI Collaboration Scope Analysis",
        "",
        f"**Changed Files:** {len(changed_files)}",
        "",
    ]

    if analysis["allowed"]:
        lines.extend(
            [
                "#### ✅ AI-Allowed Scopes (Can be modified by Cursor)",
                "",
            ]
        )
        for f in analysis["allowed"]:
            lines.append(f"- {f}")
        lines.append("")

    if analysis["restricted"]:
        lines.extend(
            [
                "#### ⚠️ Restricted Scopes (AI advisory only, human approval required)",
                "",
            ]
        )
        for f in analysis["restricted"]:
            lines.append(f"- {f}")
        lines.append("")

    if analysis["protected"]:
        lines.extend(
            [
                "#### 🔒 Protected Surfaces (LCTO-controlled, requires approval)",
                "",
            ]
        )
        for f in analysis["protected"]:
            lines.append(f"- {f}")
        lines.append("")
        lines.extend(
            [
                "**⚠️ WARNING:** This PR touches protected files.",
                "Please obtain approval from the code owner before merging.",
                "",
            ]
        )

    if analysis["untouched_subsystems"]:
        lines.extend(
            [
                "#### 📦 Untouched Subsystems",
                "",
            ]
        )
        for subsys in analysis["untouched_subsystems"]:
            lines.append(f"- {subsys}")
        lines.append("")

    return "\n".join(lines)


def main():
    changed = get_changed_files()
    code_map = load_code_map()

    if not code_map:
        print("⚠️  CODE-MAP.yaml not found. Run: python scripts/extract_code_facts.py")  # noqa: ADR-0019
        return 1

    analysis = analyze_pr(changed, code_map)
    report = format_report(analysis, changed)
    print(report)  # noqa: ADR-0019

    # Return non-zero if protected files touched (will trigger PR comment)
    return 1 if analysis["protected"] else 0


if __name__ == "__main__":
    sys.exit(main())

# Runtime execution trace - updated automatically on every execution
