"""
Determinism Tests: Verify that same inputs produce identical outputs.

This is critical for GMP compliance: reproducible code generation.
"""

import pytest
import hashlib
import json
from pathlib import Path
from dev_layer.modules.code_planning import CodePlanner, CodePlan
from dev_layer.am_engine.compile import ArtifactCompiler, ArtifactClassifier


class TestCodePlanDeterminism:
    """Test deterministic behavior of code planning."""

    def test_code_plan_identical_hash_same_inputs(self):
        """Same inputs should produce identical plan hashes."""

        governance = {
            "constraints": {"C-FILES-001": {"rule": "Files must be edited"}},
            "protocols": {},
        }
        planner1 = CodePlanner(governance)
        planner2 = CodePlanner(governance)

        # Plan 1
        plan1 = planner1.plan_change(
            intent="Add logging to UserService",
            scope=["app/services/user_service.py"],
            constraints=["C-FILES-001"],
            patterns=["mvc"],
        )

        # Plan 2 (identical inputs, different instance)
        plan2 = planner2.plan_change(
            intent="Add logging to UserService",
            scope=["app/services/user_service.py"],
            constraints=["C-FILES-001"],
            patterns=["mvc"],
        )

        assert plan1.deterministic_hash == plan2.deterministic_hash

    def test_code_plan_different_intent_different_hash(self):
        """Different intent should produce different plan hash."""

        governance = {"constraints": {}, "protocols": {}}
        planner = CodePlanner(governance)

        plan1 = planner.plan_change(
            intent="Add logging",
            scope=["app/services/user_service.py"],
            constraints=[],
            patterns=["mvc"],
        )

        plan2 = planner.plan_change(
            intent="Add caching",  # Different intent
            scope=["app/services/user_service.py"],
            constraints=[],
            patterns=["mvc"],
        )

        assert plan1.deterministic_hash != plan2.deterministic_hash

    def test_code_plan_hash_is_sha256(self):
        """Plan hash should be valid SHA256."""

        governance = {"constraints": {}, "protocols": {}}
        planner = CodePlanner(governance)

        plan = planner.plan_change(
            intent="Test",
            scope=["test.py"],
            constraints=[],
            patterns=[],
        )

        # SHA256 produces 64-character hex string
        assert len(plan.deterministic_hash) == 64
        assert all(c in "0123456789abcdef" for c in plan.deterministic_hash)


class TestArtifactCompilerDeterminism:
    """Test deterministic behavior of artifact compilation."""

    def test_classifier_same_text_same_category(self, tmp_path):
        """Same text should classify to same category."""

        classifier1 = ArtifactClassifier()
        classifier2 = ArtifactClassifier()

        text = "This is a constraint: must not allow unsafe operations"

        result1 = classifier1.classify(text)
        result2 = classifier2.classify(text)

        assert result1.category == result2.category
        assert result1.confidence == result2.confidence

    def test_compiler_idempotent(self, tmp_path):
        """Compiling same artifact twice should not create duplicate output."""

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create input artifact
        artifact_file = input_dir / "test.md"
        artifact_file.write_text("This is a heuristic: never swallow exceptions")

        # Compile twice
        compiler = ArtifactCompiler(output_dir)
        result1 = compiler.compile_artifact(
            artifact_file.read_text(),
            "test.md",
        )
        result2 = compiler.compile_artifact(
            artifact_file.read_text(),
            "test.md",
        )

        # Should return same path (idempotent)
        assert result1 == result2


class TestPlanHashConsistency:
    """Test that plan hashes remain consistent across runs."""

    def test_plan_hash_stable_across_serialization(self):
        """Plan hash should be stable when computed multiple times."""

        governance = {"constraints": {}, "protocols": {}}
        planner = CodePlanner(governance)

        plan = planner.plan_change(
            intent="Refactor handler",
            scope=["handlers/auth.py"],
            constraints=[],
            patterns=["mvc"],
        )

        # Compute hash multiple times
        hash1 = plan.compute_hash()
        hash2 = plan.compute_hash()
        hash3 = plan.compute_hash()

        assert hash1 == hash2 == hash3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
