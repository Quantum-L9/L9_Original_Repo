"""
L9 Core Governance - Credentials Policy Enforcer
=================================================

Executable security enforcement for credentials and secrets.
Converts patterns from learning/credentials-policy.md into
programmatic detection, validation, and blocking.

Key capabilities:
- Detects exposed secrets (API keys, passwords, tokens)
- Validates credential rotation dates
- Blocks deployments with exposed keys
- Enforces least-privilege patterns

Version: 1.0.0
"""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = structlog.get_logger(__name__)


class SecretType(Enum):
    """Types of secrets to detect."""
    
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"
    WEBHOOK_URL = "webhook_url"


@dataclass
class SecretPattern:
    """
    A secret detection pattern.
    
    Attributes:
        id: Pattern identifier
        name: Human-readable name
        pattern: Regex to detect secret
        secret_type: Type of secret
        severity: How critical this exposure is
        redact_pattern: Regex to use for redaction
    """
    
    id: str
    name: str
    pattern: str
    secret_type: SecretType
    severity: str  # "critical", "high", "medium"
    redact_pattern: str = r"\*\*\*REDACTED\*\*\*"


@dataclass
class SecretViolation:
    """A detected secret exposure."""
    
    pattern_id: str
    name: str
    secret_type: str
    severity: str
    match_preview: str  # First/last chars only for safety
    line_number: Optional[int] = None
    blocked: bool = True


