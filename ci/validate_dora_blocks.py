#!/usr/bin/env python3
"""
DORA Block Validator
Validates DORA blocks in all generated files

Usage:
    python validate_dora_blocks.py [--directory .] [--strict] [--fix]
"""

import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

# ============================================================================
# CONFIGURATION
# ============================================================================

MANDATORY_FIELDS = {
    "component_id": r"^[A-Z]{3}-[A-Z]{3,4}-\d{3}$",
    "component_name": r"^[A-Za-z0-9\s\-]{2,100}$",
    "module_version": r"^\d+\.\d+\.\d+$",
    "created_at": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
    "created_by": r"^[A-Za-z0-9_\s\-\.]{1,100}$",
    "layer": r"^(foundation|intelligence|operations|learning|security)$",
    "domain": r"^[a-z0-9_\-]{2,100}$",
    "type": r"^(service|collector|tracker|engine|utility|adapter|schema|config)$",
    "status": r"^(active|deprecated|experimental|maintenance)$",
    "governance_level": r"^(critical|high|medium|low)$",
    "compliance_required": r"^(true|false|True|False)$",
    "audit_trail": r"^(true|false|True|False)$",
    "purpose": r"^.{10,200}$",
    "dependencies": r"^(\[.*\]|[\[{].*)$",  # JSON array or dict-like
}

CRITICAL_DOMAINS = ["governance", "memory", "agents", "kernel", "kernel_loader"]

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/dora-validation.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# ============================================================================
# DORA BLOCK PARSING
# ============================================================================


def extract_dora_block_from_python(content: str) -> dict | None:
    """Extract DORA block from Python file."""
    match = re.search(r"__dora_block__\s*=\s*(\{.*?\})", content, re.DOTALL)
    if match:
        try:
            return eval(match.group(1))
        except Exception as e:
            logger.error(f"Failed to parse Python DORA block: {e}")
            return None
    return None


def extract_dora_block_from_yaml(content: str) -> dict | None:
    """Extract DORA block from YAML file."""
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict) and "dora_block" in data:
            return data["dora_block"]
    except Exception as e:
        logger.error(f"Failed to parse YAML DORA block: {e}")
    return None


def extract_dora_block_from_json(content: str) -> dict | None:
    """Extract DORA block from JSON file."""
    try:
        data = json.loads(content)
        if "_dora_block" in data:
            return data["_dora_block"]
    except Exception as e:
        logger.error(f"Failed to parse JSON DORA block: {e}")
    return None


def extract_dora_block_from_markdown(content: str) -> dict | None:
    """Extract DORA block from Markdown file (YAML frontmatter)."""
    if content.startswith("---"):
        try:
            # Extract content between first and second ---
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = yaml.safe_load(parts[1])
                if isinstance(frontmatter, dict) and "dora_block" in frontmatter:
                    return frontmatter["dora_block"]
        except Exception as e:
            logger.error(f"Failed to parse Markdown DORA block: {e}")
    return None


