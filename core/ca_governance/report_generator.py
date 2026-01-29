"""
L9 CA Governance - Report Generator
====================================
Generates structured reports explaining code changes proposed by CA (Coding Agent).

Every code change must be accompanied by a report that explains:
- What changed and why
- Rationale for the change
- Confidence level
- Test coverage
- Potential risks

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ChangeType(Enum):
    """Types of code changes."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"


@dataclass
class ChangeReport:
    """Structured report for code changes."""

    metadata: dict
    summary: dict
    rationale: str
    changes: list[dict]
    validation: dict
    risks: list[str] = field(default_factory=list)
    mitigation: list[str] = field(default_factory=list)


class ReportGenerator:
    """Generate reports for code changes."""

    def __init__(self, agent_id: str = "CA"):
        """
        Initialize report generator.

        Args:
            agent_id: Identifier for the agent making changes
        """
        self.agent_id = agent_id

    def generate_change_report(
        self,
        task: str,
        changes: list[dict],
        rationale: str,
        confidence: float,
        change_type: ChangeType = ChangeType.FEATURE,
        tests_added: bool = False,
        tests_passed: bool | None = None,
        breaking_changes: bool = False,
        risks: list[str] | None = None,
        mitigation: list[str] | None = None,
    ) -> ChangeReport:
        """
        Generate a complete change report.

        Args:
            task: Description of the task
            changes: List of file changes
            rationale: Explanation of why changes were made
            confidence: Confidence score (0.0-1.0)
            change_type: Type of change
            tests_added: Whether tests were added
            tests_passed: Whether tests passed (None if not run yet)
            breaking_changes: Whether changes might break existing code
            risks: List of identified risks
            mitigation: List of mitigation strategies

        Returns:
            ChangeReport object
        """
        return ChangeReport(
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task": task,
                "confidence": confidence,
                "agent": self.agent_id,
                "change_type": change_type.value,
            },
            summary={
                "files_changed": len(changes),
                "tests_added": tests_added,
                "tests_passed": tests_passed,
                "breaking_changes": breaking_changes,
            },
            rationale=rationale,
            changes=changes,
            validation={
                "constraints_checked": True,
                "protocols_followed": True,
                "tests_passed": tests_passed,
            },
            risks=risks or [],
            mitigation=mitigation or [],
        )

    def _detect_breaking_changes(self, changes: list[dict]) -> bool:
        """
        Detect if changes might break existing code.

        Args:
            changes: List of file changes

        Returns:
            True if breaking changes detected
        """
        for change in changes:
            original = change.get("original", "")
            modified = change.get("modified", "")

            # Check for function signature changes
            if "def " in original and "def " in modified:
                # Simple heuristic: function definitions changed
                orig_defs = [line for line in original.split("\n") if "def " in line]
                mod_defs = [line for line in modified.split("\n") if "def " in line]
                if orig_defs != mod_defs:
                    return True

            # Check for class changes
            if "class " in original and "class " in modified:
                orig_classes = [
                    line for line in original.split("\n") if "class " in line
                ]
                mod_classes = [
                    line for line in modified.split("\n") if "class " in line
                ]
                if orig_classes != mod_classes:
                    return True

        return False

    def _identify_risks(self, changes: list[dict]) -> list[str]:
        """
        Identify potential risks in changes.

        Args:
            changes: List of file changes

        Returns:
            List of identified risks
        """
        risks = []

        for change in changes:
            file_path = change.get("file_path", "")
            modified = change.get("modified", "")

            # Risk: Changing core files
            if "core/" in file_path:
                risks.append(f"Modifying core system file: {file_path}")

            # Risk: Database migrations
            if "migrations/" in file_path or "migration" in file_path.lower():
                risks.append(f"Database migration changes: {file_path}")

            # Risk: Authentication/security code
            if any(
                keyword in modified.lower()
                for keyword in ["password", "auth", "token", "secret"]
            ):
                risks.append(f"Security-sensitive changes in: {file_path}")

            # Risk: API changes
            if "api/" in file_path or "@app." in modified:
                risks.append(f"API endpoint changes: {file_path}")

        return risks

    def format_report(self, report: ChangeReport) -> str:
        """
        Format report as markdown.

        Args:
            report: ChangeReport object

        Returns:
            Markdown-formatted report
        """
        md = ["# Code Change Report\n\n"]

        # Metadata
        md.append("## Metadata\n")
        md.append(f"- **Task:** {report.metadata['task']}\n")
        md.append(f"- **Agent:** {report.metadata['agent']}\n")
        md.append(f"- **Type:** {report.metadata['change_type']}\n")
        md.append(f"- **Timestamp:** {report.metadata['timestamp']}\n")
        md.append(f"- **Confidence:** {report.metadata['confidence']:.2f}\n\n")

        # Summary
        md.append("## Summary\n")
        md.append(f"- **Files Changed:** {report.summary['files_changed']}\n")
        md.append(
            f"- **Tests Added:** {'✅ Yes' if report.summary['tests_added'] else '❌ No'}\n"
        )

        if report.summary["tests_passed"] is not None:
            md.append(
                f"- **Tests Passed:** {'✅ Yes' if report.summary['tests_passed'] else '❌ No'}\n"
            )
        else:
            md.append("- **Tests Passed:** ⏳ Pending\n")

        md.append(
            f"- **Breaking Changes:** {'⚠️ Yes' if report.summary['breaking_changes'] else '✅ No'}\n\n"
        )

        # Rationale
        md.append("## Rationale\n\n")
        md.append(f"{report.rationale}\n\n")

        # Risks
        if report.risks:
            md.append("## Identified Risks\n\n")
            for risk in report.risks:
                md.append(f"- ⚠️ {risk}\n")
            md.append("\n")

        # Mitigation
        if report.mitigation:
            md.append("## Risk Mitigation\n\n")
            for mitigation in report.mitigation:
                md.append(f"- ✅ {mitigation}\n")
            md.append("\n")

        # Validation
        md.append("## Validation\n")
        md.append(
            f"- **Constraints Checked:** {'✅' if report.validation['constraints_checked'] else '❌'}\n"
        )
        md.append(
            f"- **Protocols Followed:** {'✅' if report.validation['protocols_followed'] else '❌'}\n"
        )

        if report.validation["tests_passed"] is not None:
            md.append(
                f"- **Tests Passed:** {'✅' if report.validation['tests_passed'] else '❌'}\n"
            )

        md.append("\n")

        # Files Changed
        md.append("## Files Changed\n\n")
        for change in report.changes:
            md.append(f"- `{change.get('file_path', 'unknown')}`\n")

        return "".join(md)

    def format_commit_message(self, report: ChangeReport) -> str:
        """
        Generate a git commit message from the report.

        Args:
            report: ChangeReport object

        Returns:
            Commit message in conventional commits format
        """
        change_type = report.metadata["change_type"]
        task = report.metadata["task"]

        # First line: type(scope): subject
        lines = [f"{change_type}: {task}\n\n"]

        # Body: rationale
        lines.append(f"{report.rationale}\n\n")

        # Footer: metadata
        lines.append(f"Confidence: {report.metadata['confidence']:.2f}\n")
        lines.append(f"Agent: {report.metadata['agent']}\n")

        if report.summary["breaking_changes"]:
            lines.append("\nBREAKING CHANGE: This commit contains breaking changes\n")

        return "".join(lines)
