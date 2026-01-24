"""
L9 Core Governance - Security Policy Service
=============================================

Runtime security policy enforcement integrated with L9 governance engine.

This service:
- Loads security policies from config/security_policy.yaml
- Enforces security policies at runtime
- Integrates with observability for metrics and alerting
- Provides security scanning results to governance decisions

Version: 1.0.0
"""

from __future__ import annotations
from core.patterns.singleton import singleton


# ============================================================================
__dora_meta__ = {
    "component_name": "Security Policy Service",
    "module_version": "1.0.0",
    "created_by": "Manus AI",
    "created_at": "2026-01-21T00:00:00Z",
    "updated_at": "2026-01-21T00:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "security_policy",
    "type": "service",
    "status": "active",
}
# ============================================================================

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityAction(Enum):
    """Security policy enforcement actions."""
    BLOCK = "block"
    WARN = "warn"
    INFO = "info"
    ALLOW = "allow"


class VulnerabilitySeverity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityViolation:
    """Represents a security policy violation."""
    violation_id: str
    violation_type: str  # sast, dependencies, secrets, containers
    severity: VulnerabilitySeverity
    message: str
    location: Optional[str] = None
    cve: Optional[str] = None
    package: Optional[str] = None
    action: SecurityAction = SecurityAction.BLOCK
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "cve": self.cve,
            "package": self.package,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SecurityScanResult:
    """Results from a security scan."""
    scan_type: str  # sast, dependencies, secrets, containers
    scan_timestamp: datetime
    violations: List[SecurityViolation]
    passed: bool
    summary: Dict[str, int]  # Count by severity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "scan_type": self.scan_type,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "violations": [v.to_dict() for v in self.violations],
            "passed": self.passed,
            "summary": self.summary,
        }