class CredentialsPolicy:
    """
    Executable credentials policy enforcer.
    
    Detects and blocks exposed secrets, enforces rotation policies,
    and validates credential handling patterns.
    
    Usage:
        policy = CredentialsPolicy()
        safe, violations = policy.scan(content)
        if not safe:
            # Handle exposed secrets
            pass
    """
    
    def __init__(self) -> None:
        """Initialize with default secret patterns."""
        self._patterns: list[SecretPattern] = self._load_default_patterns()
    
    def _load_default_patterns(self) -> list[SecretPattern]:
        """Load default secret detection patterns."""
        return [
            SecretPattern(
                id="SEC-001",
                name="OpenAI API Key",
                pattern=r"sk-[a-zA-Z0-9]{20,}",
                secret_type=SecretType.API_KEY,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-002",
                name="Anthropic API Key",
                pattern=r"sk-ant-[a-zA-Z0-9\-]{20,}",
                secret_type=SecretType.API_KEY,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-003",
                name="Slack Bot Token",
                pattern=r"xoxb-[a-zA-Z0-9\-]{20,}",
                secret_type=SecretType.TOKEN,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-004",
                name="Slack App Token",
                pattern=r"xapp-[a-zA-Z0-9\-]{20,}",
                secret_type=SecretType.TOKEN,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-005",
                name="GitHub Token",
                pattern=r"ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{20,}",
                secret_type=SecretType.TOKEN,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-006",
                name="PostgreSQL Connection String",
                pattern=r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/\w+",
                secret_type=SecretType.CONNECTION_STRING,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-007",
                name="Generic Password in Code",
                pattern=r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']',
                secret_type=SecretType.PASSWORD,
                severity="high",
            ),
            SecretPattern(
                id="SEC-008",
                name="AWS Access Key",
                pattern=r"AKIA[0-9A-Z]{16}",
                secret_type=SecretType.API_KEY,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-009",
                name="AWS Secret Key",
                pattern=r"[a-zA-Z0-9/+]{40}(?=\s|$|['\"])",
                secret_type=SecretType.API_KEY,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-010",
                name="Private RSA Key",
                pattern=r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
                secret_type=SecretType.PRIVATE_KEY,
                severity="critical",
            ),
            SecretPattern(
                id="SEC-011",
                name="Webhook URL with Token",
                pattern=r"https://hooks\.[a-z]+\.com/[a-zA-Z0-9/]+",
                secret_type=SecretType.WEBHOOK_URL,
                severity="high",
            ),
            SecretPattern(
                id="SEC-012",
                name="Supabase Key",
                pattern=r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}",
                secret_type=SecretType.API_KEY,
                severity="critical",
            ),
        ]
    
    @property
    def patterns(self) -> list[SecretPattern]:
        """Get all loaded patterns."""
        return self._patterns
    
    def add_pattern(self, pattern: SecretPattern) -> None:
        """Add a custom secret pattern."""
        self._patterns.append(pattern)
        logger.info("credentials_policy.pattern_added", pattern_id=pattern.id)
    
    def scan(self, content: str) -> tuple[bool, list[SecretViolation]]:
        """
        Scan content for exposed secrets.
        
        Args:
            content: Text content to scan
            
        Returns:
            Tuple of (is_safe, list of violations)
        """
        violations: list[SecretViolation] = []
        lines = content.split("\n")
        
        for pattern in self._patterns:
            for line_num, line in enumerate(lines, 1):
                matches = re.findall(pattern.pattern, line, re.IGNORECASE)
                for match in matches:
                    # Create safe preview (first 4 + last 4 chars)
                    if len(match) > 12:
                        preview = f"{match[:4]}...{match[-4:]}"
                    else:
                        preview = f"{match[:2]}***"
                    
                    violation = SecretViolation(
                        pattern_id=pattern.id,
                        name=pattern.name,
                        secret_type=pattern.secret_type.value,
                        severity=pattern.severity,
                        match_preview=preview,
                        line_number=line_num,
                        blocked=pattern.severity == "critical",
                    )
                    violations.append(violation)
                    
                    logger.warning(
                        "credentials_policy.secret_detected",
                        pattern_id=pattern.id,
                        name=pattern.name,
                        line=line_num,
                        severity=pattern.severity,
                    )
        
        is_safe = not any(v.blocked for v in violations)
        return is_safe, violations
    
    def redact(self, content: str) -> str:
        """
        Redact all detected secrets from content.
        
        Args:
            content: Text content to redact
            
        Returns:
            Content with secrets replaced by ***REDACTED***
        """
        redacted = content
        
        for pattern in self._patterns:
            redacted = re.sub(
                pattern.pattern,
                "***REDACTED***",
                redacted,
                flags=re.IGNORECASE,
            )
        
        return redacted
    
    def validate_env_file(self, env_content: str) -> list[dict[str, Any]]:
        """
        Validate .env file format and content.
        
        Args:
            env_content: Content of .env file
            
        Returns:
            List of validation issues
        """
        issues: list[dict[str, Any]] = []
        lines = env_content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Check format
            if "=" not in line:
                issues.append({
                    "line": line_num,
                    "issue": "Invalid format (missing =)",
                    "content": line[:30],
                })
                continue
            
            key, value = line.split("=", 1)
            
            # Check for placeholder values
            placeholder_patterns = [
                r"your[-_]?key[-_]?here",
                r"xxx+",
                r"placeholder",
                r"changeme",
                r"TODO",
            ]
            for pp in placeholder_patterns:
                if re.search(pp, value, re.IGNORECASE):
                    issues.append({
                        "line": line_num,
                        "issue": f"Placeholder value detected for {key}",
                        "content": value[:20],
                    })
        
        return issues
    
    def get_audit_report(self, content: str) -> dict[str, Any]:
        """
        Generate security audit report for content.
        
        Args:
            content: Content to audit
            
        Returns:
            Audit report dict
        """
        is_safe, violations = self.scan(content)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "is_safe": is_safe,
            "total_violations": len(violations),
            "critical_violations": sum(1 for v in violations if v.severity == "critical"),
            "high_violations": sum(1 for v in violations if v.severity == "high"),
            "violations_by_type": {
                secret_type.value: sum(1 for v in violations if v.secret_type == secret_type.value)
                for secret_type in SecretType
            },
            "blocked": not is_safe,
            "recommendations": self._generate_recommendations(violations),
        }
    
    def _generate_recommendations(self, violations: list[SecretViolation]) -> list[str]:
        """Generate recommendations based on violations."""
        recommendations: list[str] = []
        
        if any(v.secret_type == "api_key" for v in violations):
            recommendations.append("Move API keys to environment variables")
            recommendations.append("Use secret management service (Vault, AWS Secrets Manager)")
        
        if any(v.secret_type == "password" for v in violations):
            recommendations.append("Never hardcode passwords in source code")
            recommendations.append("Use credential injection at runtime")
        
        if any(v.secret_type == "connection_string" for v in violations):
            recommendations.append("Use DATABASE_URL environment variable")
            recommendations.append("Separate credentials from connection parameters")
        
        return recommendations


