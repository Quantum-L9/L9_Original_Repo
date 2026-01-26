"""
Phase 1: Load & Parse Kernels

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Load all 10 kernels from YAML, parse into memory structures, validate syntax.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 1 Load Kernels",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_1_load_kernels",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.core.bootstrap.test_bootstrap_phases"],
    },
}
# ============================================================================

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class KernelParsed:
    """Parsed kernel representation"""

    name: str
    rules: dict[str, Any]
    version: str
    hash: str  # SHA256 of original YAML
    raw_content: dict[str, Any] = None  # Full parsed YAML


KERNEL_ORDER = [
    "01_master_kernel.yaml",
    "02_identity_kernel.yaml",
    "03_cognitive_kernel.yaml",
    "04_behavioral_kernel.yaml",
    "05_memory_kernel.yaml",
    "06_worldmodel_kernel.yaml",
    "07_execution_kernel.yaml",
    "08_safety_kernel.yaml",
    "09_developer_kernel.yaml",
    "10_packet_protocol_kernel.yaml",
]


@must_stay_async("callers use await")
async def load_and_parse_kernels(
    kernel_dir: str = "private/kernels/00_system",
) -> dict[str, KernelParsed]:
    """
    Load and parse all 10 kernels from YAML.

    Returns:
        Dict mapping kernel name to parsed structure
    """
    kernels = {}
    kernel_path_base = Path(kernel_dir)

    for kernel_file in KERNEL_ORDER:
        kernel_path = kernel_path_base / kernel_file

        if not kernel_path.exists():
            logger.warning(
                "Kernel file not found, skipping",
                kernel_file=kernel_file,
                path=str(kernel_path),
            )
            continue

        try:
            # Read YAML
            file_content = kernel_path.read_text()
            kernel_data = yaml.safe_load(file_content)

            if not kernel_data:
                logger.warning("Empty kernel file", kernel_file=kernel_file)
                continue

            # Get name (may be in different fields)
            kernel_name = (
                kernel_data.get("name")
                or kernel_data.get("kernel_name")
                or kernel_file.replace(".yaml", "")
            )

            # Get version
            kernel_version = str(kernel_data.get("version", "1.0"))

            # Compute hash for integrity
            file_hash = hashlib.sha256(file_content.encode()).hexdigest()

            kernels[kernel_name] = KernelParsed(
                name=kernel_name,
                rules=kernel_data.get("rules", kernel_data.get("directives", {})),
                version=kernel_version,
                hash=file_hash,
                raw_content=kernel_data,
            )

            logger.info(
                "Loaded kernel",
                name=kernel_name,
                version=kernel_version,
                hash_prefix=file_hash[:8],
            )

        except yaml.YAMLError as e:
            logger.error(
                "Invalid YAML in kernel", kernel_file=kernel_file, error=str(e)
            )
            raise ValueError(f"{kernel_file}: Invalid YAML: {e}") from e
        except Exception as e:
            logger.error("Failed to load kernel", kernel_file=kernel_file, error=str(e))
            raise RuntimeError(f"{kernel_file}: Failed to load: {e}") from e

    logger.info("All kernels loaded and parsed", kernel_count=len(kernels))
    return kernels


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-043",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "agent-execution",
        "async",
        "config",
        "dataclass",
        "filesystem",
        "foundation",
        "logging",
        "security",
    ],
    "keywords": [
        "agent",
        "kernel",
        "kernels",
        "load",
        "memory",
        "parse",
        "parsed",
        "phase",
    ],
    "business_value": "Implements KernelParsed for phase 1 load kernels functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
