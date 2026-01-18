"""
L9 Core Governance - Quick Fix Engine
======================================

Executable auto-remediation engine for common problems.
Converts patterns from learning/patterns/quick-fixes.md into
programmatic detection and automatic fixes.

Key capabilities:
- Detects known problem patterns via regex
- Auto-applies fixes where safe (auto_apply=True)
- Returns fix suggestions where manual review needed
- Tracks fix application history

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Quick Fix Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "quick_fixes",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
import structlog
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = structlog.get_logger(__name__)


@dataclass
class QuickFix:
    """
    A quick fix pattern.
    
    Attributes:
        id: Unique fix identifier (e.g., "QF-001")
        problem: Description of the problem
        pattern: Regex pattern to detect problem
        solution: How to fix it
        fix_fn: Optional callable that returns fixed content
        auto_apply: Whether to apply automatically
        times_applied: Count of applications
    """
    
    id: str
    problem: str
    pattern: str
    solution: str
    fix_fn: Optional[Callable[[str, re.Match], str]] = None
    auto_apply: bool = False
    times_applied: int = 0


@dataclass
class FixResult:
    """Result of applying a fix."""
    
    fix_id: str
    problem: str
    solution: str
    applied: bool
    original_match: str
    fixed_content: Optional[str] = None


class QuickFixEngine:
    """
    Executable quick-fix engine with auto-remediation.
    
    Detects known problems and applies fixes programmatically
    where safe, or returns suggestions where manual review needed.
    
    Usage:
        engine = QuickFixEngine()
        fixed_content, results = engine.auto_fix(content)
    """
    
    def __init__(self) -> None:
        """Initialize with default L9 quick fixes."""
        self._fixes: list[QuickFix] = self._load_default_fixes()
    
    def _load_default_fixes(self) -> list[QuickFix]:
        """Load default quick fixes from quick-fixes.md patterns."""
        return [
            QuickFix(
                id="QF-001",
                problem="JSON wrapped in string (double-encoded)",
                pattern=r'"(\{[^"]*\})"',
                solution="Use json.loads(json.loads(content)) for double-encoded JSON",
                fix_fn=None,  # Requires context-specific handling
                auto_apply=False,
            ),
            QuickFix(
                id="QF-002",
                problem="Jinja/template expression has leading spaces",
                pattern=r"\{\{\s+(\w+)",
                solution="Remove spaces: {{ var → {{var",
                fix_fn=lambda content, m: content.replace(m.group(0), "{{" + m.group(1)),
                auto_apply=True,
            ),
            QuickFix(
                id="QF-003",
                problem="Jinja/template expression has trailing spaces",
                pattern=r"(\w+(?:\.\w+)*)\s+\}\}",
                solution="Remove trailing spaces before }}",
                fix_fn=lambda content, m: content.replace(m.group(0), m.group(1) + "}}"),
                auto_apply=True,
            ),
            QuickFix(
                id="QF-004",
                problem="Supabase manual auth headers instead of credentials",
                pattern=r'"Authorization":\s*"Bearer.*apikey"',
                solution="Use predefinedCredentialType: supabaseApi in node config",
                fix_fn=None,  # Requires structural change
                auto_apply=False,
            ),
            QuickFix(
                id="QF-005",
                problem="Localhost URL in production code",
                pattern=r"(https?://(?:localhost|127\.0\.0\.1):\d+)",
                solution="Replace with production URL: https://l9.igorbeylin.com or environment variable",
                fix_fn=None,  # Requires user-specific URL
                auto_apply=False,
            ),
            QuickFix(
                id="QF-006",
                problem="Missing await on async call",
                pattern=r"(?<!await\s)(\w+_service\.\w+\([^)]*\))(?!\s*\))",
                solution="Add await before async service calls",
                fix_fn=None,  # Requires AST analysis for safety
                auto_apply=False,
            ),
            QuickFix(
                id="QF-007",
                problem="Bare except clause",
                pattern=r"except\s*:",
                solution="Use specific exception: except ValueError as e:",
                fix_fn=lambda content, m: content.replace("except:", "except Exception as e:"),
                auto_apply=True,
            ),
            QuickFix(
                id="QF-008",
                problem="Print statement instead of logging",
                pattern=r"^\s*print\s*\([^)]+\)",
                solution="Use structlog: logger.info() instead of print()",
                fix_fn=None,  # Requires understanding of log level
                auto_apply=False,
            ),
            QuickFix(
                id="QF-009",
                problem="Hardcoded /Users/ib-mac path",
                pattern=r"/Users/ib-mac/(?!Projects/L9)",
                solution="Use Path.home() or $HOME for portability",
                fix_fn=None,  # Requires context analysis
                auto_apply=False,
            ),
            QuickFix(
                id="QF-010",
                problem="Using requests instead of httpx",
                pattern=r"import requests|from requests import",
                solution="Use httpx for async HTTP: import httpx",
                fix_fn=lambda content, m: content.replace("import requests", "import httpx"),
                auto_apply=False,  # Requires API compatibility check
            ),
        ]
    
    @property
    def fixes(self) -> list[QuickFix]:
        """Get all loaded fixes."""
        return self._fixes
    
    def add_fix(self, fix: QuickFix) -> None:
        """Add a custom quick fix."""
        self._fixes.append(fix)
        logger.info("quick_fix.added", fix_id=fix.id, problem=fix.problem)
    
    def diagnose(self, content: str) -> list[QuickFix]:
        """
        Find applicable quick fixes for content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            List of applicable QuickFix objects
        """
        applicable: list[QuickFix] = []
        
        for fix in self._fixes:
            if re.search(fix.pattern, content, re.MULTILINE):
                applicable.append(fix)
        
        return applicable
    
    def auto_fix(self, content: str) -> tuple[str, list[FixResult]]:
        """
        Apply all auto-applicable fixes to content.
        
        Only fixes with auto_apply=True and fix_fn defined are applied.
        
        Args:
            content: Text content to fix
            
        Returns:
            Tuple of (fixed_content, list of FixResult)
        """
        results: list[FixResult] = []
        fixed_content = content
        
        for fix in self._fixes:
            matches = list(re.finditer(fix.pattern, fixed_content, re.MULTILINE))
            
            for match in matches:
                if fix.auto_apply and fix.fix_fn:
                    try:
                        new_content = fix.fix_fn(fixed_content, match)
                        if new_content != fixed_content:
                            fix.times_applied += 1
                            results.append(FixResult(
                                fix_id=fix.id,
                                problem=fix.problem,
                                solution=fix.solution,
                                applied=True,
                                original_match=match.group(0),
                                fixed_content=new_content[:100],  # Preview
                            ))
                            fixed_content = new_content
                            logger.info(
                                "quick_fix.applied",
                                fix_id=fix.id,
                                match=match.group(0)[:50],
                            )
                    except Exception as e:
                        logger.warning(
                            "quick_fix.failed",
                            fix_id=fix.id,
                            error=str(e),
                        )
                        results.append(FixResult(
                            fix_id=fix.id,
                            problem=fix.problem,
                            solution=fix.solution,
                            applied=False,
                            original_match=match.group(0),
                        ))
                else:
                    # Suggest but don't apply
                    results.append(FixResult(
                        fix_id=fix.id,
                        problem=fix.problem,
                        solution=fix.solution,
                        applied=False,
                        original_match=match.group(0),
                    ))
        
        return fixed_content, results
    
    def get_suggestions(self, content: str) -> list[dict[str, Any]]:
        """
        Get fix suggestions without applying them.
        
        Args:
            content: Text content to analyze
            
        Returns:
            List of suggestion dicts with id, problem, solution, matches
        """
        suggestions: list[dict[str, Any]] = []
        
        for fix in self.diagnose(content):
            matches = re.findall(fix.pattern, content, re.MULTILINE)
            suggestions.append({
                "id": fix.id,
                "problem": fix.problem,
                "solution": fix.solution,
                "auto_apply": fix.auto_apply,
                "matches": matches[:5],  # Limit matches shown
            })
        
        return suggestions
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about fix applications."""
        return {
            "total_fixes": len(self._fixes),
            "auto_apply_count": sum(1 for f in self._fixes if f.auto_apply),
            "total_applications": sum(f.times_applied for f in self._fixes),
            "top_fixes": sorted(
                [(f.id, f.problem, f.times_applied) for f in self._fixes if f.times_applied > 0],
                key=lambda x: x[2],
                reverse=True,
            )[:5],
        }


# Factory function
def create_quick_fix_engine() -> QuickFixEngine:
    """Create a QuickFixEngine instance with default fixes."""
    return QuickFixEngine()


__all__ = [
    "QuickFixEngine",
    "QuickFix",
    "FixResult",
    "create_quick_fix_engine",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-084",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "dataclass", "engine", "foundation", "governance", "http-client", "logging"],
    "keywords": ["auto", "create", "detection", "diagnose", "engine", "fix", "fixes", "governance"],
    "business_value": "Provides quick fixes components including QuickFix, FixResult, QuickFixEngine",
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