def extract_dora_block(file_path: Path) -> dict | None:
    """Extract DORA block from file based on file type."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Cannot read file {file_path}: {e}")
        return None

    suffix = file_path.suffix.lower()

    if suffix == ".py":
        return extract_dora_block_from_python(content)
    if suffix in [".yaml", ".yml"]:
        return extract_dora_block_from_yaml(content)
    if suffix == ".json":
        return extract_dora_block_from_json(content)
    if suffix == ".md":
        return extract_dora_block_from_markdown(content)

    return None


# ============================================================================
# VALIDATION
# ============================================================================


def validate_dora_field(field_name: str, field_value: any) -> tuple[bool, str | None]:
    """Validate a single DORA field against pattern."""
    if field_name not in MANDATORY_FIELDS:
        return True, None  # Optional field, skip

    pattern = MANDATORY_FIELDS[field_name]

    # Check for empty/placeholder
    if field_value is None or field_value == "":
        return False, f"Field '{field_name}' is empty"

    if isinstance(field_value, str):
        if "{" in field_value or "TODO" in field_value or "FILL_IN" in field_value:
            return False, f"Field '{field_name}' contains placeholder: {field_value}"

    # Validate against pattern
    if not re.match(pattern, str(field_value)):
        return (
            False,
            f"Field '{field_name}' value '{field_value}' does not match pattern '{pattern}'",
        )

    return True, None


def validate_dora_block(dora_block: dict, file_path: Path) -> tuple[bool, list[str]]:
    """Validate entire DORA block."""
    errors = []

    # Check all mandatory fields are present
    for field in MANDATORY_FIELDS:
        if field not in dora_block:
            errors.append(f"Missing mandatory field: {field}")

    # Validate each field
    for field_name, field_value in dora_block.items():
        valid, error = validate_dora_field(field_name, field_value)
        if not valid:
            errors.append(error)

    # Governance check for critical domains
    if "domain" in dora_block and "governance_level" in dora_block:
        domain = dora_block["domain"]
        gov_level = dora_block["governance_level"]

        if domain in CRITICAL_DOMAINS and gov_level not in ["critical", "high"]:
            errors.append(
                f"Domain '{domain}' is critical but governance_level is '{gov_level}'. "
                f"Must be 'critical' or 'high'"
            )

    return len(errors) == 0, errors


def check_unique_component_id(
    component_id: str, registry: dict
) -> tuple[bool, str | None]:
    """Check if component_id is globally unique."""
    if component_id in registry:
        return (
            False,
            f"component_id '{component_id}' already exists in {registry[component_id]['file_path']}",
        )
    return True, None


# ============================================================================
# MAIN VALIDATION LOGIC
# ============================================================================


def validate_file(file_path: Path, registry: dict) -> tuple[bool, dict]:
    """Validate a single file."""
    result = {
        "file_path": str(file_path),
        "status": "PASS",
        "errors": [],
        "component_id": None,
        "governance_level": None,
    }

    # Extract DORA block
    dora_block = extract_dora_block(file_path)

    if dora_block is None:
        result["status"] = "FAIL"
        result["errors"].append("No DORA block found in file")
        return False, result

    # Validate DORA block
    valid, errors = validate_dora_block(dora_block, file_path)

    if not valid:
        result["status"] = "FAIL"
        result["errors"] = errors
        return False, result

    # Extract component_id and governance_level
    component_id = dora_block.get("component_id")
    governance_level = dora_block.get("governance_level")

    result["component_id"] = component_id
    result["governance_level"] = governance_level

    # Check uniqueness
    if component_id:
        unique, error = check_unique_component_id(component_id, registry)
        if not unique:
            result["status"] = "FAIL"
            result["errors"].append(error)
            return False, result

    return True, result


def validate_directory(directory: str = ".") -> tuple[int, int, list[dict]]:
    """Validate all files in directory."""
    registry = {}
    results = []
    passed = 0
    failed = 0

    # Load existing registry if present
    registry_file = Path(directory) / ".l9-dora-registry.json"
    if registry_file.exists():
        try:
            with open(registry_file) as f:
                json.load(f)
                # Skip current files for uniqueness check (will re-add)
                registry = {}
        except Exception as e:
            logger.warning(f"Cannot load registry: {e}")

    # Scan all files
    for file_path in Path(directory).rglob("*"):
        if file_path.is_file() and file_path.suffix in [
            ".py",
            ".yaml",
            ".yml",
            ".md",
            ".json",
        ]:
            # Skip certain directories
            if any(
                part in file_path.parts
                for part in [".git", "__pycache__", ".venv", "node_modules"]
            ):
                continue

            valid, result = validate_file(file_path, registry)

            if valid:
                passed += 1
                logger.info(f"✓ {file_path}: {result['component_id']}")
            else:
                failed += 1
                logger.error(f"✗ {file_path}:")
                for error in result["errors"]:
                    logger.error(f"  - {error}")

            results.append(result)

            # Add to registry
            if result["component_id"]:
                registry[result["component_id"]] = {
                    "file_path": str(file_path),
                    "governance_level": result["governance_level"],
                    "last_validated": datetime.now(UTC).isoformat(),
                }

    # Update registry file
    try:
        os.makedirs(".", exist_ok=True)
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        logger.info(f"Updated registry: {registry_file}")
    except Exception as e:
        logger.error(f"Cannot update registry: {e}")

    return passed, failed, results


# ============================================================================
# MAIN
# ============================================================================


def main():
    """
    Validates DORA blocks within generated files to ensure compliance with standards.

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: If argument parsing fails or validation encounters a critical error.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate DORA blocks in generated files"
    )
    parser.add_argument(
        "--directory", default=".", help="Directory to scan (default: .)"
    )
    parser.add_argument("--strict", action="store_true", help="Fail on any warning")
    parser.add_argument("--report", action="store_true", help="Generate HTML report")
    args = parser.parse_args()

    logger.info(f"Validating DORA blocks in {args.directory}")

    passed, failed, _results = validate_directory(args.directory)

    logger.info(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        logger.error("DORA validation FAILED")
        return 1

    logger.info("DORA validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
