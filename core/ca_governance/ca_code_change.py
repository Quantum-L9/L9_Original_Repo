"""
L9 CA Governance - Code Change Orchestrator
============================================
Orchestrates the complete code change workflow for CA (Coding Agent).

Implements the P-CODE-001 protocol:
1. Generate diffs
2. Validate constraints
3. Generate report
4. Check confidence threshold
5. Apply or escalate

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .constraint_validator import ConstraintValidator, ValidationResult
from .diff_generator import BatchDiff, DiffGenerator
from .report_generator import ChangeReport, ChangeType, ReportGenerator


class ChangeStatus(Enum):
    """Status of a proposed change."""

    APPROVED = "approved"  # Ready to apply
    ESCALATED = "escalated"  # Needs human approval
    BLOCKED = "blocked"  # Constraint violations
    APPLIED = "applied"  # Successfully applied
    FAILED = "failed"  # Application failed


@dataclass
class ChangeProposal:
    """A proposed code change with all metadata."""

    status: ChangeStatus
    diff: str
    report: str
    changes: list[dict]
    validation: ValidationResult
    confidence: float
    reason: str | None = None
    batch_diff: BatchDiff | None = None
    change_report: ChangeReport | None = None


class CACodeChange:
    """Orchestrates code changes with full governance."""

    def __init__(
        self,
        repo_root: Path | None = None,
        governance_loader=None,
        confidence_threshold: float = 0.80,
    ):
        """
        Initialize CA code change orchestrator.

        Args:
            repo_root: Root directory of the repository
            governance_loader: Optional governance loader
            confidence_threshold: Minimum confidence for autonomous changes
        """
        self.repo_root = repo_root or Path.cwd()
        self.confidence_threshold = confidence_threshold

        # Initialize components
        self.diff_gen = DiffGenerator(repo_root=self.repo_root)
        self.report_gen = ReportGenerator(agent_id="CA")
        self.validator = ConstraintValidator(
            repo_root=self.repo_root, governance_loader=governance_loader
        )

    def propose_change(
        self,
        task: str,
        changes: list[dict],
        rationale: str,
        confidence: float,
        change_type: ChangeType = ChangeType.FEATURE,
        tests_added: bool = False,
    ) -> ChangeProposal:
        """
        Propose a code change following P-CODE-001 protocol.

        Args:
            task: Description of the task
            changes: List of dicts with keys: file_path, original, modified
            rationale: Explanation of why changes were made
            confidence: Confidence score (0.0-1.0)
            change_type: Type of change
            tests_added: Whether tests were added

        Returns:
            ChangeProposal object
        """
        # Step 1: Generate diffs
        batch_diff = self.diff_gen.generate_batch_diff(changes)
        diff_markdown = self.diff_gen.format_for_review(batch_diff)

        # Step 2: Validate constraints
        validation = self.validator.validate_batch(changes)

        # Step 3: Identify risks
        risks = self.report_gen._identify_risks(changes)
        breaking_changes = self.report_gen._detect_breaking_changes(changes)

        # Step 4: Generate report
        change_report = self.report_gen.generate_change_report(
            task=task,
            changes=changes,
            rationale=rationale,
            confidence=confidence,
            change_type=change_type,
            tests_added=tests_added,
            breaking_changes=breaking_changes,
            risks=risks,
        )
        report_markdown = self.report_gen.format_report(change_report)

        # Step 5: Check confidence threshold (POL-CONF-001)
        if confidence < self.confidence_threshold:
            return ChangeProposal(
                status=ChangeStatus.ESCALATED,
                diff=diff_markdown,
                report=report_markdown,
                changes=changes,
                validation=validation,
                confidence=confidence,
                reason=f"confidence_below_threshold ({confidence:.2f} < {self.confidence_threshold})",
                batch_diff=batch_diff,
                change_report=change_report,
            )

        # Step 6: Check for blocking violations
        if not validation.valid:
            return ChangeProposal(
                status=ChangeStatus.BLOCKED,
                diff=diff_markdown,
                report=report_markdown,
                changes=changes,
                validation=validation,
                confidence=confidence,
                reason=f"constraint_violations ({validation.blocking_count} blocking)",
                batch_diff=batch_diff,
                change_report=change_report,
            )

        # Step 7: All clear - ready to apply
        return ChangeProposal(
            status=ChangeStatus.APPROVED,
            diff=diff_markdown,
            report=report_markdown,
            changes=changes,
            validation=validation,
            confidence=confidence,
            batch_diff=batch_diff,
            change_report=change_report,
        )

    def apply_change(self, proposal: ChangeProposal) -> dict:
        """
        Apply approved changes to files.

        Args:
            proposal: ChangeProposal object

        Returns:
            Dict with success status and applied files
        """
        if proposal.status != ChangeStatus.APPROVED:
            return {
                "success": False,
                "error": f"Change not approved (status: {proposal.status.value})",
                "reason": proposal.reason,
            }

        applied = []
        failed = []

        for change in proposal.changes:
            try:
                file_path = self.repo_root / change["file_path"]

                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the modified content
                file_path.write_text(change["modified"])
                applied.append(str(file_path.relative_to(self.repo_root)))

            except Exception as e:
                failed.append({"file": change["file_path"], "error": str(e)})

        if failed:
            return {
                "success": False,
                "applied": applied,
                "failed": failed,
                "error": f"Failed to apply {len(failed)} files",
            }

        return {"success": True, "files_modified": applied, "count": len(applied)}

    def save_artifacts(
        self, proposal: ChangeProposal, output_dir: Path | None = None
    ) -> dict[str, Path]:
        """
        Save diff and report to files.

        Args:
            proposal: ChangeProposal object
            output_dir: Directory to save artifacts (defaults to changes/)

        Returns:
            Dict mapping artifact type to file path
        """
        output_dir = output_dir or (self.repo_root / "changes")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp-based filename
        from datetime import datetime

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Save diff
        diff_path = output_dir / f"diff_{timestamp}.md"
        diff_path.write_text(proposal.diff)

        # Save report
        report_path = output_dir / f"report_{timestamp}.md"
        report_path.write_text(proposal.report)

        # Save validation results if there are violations
        artifacts = {"diff": diff_path, "report": report_path}

        if proposal.validation.violations:
            validation_path = output_dir / f"validation_{timestamp}.md"
            validation_path.write_text(
                self.validator.format_violations(proposal.validation)
            )
            artifacts["validation"] = validation_path

        return artifacts

    def generate_commit_message(self, proposal: ChangeProposal) -> str:
        """
        Generate a git commit message from the proposal.

        Args:
            proposal: ChangeProposal object

        Returns:
            Commit message
        """
        if not proposal.change_report:
            return f"chore: {proposal.changes[0].get('file_path', 'update')}"

        return self.report_gen.format_commit_message(proposal.change_report)