@singleton
class SecurityPolicyService:
    """
    Security policy enforcement service for L9 governance.
    
    Integrates with:
    - config/security_policy.yaml (policy definitions)
    - core/observability/ (metrics and alerting)
    - core/governance/engine.py (policy enforcement)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize security policy service.
        
        Args:
            config_path: Path to security_policy.yaml (default: config/security_policy.yaml)
        """
        self.config_path = config_path or self._get_default_config_path()
        self.policy = self._load_policy()
        self.environment = os.getenv("L9_ENVIRONMENT", "development")
        
        logger.info(
            f"SecurityPolicyService initialized",
            extra={
                "config_path": self.config_path,
                "environment": self.environment,
            }
        )
    
    def _get_default_config_path(self) -> str:
        """Get default path to security policy config."""
        # Try to find config relative to this file
        current_dir = Path(__file__).parent
        repo_root = current_dir.parent.parent
        config_path = repo_root / "config" / "security_policy.yaml"
        
        if config_path.exists():
            return str(config_path)
        
        # Fallback to environment variable
        return os.getenv("L9_SECURITY_POLICY_PATH", "config/security_policy.yaml")
    
    def _load_policy(self) -> Dict[str, Any]:
        """Load security policy from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                policy = yaml.safe_load(f)
            
            logger.info(f"Security policy loaded from {self.config_path}")
            return policy
        
        except FileNotFoundError:
            logger.warning(
                f"Security policy file not found: {self.config_path}. Using defaults."
            )
            return self._get_default_policy()
        
        except Exception as e:
            logger.error(f"Failed to load security policy: {e}")
            return self._get_default_policy()
    
    def _get_default_policy(self) -> Dict[str, Any]:
        """Get default security policy (fail-closed)."""
        return {
            "sast": {
                "enabled": True,
                "thresholds": {
                    "critical": {"max_allowed": 0, "action": "block"},
                    "high": {"max_allowed": 0, "action": "block"},
                    "medium": {"max_allowed": 10, "action": "warn"},
                    "low": {"max_allowed": 50, "action": "info"},
                }
            },
            "dependencies": {
                "enabled": True,
                "thresholds": {
                    "critical": {"max_allowed": 0, "action": "block"},
                    "high": {"max_allowed": 3, "action": "warn"},
                    "medium": {"max_allowed": 10, "action": "info"},
                    "low": {"max_allowed": 50, "action": "info"},
                }
            },
            "secrets": {
                "enabled": True,
                "thresholds": {
                    "any_secrets": {"max_allowed": 0, "action": "block"}
                }
            },
            "containers": {
                "enabled": True,
                "thresholds": {
                    "critical": {"max_allowed": 0, "action": "warn"},
                    "high": {"max_allowed": 10, "action": "warn"},
                    "medium": {"max_allowed": 50, "action": "info"},
                    "low": {"max_allowed": 100, "action": "info"},
                }
            }
        }
    
    def get_threshold(self, scan_type: str, severity: VulnerabilitySeverity) -> Dict[str, Any]:
        """
        Get threshold configuration for a scan type and severity.
        
        Args:
            scan_type: Type of scan (sast, dependencies, secrets, containers)
            severity: Vulnerability severity
        
        Returns:
            Threshold configuration with max_allowed and action
        """
        # Check environment-specific overrides
        env_policy = self.policy.get("environments", {}).get(self.environment, {})
        if scan_type in env_policy:
            thresholds = env_policy[scan_type].get("thresholds", {})
            if severity.value in thresholds:
                return thresholds[severity.value]
        
        # Fall back to default policy
        scan_policy = self.policy.get(scan_type, {})
        thresholds = scan_policy.get("thresholds", {})
        
        if severity.value in thresholds:
            return thresholds[severity.value]
        
        # Ultimate fallback: block on critical, warn on high
        if severity == VulnerabilitySeverity.CRITICAL:
            return {"max_allowed": 0, "action": "block"}
        elif severity == VulnerabilitySeverity.HIGH:
            return {"max_allowed": 5, "action": "warn"}
        else:
            return {"max_allowed": 50, "action": "info"}
    
    def evaluate_scan_result(self, scan_result: SecurityScanResult) -> bool:
        """
        Evaluate a security scan result against policy.
        
        Args:
            scan_result: Security scan result to evaluate
        
        Returns:
            True if scan passed policy, False if it should be blocked
        """
        # Check if scan type is enabled
        scan_policy = self.policy.get(scan_result.scan_type, {})
        if not scan_policy.get("enabled", True):
            logger.info(f"{scan_result.scan_type} scanning is disabled")
            return True
        
        # Evaluate each severity level
        should_block = False
        
        for severity in VulnerabilitySeverity:
            count = scan_result.summary.get(severity.value, 0)
            threshold = self.get_threshold(scan_result.scan_type, severity)
            
            max_allowed = threshold.get("max_allowed", 999)
            action = SecurityAction(threshold.get("action", "info"))
            
            if count > max_allowed:
                logger.warning(
                    f"Security threshold exceeded",
                    extra={
                        "scan_type": scan_result.scan_type,
                        "severity": severity.value,
                        "count": count,
                        "max_allowed": max_allowed,
                        "action": action.value,
                    }
                )
                
                if action == SecurityAction.BLOCK:
                    should_block = True
        
        return not should_block
    
    def is_vulnerability_allowed(self, violation: SecurityViolation) -> bool:
        """
        Check if a vulnerability is in the allowlist.
        
        Args:
            violation: Security violation to check
        
        Returns:
            True if violation is allowed (false positive or exception)
        """
        scan_policy = self.policy.get(violation.violation_type, {})
        allowlist = scan_policy.get("allowlist", [])
        
        for allowed in allowlist:
            # Check CVE allowlist
            if violation.cve and allowed.get("cve") == violation.cve:
                # Check if exception has expired
                expires = allowed.get("expires")
                if expires:
                    expiry_date = datetime.fromisoformat(expires)
                    if datetime.utcnow() > expiry_date:
                        logger.warning(
                            f"Allowlist exception expired",
                            extra={
                                "cve": violation.cve,
                                "expires": expires,
                            }
                        )
                        continue
                
                logger.info(
                    f"Vulnerability allowed by policy",
                    extra={
                        "cve": violation.cve,
                        "reason": allowed.get("reason"),
                    }
                )
                return True
            
            # Check pattern allowlist (for secrets)
            if violation.violation_type == "secrets":
                pattern = allowed.get("pattern", "")
                if pattern and pattern in violation.message:
                    logger.info(
                        f"Secret allowed by policy",
                        extra={
                            "pattern": pattern,
                            "reason": allowed.get("reason"),
                        }
                    )
                    return True
        
        return False
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """Get observability metrics configuration."""
        return self.policy.get("observability", {}).get("metrics", [])
    
    def get_alert_config(self, alert_type: str) -> Dict[str, Any]:
        """Get alert configuration for a specific alert type."""
        alerts = self.policy.get("observability", {}).get("alerts", {})
        return alerts.get(alert_type, {})
    
    def should_send_alert(self, alert_type: str, violation: SecurityViolation) -> bool:
        """
        Determine if an alert should be sent for a violation.
        
        Args:
            alert_type: Type of alert (critical_vulnerability, high_vulnerability, etc.)
            violation: Security violation
        
        Returns:
            True if alert should be sent
        """
        alert_config = self.get_alert_config(alert_type)
        
        if not alert_config.get("enabled", False):
            return False
        
        # Check severity matches alert type
        if alert_type == "critical_vulnerability":
            return violation.severity == VulnerabilitySeverity.CRITICAL
        elif alert_type == "high_vulnerability":
            return violation.severity == VulnerabilitySeverity.HIGH
        
        return False
    
    def audit_security_decision(
        self,
        decision: str,
        scan_result: SecurityScanResult,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Audit a security policy decision.
        
        Args:
            decision: Decision made (allowed, blocked, warned)
            scan_result: Security scan result
            context: Additional context
        """
        audit_config = self.policy.get("governance", {}).get("audit", {})
        
        if not audit_config.get("enabled", True):
            return
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "scan_result": scan_result.to_dict(),
            "environment": self.environment,
            "context": context or {},
        }
        
        # Log to configured destination
        destination = audit_config.get("destination", "memory_substrate")
        
        if destination == "memory_substrate":
            # TODO: Integrate with memory substrate
            logger.info(
                "Security decision audited",
                extra=audit_entry
            )
        else:
            logger.info(
                "Security decision audited",
                extra=audit_entry
            )


# =============================================================================
# Singleton instance
# =============================================================================
_security_policy_service: Optional[SecurityPolicyService] = None


def get_security_policy_service() -> SecurityPolicyService:
    """Get singleton security policy service instance."""
    global _security_policy_service
    
    if _security_policy_service is None:
        _security_policy_service = SecurityPolicyService()
    
    return _security_policy_service


# =============================================================================
# Convenience functions
# =============================================================================

def evaluate_security_scan(scan_result: SecurityScanResult) -> bool:
    """Evaluate a security scan result against policy."""
    service = get_security_policy_service()
    return service.evaluate_scan_result(scan_result)


def is_vulnerability_allowed(violation: SecurityViolation) -> bool:
    """Check if a vulnerability is allowed by policy."""
    service = get_security_policy_service()
    return service.is_vulnerability_allowed(violation)


def audit_security_decision(
    decision: str,
    scan_result: SecurityScanResult,
    context: Optional[Dict[str, Any]] = None
):
    """Audit a security policy decision."""
    service = get_security_policy_service()
    service.audit_security_decision(decision, scan_result, context)
