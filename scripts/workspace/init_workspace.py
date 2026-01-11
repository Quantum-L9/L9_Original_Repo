#!/usr/bin/env python3
"""
L9 Workspace Initialization Script
===================================

CLI runner that initializes an L9 workspace by executing all Python
governance modules defined in setup-new-workspace.yaml.

Usage:
    python scripts/init_workspace.py
    python scripts/init_workspace.py --workspace /path/to/workspace
    python scripts/init_workspace.py --verbose

Returns exit code 0 if READY, 1 if DEGRADED, 2 if BLOCKED.

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class InitResult:
    """Complete workspace initialization result."""
    
    status: str  # READY, DEGRADED, BLOCKED
    startup_status: str
    mistakes_loaded: int
    quickfixes_loaded: int
    credentials_patterns: int
    errors: list[str]
    warnings: list[str]
    duration_ms: int


def init_workspace(workspace_root: Path, verbose: bool = False) -> InitResult:
    """
    Initialize workspace by loading all governance modules.
    
    Args:
        workspace_root: Path to workspace root
        verbose: Print detailed output
        
    Returns:
        InitResult with complete status
    """
    start_time = datetime.utcnow()
    errors: list[str] = []
    warnings: list[str] = []
    
    if verbose:
        logger.info(f"\n🚀 Initializing L9 workspace: {workspace_root}\n")
    
    # ─────────────────────────────────────────────────────────────
    # 1. Session Startup (preflight + mandatory files)
    # ─────────────────────────────────────────────────────────────
    try:
        from core.governance import create_session_startup
        
        startup = create_session_startup(workspace_root)
        startup_result = startup.execute()
        
        if verbose:
            logger.info(f"📋 Session Startup: {startup_result.status}")
            logger.info(f"   Files loaded: {len(startup_result.files_loaded)}")
            if startup_result.errors:
                for e in startup_result.errors:
                    logger.info(f"   ❌ {e}")
            if startup_result.warnings:
                for w in startup_result.warnings:
                    logger.info(f"   ⚠️  {w}")
        
        errors.extend(startup_result.errors)
        warnings.extend(startup_result.warnings)
        startup_status = startup_result.status
        
    except Exception as e:
        errors.append(f"Session Startup FAILED: {e}")
        startup_status = "BLOCKED"
        if verbose:
            logger.info(f"❌ Session Startup FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 2. Mistake Prevention (load critical rules)
    # ─────────────────────────────────────────────────────────────
    mistakes_loaded = 0
    try:
        from core.governance import create_mistake_prevention
        
        mistake_engine = create_mistake_prevention()
        mistakes_loaded = len(mistake_engine.rules)
        
        if verbose:
            logger.info(f"\n🛡️  Mistake Prevention: {mistakes_loaded} rules loaded")
            for rule in mistake_engine.rules[:3]:
                logger.info(f"   • {rule.id}: {rule.name}")
            if mistakes_loaded > 3:
                logger.info(f"   ... and {mistakes_loaded - 3} more")
                
    except Exception as e:
        errors.append(f"Mistake Prevention FAILED: {e}")
        if verbose:
            logger.info(f"❌ Mistake Prevention FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 3. Quick Fixes (load remediation patterns)
    # ─────────────────────────────────────────────────────────────
    quickfixes_loaded = 0
    try:
        from core.governance import create_quick_fix_engine
        
        quickfix_engine = create_quick_fix_engine()
        quickfixes_loaded = len(quickfix_engine.fixes)
        
        if verbose:
            logger.info(f"\n🔧 Quick Fix Engine: {quickfixes_loaded} fixes loaded")
            for fix in quickfix_engine.fixes[:3]:
                logger.info(f"   • {fix.id}: {fix.problem[:40]}...")
            if quickfixes_loaded > 3:
                logger.info(f"   ... and {quickfixes_loaded - 3} more")
                
    except Exception as e:
        warnings.append(f"Quick Fix Engine FAILED: {e}")
        if verbose:
            logger.info(f"⚠️  Quick Fix Engine FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 4. Credentials Policy (load secret patterns)
    # ─────────────────────────────────────────────────────────────
    credentials_patterns = 0
    try:
        from core.governance import create_credentials_policy
        
        credentials_policy = create_credentials_policy()
        credentials_patterns = len(credentials_policy.patterns)
        
        if verbose:
            logger.info(f"\n🔐 Credentials Policy: {credentials_patterns} patterns loaded")
            for pattern in credentials_policy.patterns[:3]:
                logger.info(f"   • {pattern.secret_type.value}: {pattern.name}")
            if credentials_patterns > 3:
                logger.info(f"   ... and {credentials_patterns - 3} more")
                
    except Exception as e:
        warnings.append(f"Credentials Policy FAILED: {e}")
        if verbose:
            logger.info(f"⚠️  Credentials Policy FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 5. Determine final status
    # ─────────────────────────────────────────────────────────────
    critical_errors = [e for e in errors if "CRITICAL" in e or "BLOCKED" in e or "FAILED" in e]
    
    if critical_errors or startup_status == "BLOCKED":
        status = "BLOCKED"
    elif warnings or startup_status == "DEGRADED":
        status = "DEGRADED"
    else:
        status = "READY"
    
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    return InitResult(
        status=status,
        startup_status=startup_status,
        mistakes_loaded=mistakes_loaded,
        quickfixes_loaded=quickfixes_loaded,
        credentials_patterns=credentials_patterns,
        errors=errors,
        warnings=warnings,
        duration_ms=duration_ms,
    )


def print_banner(result: InitResult) -> None:
    """Print final status banner."""
    status_icon = {"READY": "✅", "DEGRADED": "⚠️", "BLOCKED": "❌"}.get(result.status, "❓")
    
    logger.info("\n" + "═" * 60)
    logger.info(f"  {status_icon} L9 WORKSPACE INITIALIZATION: {result.status}")
    logger.info("═" * 60)
    logger.info(f"""
  ┌────────────────────────────────────┬──────────┐
  │ Component                          │ Status   │
  ├────────────────────────────────────┼──────────┤
  │ Session Startup                    │ {result.startup_status:<8} │
  │ Mistake Prevention Rules           │ {result.mistakes_loaded:<8} │
  │ Quick Fix Patterns                 │ {result.quickfixes_loaded:<8} │
  │ Credentials Policy Patterns        │ {result.credentials_patterns:<8} │
  └────────────────────────────────────┴──────────┘
  
  Duration: {result.duration_ms}ms
