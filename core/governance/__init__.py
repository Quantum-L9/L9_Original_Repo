"""
L9 Governance Layer

Approval gates, permission management, and execution guards.
Python governance modules provide EXECUTABLE enforcement.
"""

from __future__ import annotations

from .approval_manager import (ApprovalDecision, ApprovalManager,
                               ApprovalRequest, ApprovalStatus)
from .mistake_prevention import MistakePrevention, create_mistake_prevention
from .quick_fixes import QuickFixEngine, create_quick_fix_engine

# Session startup moved to .cursor-commands/startup/
# Import with fallback for backward compatibility
try:
    from ..cursor_commands.startup.session_startup import (
        SessionStartup, create_session_startup)
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
            from startup.session_startup import (SessionStartup,
                                                 create_session_startup)
        else:
            raise ImportError("startup module not found")
    except ImportError:
        # Final fallback: try old location
        from .session_startup import SessionStartup, create_session_startup

from .cmts import (CMTSService, MutationQuery, MutationRecord, MutationStatus,
                   get_cmts_service)
from .credentials_policy import CredentialsPolicy, create_credentials_policy
from .policy_generator import PolicyGenerator, PolicySpec, ScopeAccessSpec
from .rate_limit_policy import (RateLimitConfig, RateLimitDep,
                                RateLimitExceeded, RateLimitPolicy,
                                RateLimitResult, check_rate_limit,
                                get_rate_limit_policy, rate_limit,
                                rate_limit_context)
from .subsystem_detector import (detect_subsystem, get_subsystem_context,
                                 get_subsystem_policy, requires_human_approval)

__all__ = [
    # Approval management
    "ApprovalManager",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalDecision",
    # Python governance modules (executable enforcement)
    "MistakePrevention",
    "create_mistake_prevention",
    "QuickFixEngine",
    "create_quick_fix_engine",
    "SessionStartup",
    "create_session_startup",
    "CredentialsPolicy",
    "create_credentials_policy",
    # Code Mutation Tracking System
    "CMTSService",
    "MutationRecord",
    "MutationStatus",
    "MutationQuery",
    "get_cmts_service",
    # Subsystem Detection
    "detect_subsystem",
    "get_subsystem_policy",
    "get_subsystem_context",
    "requires_human_approval",
    # Policy Generator
    "PolicyGenerator",
    "PolicySpec",
    "ScopeAccessSpec",
    # Unified Rate Limit Policy
    "RateLimitPolicy",
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimitDep",
    "rate_limit",
    "rate_limit_context",
    "check_rate_limit",
    "get_rate_limit_policy",
    "RateLimitExceeded",
]
