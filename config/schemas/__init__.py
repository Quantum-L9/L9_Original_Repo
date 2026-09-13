"""
L9 Config Schemas Package
Version: 1.0.0

Configuration schemas for L9 governance, ADRs, and other structured data.

SCHEMAS
=======
- adr_schema.yaml: Canonical format for Architecture Decision Records
"""

from pathlib import Path


SCHEMAS_DIR = Path(__file__).parent


def get_adr_schema_path() -> Path:
    """Get path to ADR schema YAML."""
    return SCHEMAS_DIR / "adr_schema.yaml"


__all__ = ["SCHEMAS_DIR", "get_adr_schema_path"]
# Runtime execution trace - updated automatically on every execution
