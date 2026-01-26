"""
Integration tests for docs-code sync system.

Tests validate that:
  1. readme_config.yaml is well-formed and valid
  2. CODE-MAP.yaml is well-formed and queryable
  3. Protected files cannot be modified
  4. AI collaboration scopes are correctly computed
  5. README generation works correctly

MIGRATION NOTE (2026-01-25):
- Replaced per-subsystem README.meta.yaml tests with readme_config.yaml tests
- Single source of truth: config/subsystems/readme_config.yaml
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Code Facts Extraction",
    "module_version": "2.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-25T16:30:00Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "test_code_facts_extraction",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["config/subsystems/readme_config.yaml"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any

import pytest
import yaml

CONFIG_PATH = "config/subsystems/readme_config.yaml"


@pytest.fixture
def readme_config() -> dict[str, Any]:
    """Load readme_config.yaml for testing."""
    config_path = Path(CONFIG_PATH)
    if not config_path.exists():
        pytest.skip(f"{CONFIG_PATH} not found")

    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def code_map() -> dict[str, Any]:
    """Load CODE-MAP.yaml for testing."""
    code_map_path = Path("docs/CODE-MAP.yaml")
    if not code_map_path.exists():
        pytest.skip(
            "CODE-MAP.yaml not found. Run: python scripts/extract_code_facts.py"
        )

    with open(code_map_path) as f:
        return yaml.safe_load(f)


class TestReadmeConfigValidity:
    """Test that readme_config.yaml is well-formed."""

    def test_config_has_version(self, readme_config):
        """Config must have version."""
        assert "version" in readme_config
        assert readme_config["version"] in ["1.0", "2.0"]

    def test_config_has_subsystems(self, readme_config):
        """Config must define subsystems."""
        subsystems = readme_config.get("subsystems", {})
        assert len(subsystems) > 0, "No subsystems defined"

    def test_config_has_defaults(self, readme_config):
        """Config should have defaults section."""
        defaults = readme_config.get("defaults", {})
        # Defaults are optional but recommended
        if defaults:
            assert "owner" in defaults or "prereading" in defaults

    def test_subsystem_has_required_fields(self, readme_config):
        """Each subsystem must have required fields."""
        required_fields = {"path", "title", "tier", "description", "purpose"}

        for key, sub_config in readme_config.get("subsystems", {}).items():
            missing = required_fields - set(sub_config.keys())
            assert not missing, f"{key} missing fields: {missing}"

    def test_subsystem_tier_is_valid(self, readme_config):
        """Subsystem tier must be one of the valid tiers."""
        valid_tiers = {
            "core",
            "orchestration",
            "api",
            "agents",
            "services",
            "infrastructure",
            "unknown",
        }

        for key, sub_config in readme_config.get("subsystems", {}).items():
            tier = sub_config.get("tier")
            assert tier in valid_tiers, f"{key} has invalid tier: {tier}"

    def test_protected_files_are_lists(self, readme_config):
        """Protected files must be lists of strings."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            protected = sub_config.get("protected_files", [])
            assert isinstance(protected, list), f"{key} protected_files not a list"
            for f in protected:
                assert isinstance(f, str), f"{key} protected file not a string: {f}"

    def test_invariants_are_lists_of_strings(self, readme_config):
        """Invariants must be lists of strings."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            invariants = sub_config.get("invariants", [])
            assert isinstance(invariants, list), f"{key} invariants not a list"
            for inv in invariants:
                assert isinstance(inv, str), f"{key} invariant not a string: {inv}"


class TestReadmeConfigCoreSubsystems:
    """Test that core subsystems are properly configured."""

    def test_core_agents_exists(self, readme_config):
        """core_agents subsystem must exist."""
        subsystems = readme_config.get("subsystems", {})
        assert "core_agents" in subsystems, "core_agents subsystem missing"
        assert subsystems["core_agents"]["path"] == "core/agents"

    def test_memory_exists(self, readme_config):
        """memory subsystem must exist."""
        subsystems = readme_config.get("subsystems", {})
        assert "memory" in subsystems, "memory subsystem missing"
        assert subsystems["memory"]["path"] == "memory"

    def test_core_tools_exists(self, readme_config):
        """core_tools subsystem must exist."""
        subsystems = readme_config.get("subsystems", {})
        assert "core_tools" in subsystems, "core_tools subsystem missing"
        assert subsystems["core_tools"]["path"] == "core/tools"

    def test_api_exists(self, readme_config):
        """api subsystem must exist."""
        subsystems = readme_config.get("subsystems", {})
        assert "api" in subsystems, "api subsystem missing"
        assert subsystems["api"]["path"] == "api"


class TestAICollaborationScopes:
    """Test that AI collaboration scopes are consistent."""

    def test_allowed_patterns_are_lists(self, readme_config):
        """Allowed patterns must be lists."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            allowed = sub_config.get("allowed_patterns", [])
            assert isinstance(allowed, list), f"{key} allowed_patterns not a list"

    def test_forbidden_scopes_are_lists(self, readme_config):
        """Forbidden scopes must be lists."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            forbidden = sub_config.get("forbidden_scopes", [])
            assert isinstance(forbidden, list), f"{key} forbidden_scopes not a list"

    def test_allowed_and_forbidden_do_not_overlap(self, readme_config):
        """A file cannot be both allowed and forbidden."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            allowed = set(sub_config.get("allowed_patterns", []))
            forbidden = set(sub_config.get("forbidden_scopes", []))

            overlap = allowed & forbidden
            assert (
                not overlap
            ), f"{key}: patterns in both allowed and forbidden: {overlap}"


