# L9 Security Scanning System

**Version:** 1.0.0
**Created:** 2026-01-21
**Status:** Production Ready

## Overview

The L9 Security Scanning System is a comprehensive, automated security infrastructure that integrates with the L9 governance engine, observability stack, and CI/CD pipelines to provide continuous security monitoring and enforcement.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    L9 Security System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   CI/CD      │  │  Governance  │  │ Observability│      │
│  │   Workflow   │──│    Engine    │──│    Stack     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────────────────────────────────────────┐      │
│  │          Security Scanning Layers                 │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  1. SAST (Bandit + Semgrep)                      │      │
│  │  2. Dependency Scanning (Safety + pip-audit)     │      │
│  │  3. Secret Detection (TruffleHog + detect-secrets)│      │
│  │  4. Container Scanning (Trivy)                   │      │
│  │  5. Policy Enforcement (config/security_policy)  │      │
│  └──────────────────────────────────────────────────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Metrics    │  │    Alerts    │  │  Dashboard   │      │
│  │ (Prometheus) │  │ (Slack/Email)│  │  (Grafana)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. CI/CD Integration

**File:** `.github/workflows/security-comprehensive.yml`

Automated security scanning in GitHub Actions with 5 jobs:

1. **SAST Scan** - Static code analysis

   - Bandit (Python security linter)
   - Semgrep (multi-language SAST)
   - Uploads results to GitHub Security tab

2. **Dependency Scan** - Vulnerability scanning

   - Safety (Python package vulnerabilities)
   - pip-audit (PyPI vulnerability database)
   - Checks against known CVEs

3. **Secret Scan** - Credential detection

   - TruffleHog (git history scanning)
   - detect-secrets (pre-commit integration)
   - Scans full repository history

4. **Container Scan** - Docker image security

   - Trivy (comprehensive container scanner)
   - Scans base images and dependencies
   - Integrates with GitHub Security

5. **Security Report** - Consolidated reporting
   - Generates comprehensive JSON report
   - Creates markdown summary
   - Comments on PRs with results

**Triggers:**

- Every push to `main` or `develop`
- Every pull request
- Daily at 2 AM UTC (scheduled scan)
- Manual trigger via workflow_dispatch

### 2. Security Policy Configuration

**File:** `config/security_policy.yaml`

Centralized security policy defining:

- **Thresholds** for each severity level (CRITICAL, HIGH, MEDIUM, LOW)
- **Actions** (block, warn, info) for policy violations
- **Allowlists** for false positives and exceptions
- **Environment-specific overrides** (dev, staging, prod)
- **Compliance standards** (OWASP Top 10, CWE Top 25)
- **Observability configuration** (metrics, alerts)

**Example threshold:**

```yaml
sast:
  thresholds:
    critical:
      max_allowed: 0
      action: block # Blocks PR merge
    high:
      max_allowed: 5
      action: block
```

### 3. Governance Integration

**File:** `core/governance/security_policy.py`

Runtime security policy enforcement:

- **SecurityPolicyService** - Main service class
- **SecurityViolation** - Violation data model
- **SecurityScanResult** - Scan result aggregation
- **Policy evaluation** - Threshold checking
- **Allowlist management** - Exception handling
- **Audit logging** - Decision tracking

**Usage:**

```python
from core.governance.security_policy import evaluate_security_scan, SecurityScanResult

# Evaluate scan results
scan_result = SecurityScanResult(...)
passed = evaluate_security_scan(scan_result)

if not passed:
    # Block deployment
    raise SecurityPolicyViolation("Critical vulnerabilities detected")
```

### 4. Observability & Metrics

**File:** `core/observability/security_metrics.py`

Prometheus metrics collection:

- `l9_security_scan_duration_seconds` - Scan performance
- `l9_security_vulnerabilities_total` - Vulnerability counts
- `l9_security_scan_failures_total` - Scan failures
- `l9_security_policy_violations_total` - Policy violations
- `l9_security_score` - Overall security score (0-100)

**Grafana Dashboard:**

- Security score gauge
- Vulnerabilities by severity graph
- Scan duration trends
- Policy violation stats
- Secrets detected table

### 5. Alerting System

**File:** `core/observability/security_alerts.py`

Multi-channel alert delivery:

