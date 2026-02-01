"""
Base Extractor Class

All extractors inherit from this base class to ensure consistent interface.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Base Extractor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-13T13:27:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "base_extractor",
    "type": "abstract",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import logging  # noqa: ADR-0019
from abc import (  # noqa: ADR-0026 - ABC provides shared implementation
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import Any


class BaseExtractor(ABC):
    """Base class for all extractors."""

    def __init__(self, config: dict, logger: logging.Logger):
        """
        Initialize base extractor.

        Args:
            config: Suite configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.name = self.__class__.__name__

    @abstractmethod
    def extract(self, input_path: Path, output_root: Path) -> dict[str, Any]:
        """
        Extract data from input file.

        Args:
            input_path: Path to input file
            output_root: Root output directory (Extracted Files/)

        Returns:
            Dict with extraction results:
            {
                'success': bool,
                'files_extracted': int,
                'output_path': str,
                'errors': List[str]
            }
        """
        pass

    def get_config(self, key: str) -> Any:
        """Get extractor-specific configuration."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get(key)

    def is_enabled(self) -> bool:
        """Check if this extractor is enabled."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get("enabled", False)

    def create_output_dir(self, output_root: Path, subdir: str = "") -> Path:
        """
        Create output directory for this extractor.

        Args:
            output_root: Root output directory
            subdir: Optional subdirectory name

        Returns:
            Path to output directory
        """
        output_dir = output_root / subdir if subdir else output_root

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-056",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["abstract", "filesystem", "learning", "memory-substrate"],
    "keywords": ["create", "dir", "enabled", "extract", "extractor"],
    "business_value": "Implements BaseExtractor for base extractor functionality",
    "last_modified": "2026-01-13T13:27:56Z",
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
