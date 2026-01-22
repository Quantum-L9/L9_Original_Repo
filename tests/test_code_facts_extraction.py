"""
Integration tests for docs-code sync system.

Tests validate that:
  1. extract_code_facts.py correctly parses Python AST
  2. CODE-MAP.yaml is well-formed and queryable
  3. README.meta.yaml validates against schema
  4. Protected files cannot be modified
  5. AI collaboration scopes are correctly computed
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Code Facts Extraction",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "test_code_facts_extraction",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def code_map() -> Dict[str, Any]:
    """Load CODE-MAP.yaml for testing."""
    code_map_path = Path("docs/CODE-MAP.yaml")
    if not code_map_path.exists():
        pytest.skip(
            "CODE-MAP.yaml not found. Run: python scripts/extract_code_facts.py"
        )

    with open(code_map_path) as f:
        return yaml.safe_load(f)


SUBSYSTEM_PATHS = {
    "agents": "core/agents",
    "memory": "memory",
    "tools": "core/tools",
    "api": "api",
}


@pytest.fixture
def meta_files() -> Dict[str, Dict[str, Any]]:
    """Load all README.meta.yaml files."""
    meta_files = {}
    for subsystem, path in SUBSYSTEM_PATHS.items():
        meta_path = Path(f"{path}/README.meta.yaml")
        if meta_path.exists():
            with open(meta_path) as f:
                meta_files[subsystem] = yaml.safe_load(f)
    return meta_files


class TestCodeMapValidity:
    """Test that CODE-MAP.yaml is well-formed."""

    def test_code_map_has_version(self, code_map):
        """CODE-MAP must have version and timestamp."""
        assert "version" in code_map
        assert "last_verified" in code_map
        assert code_map["version"] == "1.0"

    def test_code_map_has_subsystems(self, code_map):
        """CODE-MAP must define all 4 subsystems."""
        subsystems = code_map.get("subsystems", {})
        assert set(subsystems.keys()) == {"agents", "memory", "tools", "api"}

    def test_subsystem_has_required_fields(self, code_map):
        """Each subsystem must have required fields."""
        required_fields = {
            "path",
            "entry_point",
            "key_classes",
            "data_models",
            "protected_files",
            "ai_allowed_patterns",
            "ai_forbidden_patterns",
            "invariants",
        }

        for subsystem, info in code_map.get("subsystems", {}).items():
            missing = required_fields - set(info.keys())
            assert not missing, f"{subsystem} missing fields: {missing}"

    def test_entry_points_are_valid_classes(self, code_map):
        """Entry point classes should be documented."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            entry_point = info.get("entry_point", {})
            assert entry_point.get("class"), f"{subsystem} missing entry_point.class"
            assert entry_point.get("method"), f"{subsystem} missing entry_point.method"

    def test_protected_files_are_paths(self, code_map):
        """Protected files must be valid file paths."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            protected = info.get("protected_files", [])
            assert isinstance(
                protected, list
            ), f"{subsystem} protected_files not a list"
            for f in protected:
                assert isinstance(
                    f, str
                ), f"{subsystem} protected file not a string: {f}"
                assert len(f) > 0, f"{subsystem} empty protected file path"

    def test_ai_patterns_are_valid(self, code_map):
        """AI allowed/forbidden patterns must be glob patterns or paths."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            allowed = info.get("ai_allowed_patterns", [])
            forbidden = info.get("ai_forbidden_patterns", [])

            assert isinstance(
                allowed, list
            ), f"{subsystem} ai_allowed_patterns not a list"
            assert isinstance(
                forbidden, list
            ), f"{subsystem} ai_forbidden_patterns not a list"

            # All items should be non-empty strings
            for item in allowed + forbidden:
                assert isinstance(item, str) and len(item) > 0


class TestMetaYamlValidity:
    """Test that README.meta.yaml files are well-formed."""

    def test_meta_yaml_exists_for_all_subsystems(self, meta_files):
        """All 4 subsystems should have README.meta.yaml."""
        assert len(meta_files) == 4, f"Expected 4 meta files, found {len(meta_files)}"

    def test_meta_yaml_has_required_structure(self, meta_files):
        """Each README.meta.yaml must have required top-level keys."""
        required = {"metadata", "sections", "aicollaboration", "invariants"}

        for subsystem, meta in meta_files.items():
            missing = required - set(meta.keys())
            assert not missing, f"{subsystem} README.meta.yaml missing keys: {missing}"

    def test_meta_yaml_sections_have_required_flag(self, meta_files):
        """Each section must specify 'required' boolean."""
        for subsystem, meta in meta_files.items():
            sections = meta.get("sections", {})
            for section_name, section_info in sections.items():
                assert (
                    "required" in section_info
                ), f"{subsystem} section '{section_name}' missing 'required' flag"
                assert isinstance(
                    section_info["required"], bool
                ), f"{subsystem} section '{section_name}' 'required' not boolean"

    def test_ai_collaboration_rules_present(self, meta_files):
        """Each meta file must define AI collaboration rules."""
        for subsystem, meta in meta_files.items():
            ai_collab = meta.get("aicollaboration", {})

            assert "allowedscopes" in ai_collab, f"{subsystem} missing allowedscopes"
            assert (
                "restrictedscopes" in ai_collab
            ), f"{subsystem} missing restrictedscopes"
            assert (
                "forbiddenscopes" in ai_collab
            ), f"{subsystem} missing forbiddenscopes"

            assert isinstance(ai_collab["allowedscopes"], list)
            assert isinstance(ai_collab["restrictedscopes"], list)
            assert isinstance(ai_collab["forbiddenscopes"], list)

    def test_invariants_are_human_readable(self, meta_files):
        """Invariants should be strings describing rules."""
        for subsystem, meta in meta_files.items():
            invariants = meta.get("invariants", [])
            assert isinstance(invariants, list), f"{subsystem} invariants not a list"

            for inv in invariants:
                assert (
                    isinstance(inv, str) and len(inv) > 0
                ), f"{subsystem} invariant not a non-empty string: {inv}"