""")
    
    if result.errors:
        logger.info("  ❌ Errors:")
        for e in result.errors:
            logger.info(f"     • {e}")
        logger.info()
    
    if result.warnings:
        logger.info("  ⚠️  Warnings:")
        for w in result.warnings:
            logger.info(f"     • {w}")
        logger.info()
    
    if result.status == "READY":
        logger.info("  🎯 READY FOR WORK - Python governance enforcement ACTIVE\n")
    elif result.status == "DEGRADED":
        logger.info("  ⚠️  DEGRADED - Some systems unavailable, proceed with caution\n")
    else:
        logger.info("  🛑 BLOCKED - Critical systems failed, resolve before proceeding\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize L9 workspace with Python governance modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/init_workspace.py
  python scripts/init_workspace.py --verbose
  python scripts/init_workspace.py --workspace /path/to/l9
  
Exit Codes:
  0 = READY (all systems operational)
  1 = DEGRADED (some warnings, proceed with caution)
  2 = BLOCKED (critical failures, resolve first)
        """,
    )
    parser.add_argument(
        "--workspace", "-w",
        type=Path,
        default=PROJECT_ROOT,
        help="Workspace root path (default: L9 project root)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only print final status line",
    )
    
    args = parser.parse_args()
    
    result = init_workspace(args.workspace, verbose=args.verbose)
    
    if args.quiet:
        logger.info(f"{result.status}")
    else:
        print_banner(result)
    
    # Return exit code based on status
    return {"READY": 0, "DEGRADED": 1, "BLOCKED": 2}.get(result.status, 2)


if __name__ == "__main__":
    sys.exit(main())

