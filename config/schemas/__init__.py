"""
L9 Config Schemas Package
Version: 1.0.0

Configuration schemas for L9 governance, ADRs, and other structured data.

SCHEMAS
=======
- adr_schema.yaml: Canonical format for Architecture Decision Records
"""

from pathlib import Path

__dora_meta__ = {
    "component_name": "Config Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:00:00Z",
    "updated_at": "2026-01-20T00:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "config.schemas",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.governance.session_startup"],
    },
}

SCHEMAS_DIR = Path(__file__).parent


def get_adr_schema_path() -> Path:
    """Get path to ADR schema YAML."""
    return SCHEMAS_DIR / "adr_schema.yaml"


__all__ = ["SCHEMAS_DIR", "get_adr_schema_path"]
