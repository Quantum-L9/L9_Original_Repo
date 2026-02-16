"""
End-to-end tests: Plan → Diff → Verification → Report

Tests the full pipeline from intent to deployable diff.
"""

import json

import pytest
from dev_layer.am_engine.compile import ArtifactCompiler
from dev_layer.modules.code_planning import (
    ChangeType,
    CodeChange,
    CodePlanner,
    VerificationReport,
    generate_diff,
)
from dev_layer.runtime.enforcement import (
    EnforcementEngine,
    GateDecision,
    OperationContext,
)


class TestDiffGeneration:
    """Test unified diff generation from plans."""

    def test_replace_change_generates_valid_diff(self):
        """REPLACE change should generate valid unified diff."""

        plan = CodePlanner({"constraints": {}, "protocols": {}}).plan_change(
            intent="Fix typo",
            scope=["utils.py"],
            constraints=[],
            patterns=[],
        )

        # Add a change
        plan.changes.append(
            CodeChange(
                file_path="utils.py",
                line_start=10,
                line_end=12,
                change_type=ChangeType.REPLACE,
                old_content="def old_function():\n    pass",
                new_content="def new_function():\n    return True",
            )
        )

        diff = generate_diff(plan, {})

        # Diff should contain file paths and changes
        assert "--- a/utils.py" in diff
        assert "+++ b/utils.py" in diff
        assert "-def old_function" in diff
        assert "+def new_function" in diff

    def test_insert_change_generates_valid_diff(self):
        """INSERT change should generate valid unified diff."""

        plan = CodePlanner({"constraints": {}, "protocols": {}}).plan_change(
            intent="Add import",
            scope=["main.py"],
            constraints=[],
            patterns=[],
        )

        plan.changes.append(
            CodeChange(
                file_path="main.py",
                line_start=1,
                line_end=1,
                change_type=ChangeType.INSERT,
                new_content="import logging",
            )
        )

        diff = generate_diff(plan, {})

        assert "+import logging" in diff


class TestGovernanceEnforcement:
    """Test governance enforcement in plan generation."""

    def test_enforcement_blocks_critical_risk_changes(self):
        """Engine should escalate critical-risk operations."""

        engine = EnforcementEngine()
        governance_law = {
            "constraints": {},
            "protocols": {},
            "policies": {},
        }
        engine.load_law(governance_law)

        context = OperationContext(
            operation_type="code_generation",
            target_path="governance/core.yaml",
            user="ca",
            estimated_risk="critical",
        )

        # Should escalate
        decision = engine.evaluate_gate(context)
        assert decision == GateDecision.ESCALATE

    def test_enforcement_allows_low_risk_changes(self):
        """Engine should allow low-risk operations."""

        engine = EnforcementEngine()
        engine.load_law({"constraints": {}, "protocols": {}, "policies": {}})

        context = OperationContext(
            operation_type="test_generation",
            target_path="tests/test_new_feature.py",
            user="ca",
            estimated_risk="low",
        )

        decision = engine.evaluate_gate(context)
        assert decision == GateDecision.ALLOWED


class TestVerificationReport:
    """Test verification report generation."""

    def test_report_serialization_to_json(self):
        """Verification report should serialize to valid JSON."""

        report = VerificationReport(
            plan_id="plan_test123",
            tests_passed=True,
            constraints_satisfied=True,
            rules_applied=["C-FILES-001", "H-EXCEPT-001"],
            risks_identified=[],
            confidence_score=0.92,
        )

        json_str = report.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["plan_id"] == "plan_test123"
        assert data["tests_passed"] is True
        assert data["confidence_score"] == 0.92


class TestEndToEndPipeline:
    """Test complete pipeline: artifact → plan → diff → report."""

    def test_complete_pipeline(self, tmp_path):
        """Full pipeline should work end-to-end."""

        # 1. Create artifact
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        artifact_file = input_dir / "dev_layer.md"
        artifact_file.write_text(
            "# Code Generation Rules\n\n"
            "C-FILES-001: Files must be edited, never recreated\n"
            "H-EXCEPT-001: Never swallow exceptions"
        )

        # 2. Compile artifact
        compiler = ArtifactCompiler(output_dir)
        result = compiler.compile_artifact(
            artifact_file.read_text(),
            "dev_layer.md",
        )

        assert result is not None
        assert result.exists()

        # 3. Generate plan
        governance = {"constraints": {}, "protocols": {}}
        planner = CodePlanner(governance)
        plan = planner.plan_change(
            intent="Refactor authentication module",
            scope=["services/auth.py"],
            constraints=["C-FILES-001"],
            patterns=["mvc"],
        )

        assert plan.plan_id.startswith("plan_")
        assert len(plan.deterministic_hash) == 64

        # 4. Create report
        report = VerificationReport(
            plan_id=plan.plan_id,
            tests_passed=True,
            constraints_satisfied=True,
            rules_applied=plan.constraints_validated,
            risks_identified=[],
            confidence_score=0.90,
        )

        assert report.confidence_score >= 0.85  # Meets threshold

        # Should be serializable
        json_str = report.to_json()
        assert json_str
        assert "plan_id" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