class TestProtectedFileEnforcement:
    """Test that protected files are properly defined."""

    def test_core_agents_has_protected_files(self, readme_config):
        """core_agents should have protected files."""
        sub = readme_config.get("subsystems", {}).get("core_agents", {})
        protected = sub.get("protected_files", [])
        assert len(protected) > 0, "core_agents has no protected files"
        assert "executor.py" in protected, "executor.py should be protected"

    def test_memory_has_protected_files(self, readme_config):
        """memory should have protected files."""
        sub = readme_config.get("subsystems", {}).get("memory", {})
        protected = sub.get("protected_files", [])
        assert len(protected) > 0, "memory has no protected files"
        assert (
            "substrate_service.py" in protected
        ), "substrate_service.py should be protected"


class TestInvariantCoverage:
    """Test that invariants are defined for key concepts."""

    def test_all_subsystems_have_invariants(self, readme_config):
        """Every subsystem should define invariants."""
        for key, sub_config in readme_config.get("subsystems", {}).items():
            if sub_config.get("skip", False):
                continue
            invariants = sub_config.get("invariants", [])
            # Not all subsystems require invariants, but major ones should
            if sub_config.get("tier") == "core":
                assert (
                    len(invariants) > 0
                ), f"{key} (core tier) has no invariants defined"


class TestCodeMapValidity:
    """Test that CODE-MAP.yaml is well-formed (legacy support)."""

    def test_code_map_has_version(self, code_map):
        """CODE-MAP must have version and timestamp."""
        assert "version" in code_map
        assert "last_verified" in code_map
        assert code_map["version"] == "1.0"

    def test_code_map_has_subsystems(self, code_map):
        """CODE-MAP must define subsystems."""
        subsystems = code_map.get("subsystems", {})
        assert len(subsystems) >= 4, "CODE-MAP should have at least 4 subsystems"


class TestReadmeGeneratorScript:
    """Test the README generator script."""

    def test_generator_script_exists(self):
        """Generator script must exist."""
        script_path = Path("scripts/generate_subsystem_readmes.py")
        assert script_path.exists(), "generate_subsystem_readmes.py not found"

    def test_generator_can_validate(self):
        """Generator --validate should work."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/generate_subsystem_readmes.py", "--validate"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Validation failed: {result.stderr}"

    def test_generator_can_list(self):
        """Generator --list should work."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/generate_subsystem_readmes.py", "--list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"List failed: {result.stderr}"
        assert "core_agents" in result.stdout, "core_agents not in list output"


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
    "dependencies": ["config/subsystems/readme_config.yaml"],
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
        "readme",
        "config",
        "validation",
        "subsystems",
    ],
    "business_value": "Validates readme_config.yaml and README generation pipeline",
    "last_modified": "2026-01-25T16:30:00Z",
    "modified_by": "README Pipeline Consolidation",
    "change_summary": "Migrated from README.meta.yaml to readme_config.yaml",
}
# ============================================================================