- **Slack** - Real-time notifications
- **Email** - Detailed reports
- **PagerDuty** - Critical incident management
- **Webhook** - Custom integrations

**Alert Types:**

- `critical_vulnerability` - CRITICAL vulnerabilities detected
- `high_vulnerability` - HIGH vulnerabilities detected
- `secret_detected` - Secrets found in code
- `policy_violation` - Security policy violated
- `scan_failure` - Security scan failed

**Deduplication:** 15-minute window to prevent alert fatigue

## Installation & Setup

### 1. Install Dependencies

```bash
# Install security scanning tools
pip install bandit[toml] bandit-sarif-formatter
pip install semgrep
pip install safety pip-audit
pip install detect-secrets

# Install TruffleHog
curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin

# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

### 2. Configure Environment Variables

```bash
# Slack alerting
export L9_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Email alerting
export L9_EMAIL_SMTP_HOST="smtp.gmail.com"
export L9_EMAIL_FROM="security@l9.ai"

# PagerDuty alerting
export L9_PAGERDUTY_INTEGRATION_KEY="your-pagerduty-key"

# Environment
export L9_ENVIRONMENT="production"  # or development, staging
```

### 3. Enable GitHub Actions

The security workflow is automatically enabled. To configure:

1. Go to repository Settings → Secrets and variables → Actions
2. Add required secrets:
   - `SLACK_WEBHOOK_URL` (optional)
   - `PAGERDUTY_KEY` (optional)

### 4. Configure Security Policy

Edit `config/security_policy.yaml` to customize:

- Severity thresholds
- Allowlisted vulnerabilities
- Environment-specific rules
- Alert channels and recipients

### 5. Set Up Grafana Dashboard

```bash
# Generate dashboard JSON
python3 << 'EOF'
from core.observability.security_metrics import get_grafana_dashboard_json
import json

dashboard = get_grafana_dashboard_json()
with open('grafana-security-dashboard.json', 'w') as f:
    json.dump(dashboard, f, indent=2)

print("Dashboard JSON generated: grafana-security-dashboard.json")
EOF

# Import to Grafana
# 1. Open Grafana
# 2. Go to Dashboards → Import
# 3. Upload grafana-security-dashboard.json
```

## Usage

### Running Security Scans Locally

```bash
# Run SAST scan
bandit -r . -f json -o bandit-report.json

# Run dependency scan
safety check --json

# Run secret detection
detect-secrets scan

# Run container scan
trivy fs .
```

### Checking Security Score

```python
from core.observability.security_metrics import calculate_security_score

scan_results = {
    "sast": {"critical": 0, "high": 2, "medium": 5, "low": 10},
    "dependencies": {"critical": 0, "high": 1, "medium": 3, "low": 5},
    "secrets": {"critical": 0},
    "containers": {"critical": 0, "high": 3, "medium": 10, "low": 20}
}

score = calculate_security_score(scan_results)
print(f"Security Score: {score}/100")
```

### Sending Custom Alerts

```python
from core.observability.security_alerts import send_vulnerability_alert

send_vulnerability_alert(
    scan_type="sast",
    severity="high",
    count=3,
    details={
        "file": "api/routes/auth.py",
        "line": 42,
        "issue": "SQL injection vulnerability"
    }
)
```

## Security Thresholds

### Default Thresholds (Production)

| Scan Type        | Critical  | High      | Medium    | Low        |
| ---------------- | --------- | --------- | --------- | ---------- |
| **SAST**         | 0 (block) | 0 (block) | 20 (warn) | 50 (info)  |
| **Dependencies** | 0 (block) | 3 (warn)  | 10 (info) | 50 (info)  |
| **Secrets**      | 0 (block) | -         | -         | -          |
| **Containers**   | 0 (warn)  | 10 (warn) | 50 (info) | 100 (info) |

### Development Environment

More lenient thresholds for faster iteration:

- HIGH vulnerabilities: warn instead of block
- Secrets: only scan current commit (not full history)

## Compliance

The security system helps meet compliance requirements for:

- **OWASP Top 10** - Web application security risks
- **CWE Top 25** - Most dangerous software weaknesses
- **SANS Top 25** - Most dangerous programming errors
- **SOC 2** - Security and availability controls
- **ISO 27001** - Information security management

## Metrics & Monitoring

### Key Metrics

1. **Security Score** - Overall security posture (0-100)
2. **Vulnerability Count** - By type and severity
3. **Scan Duration** - Performance tracking
4. **Policy Violations** - Governance enforcement
5. **Mean Time to Remediation** - Response effectiveness

### Grafana Queries

```promql
# Security score
l9_security_score{environment="production"}

