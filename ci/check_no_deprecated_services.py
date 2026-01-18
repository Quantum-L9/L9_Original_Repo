#!/usr/bin/env python3
"""
L9 CI Gate: No Deprecated Services (Supabase, n8n)
===================================================

Ensures deprecated services (supabase, n8n) are not imported,
referenced, or configured anywhere in the codebase.

These services have been removed from L9 architecture.
Any references indicate incomplete migration or accidental reintroduction.

Usage:
    python ci/check_no_deprecated_services.py

Exit codes:
    0 = All checks passed (no deprecated service references)
    1 = Violations detected

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Check No Deprecated Services",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_no_deprecated_services",
    "type": "cli",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["episodic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import re
import sys
from pathlib import Path
from typing import NamedTuple

import structlog

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = structlog.get_logger(__name__)


class Violation(NamedTuple):
    """A single violation found in the codebase."""
    file: Path
    line_num: int
    pattern: str
    line_content: str


# =============================================================================
# FORBIDDEN PATTERNS
# =============================================================================

FORBIDDEN_PATTERNS = {
    # Supabase patterns
    "supabase": [
        r"\bsupabase\b",              # Any word "supabase"
        r"\bSupabase\b",              # Capitalized
        r"SUPABASE_",                 # Env vars like SUPABASE_URL
        r"supabase\.co",              # Supabase domain
        r"supabase-py",               # Package name
        r"from\s+supabase",           # Import statement
        r"import\s+supabase",         # Import statement
    ],
    # n8n patterns
    "n8n": [
        r"\bn8n\b",                   # Any word "n8n"
        r"\bN8N\b",                   # Uppercase
        r"N8N_",                      # Env vars like N8N_URL
        r"n8n\.io",                   # n8n domain
        r"n8n\.cloud",                # n8n cloud domain
        r"n8n-workflow",              # n8n workflow references
    ],
}

# =============================================================================
# SCAN CONFIGURATION
# =============================================================================

# Directories to scan
SCAN_DIRS = [
    "api",
    "core", 
    "runtime",
    "services",
    "orchestration",
    "memory",
    "agents",
    "config",
    "scripts",
    "tests",
    "mcp_memory",
    "world_model",
    "email_agent",
    "clients",
]

# File extensions to check
SCAN_EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".env", ".txt"}

# Directories to exclude
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "archive",
    ".cursor",
    "docs",  # Allow in docs for historical references
}

# Files to exclude (exact matches or patterns)
EXCLUDE_FILES = {
    "check_no_deprecated_services.py",  # This file itself
    "CHANGELOG.md",
    "MIGRATION.md",
}

# Directories that contain historical/documentation content (allowed to reference deprecated services)
DOCUMENTATION_DIRS = {
    "inbox",           # Historical chat logs
    "extractor",       # Legacy extractor docs
    "chat_history",    # Chat history files
}

# Files that document anti-patterns (allowed to mention deprecated services as examples of what NOT to do)
ANTI_PATTERN_FILES = {
    "mistake_prevention.py",
    "quick_fixes.py",
    "credentials_policy.py",
}


# =============================================================================
# DETECTION LOGIC
# =============================================================================


def should_scan_file(file_path: Path) -> bool:
    """Determine if a file should be scanned."""
    # Check extension
    if file_path.suffix not in SCAN_EXTENSIONS:
        return False
    
    # Check excluded directories
    path_str = str(file_path)
    for excl_dir in EXCLUDE_DIRS:
        if f"/{excl_dir}/" in path_str or path_str.startswith(f"{excl_dir}/"):
            return False
    
    # Check documentation directories (historical content allowed)
    for doc_dir in DOCUMENTATION_DIRS:
        if f"/{doc_dir}/" in path_str:
            return False
    
    # Check excluded files
    if file_path.name in EXCLUDE_FILES:
        return False
    
    # Check anti-pattern documentation files (allowed to document what NOT to do)
    if file_path.name in ANTI_PATTERN_FILES:
        return False
    
    return True


def scan_file(file_path: Path) -> list[Violation]:
    """Scan a single file for forbidden patterns."""
    violations: list[Violation] = []
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            # Skip comments in Python files
            stripped = line.strip()
            if file_path.suffix == ".py" and stripped.startswith("#"):
                # Allow comments that explain WHY something was removed
                if "removed" in stripped.lower() or "deprecated" in stripped.lower():
                    continue
            
            # Check all forbidden patterns
            for service_name, patterns in FORBIDDEN_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append(Violation(
                            file=file_path,
                            line_num=line_num,
                            pattern=f"{service_name}: {pattern}",
                            line_content=line.strip()[:100],  # Truncate long lines
                        ))
                        break  # One violation per line per service is enough
                        
    except Exception as e:
        logger.info(f"   ⚠️  Could not read {file_path}: {e}")
    
    return violations


def check_no_deprecated_services() -> tuple[bool, list[Violation]]:
    """
    Check that no deprecated services are referenced in codebase.
    
    Returns:
        Tuple of (all_passed, list of violations)
    """
    all_violations: list[Violation] = []
    files_scanned = 0
    
    logger.info("\n🔍 Scanning for deprecated service references...")
    logger.info("   Forbidden: supabase, n8n")
    logger.info(f"   Scanning: {', '.join(SCAN_DIRS)}")
    
    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            if not should_scan_file(file_path):
                continue
            
            violations = scan_file(file_path)
            all_violations.extend(violations)
            files_scanned += 1
    
    # Also check root-level config files
    root_configs = ["docker-compose.yml", "docker-compose.yaml", ".env.example", "requirements.txt"]
    for config_name in root_configs:
        config_path = PROJECT_ROOT / config_name
        if config_path.exists() and should_scan_file(config_path):
            violations = scan_file(config_path)
            all_violations.extend(violations)
            files_scanned += 1
    
    logger.info(f"   Files scanned: {files_scanned}")
    
    return len(all_violations) == 0, all_violations


def main() -> int:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("🔧 L9 CI GATE: No Deprecated Services (Supabase, n8n)")
    logger.info("=" * 60)
    
    passed, violations = check_no_deprecated_services()
    
    if passed:
        logger.info("\n" + "=" * 60)
        logger.info("✅ CI GATE PASSED: No deprecated service references found")
        logger.info("=" * 60 + "\n")
        return 0
    else:
        logger.info("\n" + "=" * 60)
        logger.info(f"❌ CI GATE FAILED: {len(violations)} violation(s) found")
        logger.info("=" * 60)
        
        # Group by service
        by_service: dict[str, list[Violation]] = {}
        for v in violations:
            service = v.pattern.split(":")[0]
            by_service.setdefault(service, []).append(v)
        
        for service, service_violations in sorted(by_service.items()):
            logger.info(f"\n🚫 {service.upper()} references ({len(service_violations)}):")
            for v in service_violations[:10]:  # Limit output
                rel_path = v.file.relative_to(PROJECT_ROOT)
                logger.info(f"   {rel_path}:{v.line_num}")
                logger.info(f"      → {v.line_content}")
            if len(service_violations) > 10:
                logger.info(f"   ... and {len(service_violations) - 10} more")
        
        logger.info("\n" + "-" * 60)
        logger.info("💡 To fix: Remove all references to deprecated services.")
        logger.info("   These services have been replaced in L9 architecture.")
        logger.info("-" * 60 + "\n")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "caching", "ci", "cli", "event-driven", "filesystem", "logging", "migration", "operations", "testing"],
    "keywords": ["check", "deprecated", "scan", "services", "should", "violation"],
    "business_value": "Implements Violation for check no deprecated services functionality",
    "last_modified": "2026-01-14T15:03:00Z",
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
