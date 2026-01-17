"""
Phase 1: Load & Parse Kernels

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Load all 10 kernels from YAML, parse into memory structures, validate syntax.
"""

from __future__ import annotations

from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
import hashlib

import yaml
import structlog
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class KernelParsed:
    """Parsed kernel representation"""

    name: str
    rules: Dict[str, Any]
    version: str
    hash: str  # SHA256 of original YAML
    raw_content: Dict[str, Any] = None  # Full parsed YAML


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
) -> Dict[str, KernelParsed]:
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
            raise ValueError(f"{kernel_file}: Invalid YAML: {e}")
        except Exception as e:
            logger.error("Failed to load kernel", kernel_file=kernel_file, error=str(e))
            raise RuntimeError(f"{kernel_file}: Failed to load: {e}")

    logger.info("All kernels loaded and parsed", kernel_count=len(kernels))
    return kernels
