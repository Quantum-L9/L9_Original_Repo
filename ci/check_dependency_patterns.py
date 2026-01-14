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

import re
import sys
from pathlib import Path

# Pattern violations to detect
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
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    
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
    print(f"Checked {files_checked} files for dependency pattern violations")
    print()
    
    if not all_violations:
        print("✅ No dependency pattern violations found")
        return 0
    
    print(f"❌ Found violations in {len(all_violations)} files:")
    print()
    
    for filepath, violations in sorted(all_violations.items()):
        print(f"  {filepath}:")
        for line_num, line_content, message in violations:
            print(f"    Line {line_num}: {message}")
            print(f"      > {line_content[:80]}...")
        print()
    
    print("=" * 60)
    print("DEPENDENCY PATTERN ENFORCEMENT")
    print("=" * 60)
    print()
    print("L9 routes must use LAZY MODULE SINGLETONS for Redis/Neo4j:")
    print()
    print("  ✅ CORRECT:")
    print("     _client = None")
    print("     async def get_redis():")
    print("         global _client")
    print("         if _client is None:")
    print("             from runtime.redis_client import get_redis_client")
    print("             _client = await get_redis_client()")
    print("         return _client")
    print()
    print("  ❌ WRONG:")
    print("     from api.dependencies import get_redis_client")
    print("     @router.get(...)")
    print("     async def route(client = Depends(get_redis_client)):")
    print()
    print("See: .cursor/rules/89-dependency-patterns.mdc")
    print()
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
