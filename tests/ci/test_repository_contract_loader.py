"""Unit tests for the repository contract catalog loader.

Validates YAML loading, schema enforcement, and structural invariants
for the contract catalog used by ``test_repository_contract_calls.py``.
"""
from __future__ import annotations

import pathlib
import textwrap

import pytest

from tests.ci._repository_contract_loader import (
    CatalogValidationError,
    ContractCatalog,
    ContractPair,
    load_catalog,
)


@pytest.fixture()
def tmp_catalog(tmp_path: pathlib.Path):
    """Factory fixture: write YAML content and return the file path."""

    def _write(content: str) -> pathlib.Path:
        p = tmp_path / "test_catalog.yaml"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    return _write


class TestCatalogLoading:
    """Tests for successful catalog loading."""

    def test_minimal_valid_catalog(self, tmp_catalog) -> None:
        """A minimal valid YAML catalog loads without error."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: test_method
                param: test_param
                allowed_literals: ["a", "b"]
                dynamic_policy: hybrid_warn
                severity: error
                description: test pair
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        catalog = load_catalog(path)
        assert isinstance(catalog, ContractCatalog)
        assert catalog.schema_version == "1.0.0"
        assert len(catalog.pairs) == 1
        assert catalog.pairs[0].method == "test_method"
        assert catalog.pairs[0].param == "test_param"
        assert catalog.pairs[0].allowed_literals == ["a", "b"]

    def test_multiple_pairs_load(self, tmp_catalog) -> None:
        """Catalog with multiple distinct pairs loads correctly."""
        path = tmp_catalog("""
            schema_version: "2.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m1
                param: p1
                allowed_literals: ["x"]
                dynamic_policy: hybrid_warn
                severity: error
              - method: m2
                param: p2
                allowed_literals: ["y", "z"]
                dynamic_policy: hybrid_warn
                severity: warning
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 5
              drift_policy: warn
        """)
        catalog = load_catalog(path)
        assert len(catalog.pairs) == 2
        assert catalog.pairs[1].allowed_literals == ["y", "z"]

    def test_dynamic_sources_parsed(self, tmp_catalog) -> None:
        """Dynamic source patterns are parsed into typed objects."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                param: p
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns:
                - kind: enum_member
                  pattern: "PacketType.*"
                  trust_level: proven
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        catalog = load_catalog(path)
        assert len(catalog.dynamic_sources) == 1
        assert catalog.dynamic_sources[0].kind == "enum_member"
        assert catalog.dynamic_sources[0].trust_level == "proven"

    def test_stage2_fields_loaded(self, tmp_catalog) -> None:
        """S2-4/S2-6 fields (param_position, baseline_callsites, drift_threshold_percent) load."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: insert_semantic_embedding
                param: scope
                allowed_literals: ["developer", "global"]
                dynamic_policy: hybrid_warn
                severity: error
                param_position: 3
                baseline_callsites: 12
                drift_threshold_percent: 15
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        catalog = load_catalog(path)
        pair = catalog.pairs[0]
        assert pair.param_position == 3
        assert pair.baseline_callsites == 12
        assert pair.drift_threshold_percent == 15

    def test_stage2_fields_default(self, tmp_catalog) -> None:
        """S2-4/S2-6 fields default correctly when omitted from YAML."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                param: p
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        catalog = load_catalog(path)
        pair = catalog.pairs[0]
        assert pair.param_position is None
        assert pair.baseline_callsites is None
        assert pair.drift_threshold_percent == 25


class TestCatalogValidationErrors:
    """Tests for structural validation failures."""

    def test_missing_required_top_key(self, tmp_catalog) -> None:
        """Missing top-level key raises ``CatalogValidationError``."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                param: p
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
        """)
        with pytest.raises(CatalogValidationError, match="Missing required top-level keys"):
            load_catalog(path)

    def test_duplicate_method_param_rejected(self, tmp_catalog) -> None:
        """Duplicate ``(method, param)`` pair raises ``CatalogValidationError``."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: emit_packet
                param: packet_type
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
              - method: emit_packet
                param: packet_type
                allowed_literals: ["b"]
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        with pytest.raises(CatalogValidationError, match="Duplicate"):
            load_catalog(path)

    def test_empty_allowlist_rejected(self, tmp_catalog) -> None:
        """Pair with empty ``allowed_literals`` raises ``CatalogValidationError``."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                param: p
                allowed_literals: []
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        with pytest.raises(CatalogValidationError, match="non-empty"):
            load_catalog(path)

    def test_missing_pair_required_key(self, tmp_catalog) -> None:
        """Pair missing a required key raises ``CatalogValidationError``."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: ["**/*.py"]
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        with pytest.raises(CatalogValidationError, match="missing required key"):
            load_catalog(path)

    def test_empty_include_globs_rejected(self, tmp_catalog) -> None:
        """Empty ``include_globs`` raises ``CatalogValidationError``."""
        path = tmp_catalog("""
            schema_version: "1.0.0"
            scan:
              include_globs: []
              exclude_globs: [".venv/**"]
            pairs:
              - method: m
                param: p
                allowed_literals: ["a"]
                dynamic_policy: hybrid_warn
                severity: error
            dynamic_sources:
              allow_patterns: []
            baseline:
              file: ""
              drift_threshold_percent: 10
              drift_policy: warn
        """)
        with pytest.raises(CatalogValidationError, match="non-empty"):
            load_catalog(path)

    def test_nonexistent_file_raises(self) -> None:
        """Loading from a path that does not exist raises ``FileNotFoundError``."""
        fake = pathlib.Path("/nonexistent/catalog.yaml")
        with pytest.raises(FileNotFoundError):
            load_catalog(fake)

    def test_non_mapping_root_rejected(self, tmp_catalog) -> None:
        """YAML root that is not a mapping raises ``CatalogValidationError``."""
        path = tmp_catalog("- just a list")
        with pytest.raises(CatalogValidationError, match="mapping"):
            load_catalog(path)