# Critical vulnerabilities
sum(l9_security_vulnerabilities_total{severity="critical"})

# Scan duration (p95)
histogram_quantile(0.95, l9_security_scan_duration_seconds)

# Policy violations per day
rate(l9_security_policy_violations_total[24h])
```

## Troubleshooting

### Scan Failures

**Issue:** Security scan fails in CI/CD

**Solutions:**

1. Check tool installation: `bandit --version`, `semgrep --version`
2. Review scan logs in GitHub Actions artifacts
3. Verify file permissions and exclusions
4. Check for syntax errors in Python files

### False Positives

**Issue:** Legitimate code flagged as vulnerable

**Solution:**
Add to allowlist in `config/security_policy.yaml`:

```yaml
sast:
  allowlist:
    - pattern: "test_api_key_12345"
      reason: "Test fixture, not a real secret"
```

### Alert Fatigue

**Issue:** Too many alerts

**Solutions:**

1. Adjust thresholds in `config/security_policy.yaml`
2. Enable deduplication (default: 15 minutes)
3. Use different channels for different severities
4. Set up alert aggregation (daily digest)

## Best Practices

### 1. Fail-Closed by Default

- Block on CRITICAL vulnerabilities
- Require manual approval for exceptions
- Audit all security decisions

### 2. Defense in Depth

- Multiple scanning tools per category
- Pre-commit hooks + CI/CD + runtime checks
- Continuous monitoring and alerting

### 3. Shift Left

- Run scans early in development
- Provide fast feedback to developers
- Integrate with IDE and pre-commit hooks

### 4. Continuous Improvement

- Review security metrics weekly
- Update policies based on trends
- Track mean time to remediation
- Conduct regular security reviews

### 5. Least Privilege

- Limit access to security configurations
- Require approval for policy changes
- Audit all security-related actions

## Integration Points

### With L9 Governance

```python
from core.governance.engine import GovernanceEngineService
from core.governance.security_policy import get_security_policy_service

# Security policy is automatically loaded by governance engine
gov_engine = GovernanceEngineService()
sec_policy = get_security_policy_service()

# Policies are enforced at runtime
```

### With L9 Observability

```python
from core.observability.security_metrics import record_vulnerabilities
from core.observability.security_alerts import send_vulnerability_alert

# Metrics are automatically collected
record_vulnerabilities("sast", "high", 3)

# Alerts are sent based on policy
send_vulnerability_alert("sast", "critical", 1, {...})
```

### With L9 Memory Substrate

Security decisions are audited to the memory substrate:

```python
from core.governance.security_policy import audit_security_decision

audit_security_decision(
    decision="blocked",
    scan_result=scan_result,
    context={"pr_number": 123, "author": "user@example.com"}
)
```

## Roadmap

### Phase 1 (Complete)

- ✅ CI/CD integration
- ✅ Security policy configuration
- ✅ Governance integration
- ✅ Metrics and alerting
- ✅ Documentation

### Phase 2 (Q1 2026)

- 🔄 Machine learning for vulnerability prioritization
- 🔄 Automated remediation suggestions
- 🔄 Security score trending and forecasting
- 🔄 Integration with external threat intelligence

### Phase 3 (Q2 2026)

- 📅 Runtime application self-protection (RASP)
- 📅 Advanced behavioral analysis
- 📅 Security chaos engineering
- 📅 Compliance automation (SOC 2, ISO 27001)

## Support

For questions or issues:

1. Check this documentation
2. Review `config/security_policy.yaml` for configuration
3. Check GitHub Actions logs for scan details
4. Review Grafana dashboards for metrics
5. Contact security team: security@l9.ai

## License

Copyright © 2026 L9 AI OS. All rights reserved.

---

**Last Updated:** 2026-01-21
**Version:** 1.0.0
**Maintainer:** Security Team