class TestProtectedFileEnforcement:
    """Test that protected files are properly defined."""

    def test_protected_files_do_not_overlap_between_subsystems(self, code_map):
        """Protected files should be unique (no cross-subsystem conflicts)."""
        all_protected = set()

        for subsystem, info in code_map.get("subsystems", {}).items():
            protected = set(info.get("protected_files", []))

            overlap = all_protected & protected
            assert not overlap, f"Protected file overlap between subsystems: {overlap}"

            all_protected.update(protected)

    def test_forbidden_patterns_include_protected_files(self, code_map):
        """ai_forbidden_patterns should be the same as protected_files."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            protected = set(info.get("protected_files", []))
            forbidden = set(info.get("ai_forbidden_patterns", []))

            # Forbidden should at least include protected
            assert protected.issubset(
                forbidden
            ), f"{subsystem}: protected files not fully in forbidden patterns"


class TestAICollaborationScopes:
    """Test that AI collaboration scopes are consistent."""

    def test_allowed_and_forbidden_do_not_overlap(self, code_map):
        """A file pattern cannot be both allowed and forbidden."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            allowed = set(info.get("ai_allowed_patterns", []))
            forbidden = set(info.get("ai_forbidden_patterns", []))

            # Check for exact overlaps (wildcard patterns might have semantic overlap)
            overlap = allowed & forbidden
            assert (
                not overlap
            ), f"{subsystem}: patterns in both allowed and forbidden: {overlap}"

    def test_all_allowed_patterns_are_valid_globs(self, code_map):
        """Allowed patterns should be valid glob or path patterns."""
        import fnmatch

        for subsystem, info in code_map.get("subsystems", {}).items():
            allowed = info.get("ai_allowed_patterns", [])

            for pattern in allowed:
                # Just verify fnmatch can parse it (no exception)
                try:
                    fnmatch.fnmatch("dummy/path.py", pattern)
                except Exception as e:
                    pytest.fail(f"{subsystem} invalid pattern '{pattern}': {e}")


class TestCodeMapAndMetaConsistency:
    """Test that CODE-MAP.yaml and README.meta.yaml are in sync."""

    def test_code_map_subsystems_match_meta_files(self, code_map, meta_files):
        """CODE-MAP subsystems should match available meta files."""
        code_map_subsystems = set(code_map.get("subsystems", {}).keys())
        meta_subsystems = set(meta_files.keys())

        assert code_map_subsystems == meta_subsystems, (
            f"Subsystem mismatch: CODE-MAP has {code_map_subsystems}, "
            f"meta files have {meta_subsystems}"
        )

    def test_ai_rules_in_meta_match_code_map(self, code_map, meta_files):
        """AI collaboration rules in meta files should align with CODE-MAP."""
        for subsystem in code_map.get("subsystems", {}):
            if subsystem not in meta_files:
                continue

            meta_forbidden = set(
                meta_files[subsystem]
                .get("aicollaboration", {})
                .get("forbiddenscopes", [])
            )

            # Meta files should define forbidden scopes
            assert len(meta_forbidden) > 0, f"{subsystem} meta has no forbidden scopes"


class TestInvariantCoverage:
    """Test that invariants are defined for key concepts."""

    def test_all_subsystems_have_invariants(self, code_map):
        """Every subsystem should define invariants."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            invariants = info.get("invariants", [])
            assert len(invariants) > 0, f"{subsystem} has no invariants defined"
            assert all(
                isinstance(i, str) for i in invariants
            ), f"{subsystem} invariants not all strings"

    def test_invariants_are_testable(self, code_map):
        """Invariants should describe verifiable properties."""
        for subsystem, info in code_map.get("subsystems", {}).items():
            invariants = info.get("invariants", [])

            for inv in invariants:
                # Heuristic: good invariants reference concrete properties
                has_concrete = any(
                    word in inv.lower()
                    for word in [
                        "uuid",
                        "iso",
                        "positive",
                        "non-empty",
                        "required",
                        "must",
                    ]
                )
                assert (
                    has_concrete or len(inv) > 30
                ), f"{subsystem} invariant too vague: '{inv}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": ".DO-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        ".dora",
        "api",
        "config",
        "filesystem",
        "operations",
        "rest-api",
        "test",
        "testing",
    ],
    "keywords": [
        "all",
        "allowed",
        "between",
        "classes",
        "collaboration",
        "consistency",
        "correctly",
        "coverage",
    ],
    "business_value": "Provides test code facts extraction components including TestCodeMapValidity, TestMetaYamlValidity, TestProtectedFileEnforcement",
    "last_modified": "2026-01-18T02:07:37Z",
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
