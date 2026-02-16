#!/usr/bin/env python3
"""
CI Check: Dependency Access Patterns
=====================================

Enforces L9's chosen pattern for infrastructure client access:
- Routes MUST use lazy module singletons (get_redis(), get_neo4j())
- Routes MUST NOT use Depends(get_redis_client) or Depends(get_neo4j_client)

Decision: 2026-01-13
Rationale: Graceful degradation, lazy init, no lifespan dependency

Run: python ci/check_dependency_patterns.py
Exit: 0 = pass, 1 = violations found
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Dependency Patterns",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T15:33:14Z",
    "updated_at": "2026-01-14T13:06:25Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "check_dependency_patterns",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
import sys
from pathlib import Path

import structlog

# Pattern violations to detect

logger = structlog.get_logger(__name__)

FORBIDDEN_PATTERNS = [
    # Depends() injection of infrastructure clients
    (
        r"Depends\s*\(\s*get_redis_client\s*\)",
        "Use lazy import pattern (get_redis()) instead of Depends(get_redis_client)",
    ),
    (
        r"Depends\s*\(\s*get_neo4j_client\s*\)",
        "Use lazy import pattern (get_neo4j()) instead of Depends(get_neo4j_client)",
    ),
    # Direct import of these dependencies for Depends usage
    (
        r"from\s+api\.dependencies\s+import\s+[^#]*get_redis_client",
        "Don't import get_redis_client for routes - use lazy pattern",
    ),
    (
        r"from\s+api\.dependencies\s+import\s+[^#]*get_neo4j_client",
        "Don't import get_neo4j_client for routes - use lazy pattern",
    ),
]

# Directories to scan
SCAN_DIRS = [
    "api/",
    "api/memory/",
    "api/routes/",
]

# Files to exclude (scaffolding location is OK)
EXCLUDE_FILES = {
    "api/dependencies.py",  # Scaffolding definitions live here
}


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Check a single file for pattern violations.

    Returns list of (line_number, line_content, violation_message)
    """
    violations = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern, message in FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    violations.append((i, line.strip(), message))
    except Exception as e:
        logger.error("warning: could not read filepath: e", filepath=filepath, e=e)

    return violations


def main() -> int:
    """Run the dependency pattern check.

    Returns:
        0 if no violations, 1 if violations found
    """
    repo_root = Path(__file__).parent.parent

    all_violations: dict[str, list[tuple[int, str, str]]] = {}
    files_checked = 0

    for scan_dir in SCAN_DIRS:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.glob("*.py"):
            rel_path = str(filepath.relative_to(repo_root))

            # Skip excluded files
            if rel_path in EXCLUDE_FILES:
                continue

            files_checked += 1
            violations = check_file(filepath)

            if violations:
                all_violations[rel_path] = violations

    # Report results
    logger.info(
        "checked files checked files for dependency pattern violations",
        files_checked=files_checked,
    )
    if not all_violations:
        logger.info("✅ no dependency pattern violations found")
        return 0

    logger.info("❌ found violations in {len(all_violations)} files:")
    for filepath, violations in sorted(all_violations.items()):
        logger.info("  filepath:", filepath=filepath)
        for line_num, _line_content, message in violations:
            logger.info(
                "    line line num: message", line_num=line_num, message=message
            )
            logger.info("      > {line_content[:80]}...")
    logger.info("=" * 60)
    logger.info("dependency pattern enforcement")
    logger.info("=" * 60)
    logger.info("l9 routes must use lazy module singletons for redis/neo4j:")
    logger.info("  ✅ correct:")
    logger.info("     _client = none")
    logger.info("     async def get_redis():")
    logger.info("         global _client")
    logger.info("         if _client is none:")
    logger.info("             from runtime.redis_client import get_redis_client")
    logger.info("             _client = await get_redis_client()")
    logger.info("         return _client")
    logger.info("  ❌ wrong:")
    logger.info("     from api.dependencies import get_redis_client")
    logger.info("     @router.get(...)")
    logger.info("     async def route(client = depends(get_redis_client)):")
    logger.info("see: .cursor/rules/89-dependency-patterns.mdc")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "endpoint",
        "filesystem",
        "messaging",
        "operations",
        "router",
    ],
    "keywords": ["check", "dependency", "patterns", "redis", "route"],
    "business_value": "Utility module for check dependency patterns",
    "last_modified": "2026-01-14T13:06:25Z",
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