# Factory function
def create_credentials_policy() -> CredentialsPolicy:
    """Create a CredentialsPolicy instance with default patterns."""
    return CredentialsPolicy()


__all__ = [
    "CredentialsPolicy",
    "SecretPattern",
    "SecretViolation",
    "SecretType",
    "create_credentials_policy",
    "CredentialRotationPolicy",
    "CredentialRecord",
    "RotationStatus",
    "create_rotation_policy",
]


# =============================================================================
# CREDENTIAL ROTATION POLICY (v1.1.0)
# =============================================================================



class RotationStatus(Enum):
    """Status of credential rotation."""
    
    CURRENT = "current"           # Within rotation period
    WARNING = "warning"           # Approaching expiration
    EXPIRED = "expired"           # Past rotation deadline
    ROTATED = "rotated"           # Successfully rotated
    UNKNOWN = "unknown"           # No rotation date recorded


@dataclass
class CredentialRecord:
    """
    Record of a credential's rotation status.
    
    Attributes:
        credential_id: Unique identifier for the credential
        credential_type: Type of credential (api_key, password, token, etc.)
        name: Human-readable name
        created_at: When the credential was created
        last_rotated: When the credential was last rotated
        rotation_period_days: How often credential should be rotated
        owner: Who owns/manages this credential
        notes: Additional notes
    """
    
    credential_id: str
    credential_type: str
    name: str
    created_at: datetime
    last_rotated: Optional[datetime] = None
    rotation_period_days: int = 90  # Default: rotate every 90 days
    owner: str = "system"
    notes: str = ""
    
    @property
    def days_since_rotation(self) -> int:
        """Days since last rotation (or creation if never rotated)."""
        reference_date = self.last_rotated or self.created_at
        return (datetime.utcnow() - reference_date).days
    
    @property
    def days_until_due(self) -> int:
        """Days until rotation is due. Negative if overdue."""
        return self.rotation_period_days - self.days_since_rotation
    
    @property
    def status(self) -> RotationStatus:
        """Current rotation status."""
        days_until = self.days_until_due
        
        if days_until > 14:  # More than 2 weeks
            return RotationStatus.CURRENT
        elif days_until > 0:  # Within 2 weeks
            return RotationStatus.WARNING
        else:  # Overdue
            return RotationStatus.EXPIRED
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "credential_id": self.credential_id,
            "credential_type": self.credential_type,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "rotation_period_days": self.rotation_period_days,
            "days_since_rotation": self.days_since_rotation,
            "days_until_due": self.days_until_due,
            "status": self.status.value,
            "owner": self.owner,
            "notes": self.notes,
        }


