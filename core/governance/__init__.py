"""
L9 Governance Layer

Approval gates, permission management, and execution guards.
Python governance modules provide EXECUTABLE enforcement.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .approval_manager import (
    ApprovalDecision,
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)
from .mistake_prevention import MistakePrevention, create_mistake_prevention
from .quick_fixes import QuickFixEngine, create_quick_fix_engine

# Session startup moved to .cursor-commands/startup/
# Import with fallback for backward compatibility
try:
    from ..cursor_commands.startup.session_startup import (
        SessionStartup,
        create_session_startup,
    )
except ImportError:
    # Fallback: try absolute import
    try:
        import sys
        from pathlib import Path

        startup_path = (
            Path(__file__).parent.parent.parent / ".cursor-commands" / "startup"
        )
        if startup_path.exists():
            sys.path.insert(0, str(startup_path.parent))
            from startup.session_startup import SessionStartup, create_session_startup
        else:
            raise ImportError("startup module not found")
    except ImportError:
        # Final fallback: try old location
        from .session_startup import SessionStartup, create_session_startup

from .cmts import (
    CMTSService,
    MutationQuery,
    MutationRecord,
    MutationStatus,
    get_cmts_service,
)
from .credentials_policy import CredentialsPolicy, create_credentials_policy
from .policy_generator import PolicyGenerator, PolicySpec, ScopeAccessSpec
from .rate_limit_policy import (
    RateLimitConfig,
    RateLimitDep,
    RateLimitExceeded,
    RateLimitPolicy,
    RateLimitResult,
    check_rate_limit,
    get_rate_limit_policy,
    rate_limit,
    rate_limit_context,
)
from .subsystem_detector import (
    detect_subsystem,
    get_subsystem_context,
    get_subsystem_policy,
    requires_human_approval,
)

__all__ = [
    "ApprovalDecision",
    # Approval management
    "ApprovalManager",
    "ApprovalRequest",
    "ApprovalStatus",
    # Code Mutation Tracking System
    "CMTSService",
    "CredentialsPolicy",
    # Python governance modules (executable enforcement)
    "MistakePrevention",
    "MutationQuery",
    "MutationRecord",
    "MutationStatus",
    # Policy Generator
    "PolicyGenerator",
    "PolicySpec",
    "QuickFixEngine",
    "RateLimitConfig",
    "RateLimitDep",
    "RateLimitExceeded",
    # Unified Rate Limit Policy
    "RateLimitPolicy",
    "RateLimitResult",
    "ScopeAccessSpec",
    "SessionStartup",
    "check_rate_limit",
    "create_credentials_policy",
    "create_mistake_prevention",
    "create_quick_fix_engine",
    "create_session_startup",
    # Subsystem Detection
    "detect_subsystem",
    "get_cmts_service",
    "get_rate_limit_policy",
    "get_subsystem_context",
    "get_subsystem_policy",
    "rate_limit",
    "rate_limit_context",
    "requires_human_approval",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-172",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "authorization",
        "event-driven",
        "filesystem",
        "foundation",
        "governance",
        "utility",
    ],
    "keywords": ["governance"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:47Z",
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
