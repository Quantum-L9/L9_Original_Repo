"""
L9 Governance Layer

Approval gates, permission management, and execution guards.
Python governance modules provide EXECUTABLE enforcement.
"""
from __future__ import annotations

from .approval_manager import ApprovalManager, ApprovalStatus, ApprovalRequest, ApprovalDecision
from .mistake_prevention import MistakePrevention, create_mistake_prevention
from .quick_fixes import QuickFixEngine, create_quick_fix_engine
# Session startup moved to .cursor-commands/startup/
# Import with fallback for backward compatibility
try:
    from ..cursor_commands.startup.session_startup import SessionStartup, create_session_startup
except ImportError:
    # Fallback: try absolute import
    try:
        import sys
        from pathlib import Path
        startup_path = Path(__file__).parent.parent.parent / ".cursor-commands" / "startup"
        if startup_path.exists():
            sys.path.insert(0, str(startup_path.parent))
            from startup.session_startup import SessionStartup, create_session_startup
        else:
            raise ImportError("startup module not found")
    except ImportError:
        # Final fallback: try old location
        from .session_startup import SessionStartup, create_session_startup
from .credentials_policy import CredentialsPolicy, create_credentials_policy

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
]