class CredentialRotationPolicy:
    """
    Credential rotation policy enforcer.
    
    Tracks credential ages, enforces rotation schedules, and provides
    audit reports on credential health.
    
    Usage:
        policy = CredentialRotationPolicy()
        policy.register_credential("api_key_openai", "api_key", "OpenAI API Key")
        policy.record_rotation("api_key_openai")
        report = policy.get_rotation_report()
    """
    
    # Default rotation periods by credential type (in days)
    DEFAULT_ROTATION_PERIODS: dict[str, int] = {
        "api_key": 90,        # API keys: 90 days
        "password": 90,       # Passwords: 90 days
        "token": 30,          # Tokens: 30 days (often shorter-lived)
        "private_key": 365,   # Private keys: 1 year
        "connection_string": 90,  # Connection strings: 90 days
        "webhook_url": 180,   # Webhook URLs: 6 months
    }
    
    # Warning threshold (days before expiration to warn)
    WARNING_THRESHOLD_DAYS: int = 14
    
    def __init__(self) -> None:
        """Initialize credential rotation policy."""
        self._credentials: dict[str, CredentialRecord] = {}
        self._rotation_history: list[dict[str, Any]] = []
        logger.info("CredentialRotationPolicy initialized")
    
    def register_credential(
        self,
        credential_id: str,
        credential_type: str,
        name: str,
        created_at: Optional[datetime] = None,
        rotation_period_days: Optional[int] = None,
        owner: str = "system",
        notes: str = "",
    ) -> CredentialRecord:
        """
        Register a credential for rotation tracking.
        
        Args:
            credential_id: Unique identifier
            credential_type: Type (api_key, password, token, etc.)
            name: Human-readable name
            created_at: When created (defaults to now)
            rotation_period_days: Custom rotation period
            owner: Who owns this credential
            notes: Additional notes
            
        Returns:
            The created CredentialRecord
        """
        if rotation_period_days is None:
            rotation_period_days = self.DEFAULT_ROTATION_PERIODS.get(credential_type, 90)
        
        record = CredentialRecord(
            credential_id=credential_id,
            credential_type=credential_type,
            name=name,
            created_at=created_at or datetime.utcnow(),
            rotation_period_days=rotation_period_days,
            owner=owner,
            notes=notes,
        )
        
        self._credentials[credential_id] = record
        
        logger.info(
            "credential_rotation.registered",
            credential_id=credential_id,
            credential_type=credential_type,
            rotation_period_days=rotation_period_days,
        )
        
        return record
    
    def record_rotation(
        self,
        credential_id: str,
        rotated_at: Optional[datetime] = None,
        rotated_by: str = "system",
        notes: str = "",
    ) -> bool:
        """
        Record that a credential was rotated.
        
        Args:
            credential_id: ID of the rotated credential
            rotated_at: When rotation occurred (defaults to now)
            rotated_by: Who performed the rotation
            notes: Additional notes
            
        Returns:
            True if recorded successfully
        """
        if credential_id not in self._credentials:
            logger.warning(
                "credential_rotation.unknown_credential",
                credential_id=credential_id,
            )
            return False
        
        rotation_time = rotated_at or datetime.utcnow()
        record = self._credentials[credential_id]
        old_rotated = record.last_rotated
        record.last_rotated = rotation_time
        
        # Record in history
        self._rotation_history.append({
            "credential_id": credential_id,
            "credential_type": record.credential_type,
            "rotated_at": rotation_time.isoformat(),
            "rotated_by": rotated_by,
            "previous_rotation": old_rotated.isoformat() if old_rotated else None,
            "notes": notes,
        })
        
        logger.info(
            "credential_rotation.rotated",
            credential_id=credential_id,
            rotated_by=rotated_by,
        )
        
        return True
    
    def get_credential(self, credential_id: str) -> Optional[CredentialRecord]:
        """Get a credential record by ID."""
        return self._credentials.get(credential_id)
    
    def get_all_credentials(self) -> list[CredentialRecord]:
        """Get all registered credentials."""
        return list(self._credentials.values())
    
    def get_credentials_by_status(self, status: RotationStatus) -> list[CredentialRecord]:
        """Get credentials with a specific status."""
        return [c for c in self._credentials.values() if c.status == status]
    
    def get_expired_credentials(self) -> list[CredentialRecord]:
        """Get all expired credentials (need immediate rotation)."""
        return self.get_credentials_by_status(RotationStatus.EXPIRED)
    
    def get_warning_credentials(self) -> list[CredentialRecord]:
        """Get credentials approaching expiration."""
        return self.get_credentials_by_status(RotationStatus.WARNING)
    
    def check_compliance(self) -> tuple[bool, list[CredentialRecord]]:
        """
        Check if all credentials are compliant with rotation policy.
        
        Returns:
            Tuple of (is_compliant, list of non-compliant credentials)
        """
        non_compliant = [
            c for c in self._credentials.values()
            if c.status in (RotationStatus.EXPIRED, RotationStatus.WARNING)
        ]
        
        is_compliant = len(self.get_expired_credentials()) == 0
        
        return is_compliant, non_compliant
    
    def get_rotation_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive rotation report.
        
        Returns:
            Report dictionary with status breakdown and recommendations
        """
        credentials = list(self._credentials.values())
        
        by_status = {
            RotationStatus.CURRENT.value: [],
            RotationStatus.WARNING.value: [],
            RotationStatus.EXPIRED.value: [],
        }
        
        for cred in credentials:
            by_status[cred.status.value].append(cred.to_dict())
        
        is_compliant, non_compliant = self.check_compliance()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_credentials": len(credentials),
            "is_compliant": is_compliant,
            "status_breakdown": {
                "current": len(by_status[RotationStatus.CURRENT.value]),
                "warning": len(by_status[RotationStatus.WARNING.value]),
                "expired": len(by_status[RotationStatus.EXPIRED.value]),
            },
            "credentials_by_status": by_status,
            "recommendations": self._generate_recommendations(non_compliant),
            "rotation_history_count": len(self._rotation_history),
        }
    
    def _generate_recommendations(
        self,
        non_compliant: list[CredentialRecord],
    ) -> list[str]:
        """Generate recommendations based on non-compliant credentials."""
        recommendations: list[str] = []
        
        expired = [c for c in non_compliant if c.status == RotationStatus.EXPIRED]
        warning = [c for c in non_compliant if c.status == RotationStatus.WARNING]
        
        if expired:
            recommendations.append(
                f"URGENT: {len(expired)} credential(s) require immediate rotation"
            )
            for cred in expired[:3]:  # Show up to 3
                recommendations.append(
                    f"  - Rotate {cred.name} ({cred.days_since_rotation} days old)"
                )
        
        if warning:
            recommendations.append(
                f"WARNING: {len(warning)} credential(s) approaching rotation deadline"
            )
            for cred in warning[:3]:  # Show up to 3
                recommendations.append(
                    f"  - {cred.name} due in {cred.days_until_due} days"
                )
        
        if not recommendations:
            recommendations.append("All credentials are current. No action needed.")
        
        return recommendations
    
    def get_rotation_history(
        self,
        credential_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get rotation history.
        
        Args:
            credential_id: Filter by credential (optional)
            limit: Maximum entries to return
            
        Returns:
            List of rotation history entries
        """
        history = self._rotation_history
        
        if credential_id:
            history = [h for h in history if h["credential_id"] == credential_id]
        
        return history[-limit:]
    
    def export_state(self) -> dict[str, Any]:
        """Export current state for persistence."""
        return {
            "credentials": {
                cid: cred.to_dict()
                for cid, cred in self._credentials.items()
            },
            "rotation_history": self._rotation_history,
            "exported_at": datetime.utcnow().isoformat(),
        }
    
    def import_state(self, state: dict[str, Any]) -> int:
        """
        Import state from persistence.
        
        Args:
            state: Previously exported state
            
        Returns:
            Number of credentials imported
        """
        credentials_data = state.get("credentials", {})
        imported = 0
        
        for cid, cdata in credentials_data.items():
            try:
                record = CredentialRecord(
                    credential_id=cdata["credential_id"],
                    credential_type=cdata["credential_type"],
                    name=cdata["name"],
                    created_at=datetime.fromisoformat(cdata["created_at"]),
                    last_rotated=(
                        datetime.fromisoformat(cdata["last_rotated"])
                        if cdata.get("last_rotated")
                        else None
                    ),
                    rotation_period_days=cdata.get("rotation_period_days", 90),
                    owner=cdata.get("owner", "system"),
                    notes=cdata.get("notes", ""),
                )
                self._credentials[cid] = record
                imported += 1
            except Exception as e:
                logger.warning(
                    "credential_rotation.import_error",
                    credential_id=cid,
                    error=str(e),
                )
        
        self._rotation_history = state.get("rotation_history", [])
        
        logger.info(
            "credential_rotation.state_imported",
            credentials_imported=imported,
            history_entries=len(self._rotation_history),
        )
        
        return imported


def create_rotation_policy() -> CredentialRotationPolicy:
    """Create a CredentialRotationPolicy instance."""
    return CredentialRotationPolicy()

