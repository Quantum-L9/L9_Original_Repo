# CURSOR-RUNBOOK: L9 PRE-COMMIT SECURITY GATES IMPLEMENTATION
## Enterprise-Grade Deployment Guide

**Last Updated:** 2026-01-19  
**Risk Tier:** T2 (Reversible)  
**Implementation Time:** 45 minutes  
**Rollback Time:** 5 minutes  

---

## PHASE 0-1: ASSESSMENT & BACKUP

### Step 1: Verify Current State
```bash
# Check existing pre-commit hook
ls -la .git/hooks/pre-commit
file .git/hooks/pre-commit

# Backup current setup
mkdir -p .git/hooks/.backups
cp .git/hooks/pre-commit .git/hooks/.backups/pre-commit.backup.$(date +%Y%m%d)

# List staged files that would be affected
git diff --cached --name-only | head -20
```

**Expected Output:**
- File exists and is executable
- Backup created successfully
- Staged files count ≥0

### Step 2: Check Dependencies
```bash
# Verify required tools installed
which gitleaks ruff mypy pytest curl git

# Check versions
ruff --version
mypy --version
pytest --version
gitleaks --version
```

**Missing Tools? Install:**
```bash
# macOS
brew install gitleaks

# Linux (Ubuntu/Debian)
apt-get install git

# Python tools
pip install --upgrade ruff mypy pytest pytest-cov
```

---

## PHASE 1: DEPLOYMENT

### Step 3: Create Logging Infrastructure
```bash
# Create log directories with proper permissions
sudo mkdir -p /var/log/l9
sudo chmod 777 /var/log/l9

# Verify
ls -ld /var/log/l9
```

### Step 4: Deploy Enhanced Pre-Commit Hook
```bash
# From L9 repository root
chmod +x install-precommit-security.sh
./install-precommit-security.sh

# Verify deployment
ls -la .git/hooks/pre-commit
file .git/hooks/pre-commit
head -20 .git/hooks/pre-commit
```

**Expected Output:**
```
.git/hooks/pre-commit: Bourne-again shell script text executable
✓ Deployed enhanced pre-commit hook
✓ Pre-commit hook is executable
✓ Installation complete!
```

### Step 5: Configure Environment Variables
```bash
# Add to ~/.bashrc, ~/.zshrc, or .env.local
export HOOK_AUDIT_LOG=/var/log/l9/pre-commit-hooks.jsonl
export AI_SEC_LOG=/var/log/l9/ai_security.jsonl
export TEST_LOG=/var/log/l9/test_execution.jsonl
export PROMETHEUS_PUSHGATEWAY=http://localhost:9091  # Optional

# Optional: Splunk SIEM integration
export SIEM_HEC_URL=https://splunk.example.com:8088/services/collector
export SIEM_HEC_TOKEN=your-hec-token-here

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

---

## PHASE 2: VALIDATION & TESTING

### Step 6: Test on Feature Branch (Safe)
```bash
# Switch to feature branch (NOT main)
git checkout -b test/precommit-validation

# Make a test commit
git commit --allow-empty -m "test: verify pre-commit security gates"

# Watch for all 8 gates to pass
```

**Expected Output:**
```
🔐 L9 ENTERPRISE PRE-COMMIT SECURITY GATES
==========================================
Branch: test/precommit-validation | User: cryptoxdog

[GATE 0/8] BRANCH PROTECTION CHECK
✓ Branch protection verified (main branch bypass impossible)

[GATE 1/8] SECRET SCANNING
✓ No secrets detected

[GATE 2/8] AUTO-FORMAT PYTHON (ruff)
✓ Code formatted with ruff

[GATE 3/8] LINT PYTHON (ruff check)
✓ Lint checks passed (auto-fixed)

[GATE 4/8] TYPE CHECKING (STRICT MODE)
✓ Type checking passed (strict mode)

[GATE 5/8] AI SECURITY (PROMPT INJECTION DETECTION)
✓ AI security checks passed (no injection patterns)

[GATE 6/8] TEST EXECUTION + COVERAGE (≥75%)
✓ Tests passed with ≥75% coverage (12s)

[GATE 7/8] PROTECTED SURFACES CHECK
✓ Protected surfaces validated

[GATE 8/8] AUDIT LOGGING & METRICS
✓ Audit trail logged to: /var/log/l9/pre-commit-hooks.jsonl

✅ ALL GATES PASSED (8/8)
Duration: 18s
```

### Step 7: Verify Audit Logs
```bash
# Check hook execution log
tail -20 /var/log/l9/pre-commit-hooks.jsonl

# Check AI security violations log
tail -20 /var/log/l9/ai_security.jsonl

# Check test results log
tail -20 /var/log/l9/test_execution.jsonl

# Parse JSON logs for analysis
cat /var/log/l9/pre-commit-hooks.jsonl | jq '.[] | {timestamp, event_type, status, duration_seconds}'
```

**Expected Output:**
```json
{
  "timestamp": "2026-01-19T22:15:30+00:00",
  "event_type": "precommit_success",
  "status": "passed",
  "duration_seconds": 18,
  "checks_passed": 8
}
```

### Step 8: Test Protection on Main Branch
```bash
# Switch to main
git checkout main

# Attempt commit with bypass (should FAIL)
git commit --allow-empty --no-verify -m "test: bypass on main" 2>&1 || echo "✓ Bypass correctly blocked"

# Regular commit should WORK
git commit --allow-empty -m "test: normal commit on main" 2>&1 && echo "✓ Normal commit allowed" || true
```

**Expected Output:**
```
❌ CRITICAL: --no-verify / bypass blocked on main
   Branch: main is PROTECTED
   Emergency override: Contact security@l9.ai with incident ticket
```

---

## PHASE 3: CONFIGURATION & TUNING

### Step 9: Customize Protected Surfaces (Optional)
Edit `.git/hooks/pre-commit` line ~270 to add/remove protected files:

```bash
PROTECTED_SURFACES=(
    "orchestration/websocket_orchestrator.py"
    "memory/substrate_service.py"
    "core/kernel_loader.py"
    "docker-compose.yml"
    "core/packet.py"
    "core/auth.py"
    # Add custom files here:
    "path/to/your/critical/file.py"
)
```

### Step 10: Enable SIEM Integration (Optional)
```bash
# Configure Splunk HEC (HTTP Event Collector)
export SIEM_HEC_URL="https://your-splunk-instance:8088/services/collector"
export SIEM_HEC_TOKEN="your-hec-token"

# Or configure to a generic webhook
export SIEM_WEBHOOK_URL="https://your-security-platform/api/events"

# Test integration
.git/hooks/pre-commit --test-siem
```

### Step 11: Set Coverage Threshold (Optional)
Edit line ~297 in `.git/hooks/pre-commit`:

```bash
COVERAGE_THRESHOLD=75  # Change to your minimum (e.g., 80)
```

---

## PHASE 4: TEAM ROLLOUT

### Step 12: Document for Team
```bash
# Create team guidance document
cat > PRECOMMIT_SECURITY.md << 'EOF'
# L9 Pre-Commit Security Gates

## Overview
All commits are automatically validated against 8 security gates:
1. Branch protection (no bypass on main/production)
2. Secret scanning (gitleaks)
3. Code formatting (ruff)
4. Linting (ruff check)
5. Type checking (mypy --strict)
6. AI security (prompt injection detection)
7. Test execution (pytest, ≥75% coverage)
8. Protected surfaces (critical file validation)

## Common Issues & Solutions

### "Type errors found"
```bash
# Option 1: Fix the error
mypy --strict src/your_file.py

# Option 2: Add type: ignore (if necessary)
some_function()  # type: ignore[error-code]
```

### "Tests failed or coverage <75%"
```bash
# Run tests locally first
pytest --cov=. src/

# Add missing test coverage
```

### "Secret detected"
```bash
# Move to .env or environment variable
# Never commit credentials
git rm --cached .env
echo ".env" >> .gitignore
```

### "Bypass on main blocked"
```bash
# This is INTENTIONAL - no override via --no-verify on main
# For emergency:
1. Create issue: https://github.com/cryptoxdog/L9/issues
2. Tag: @security
3. Provide justification + risk assessment
4. Security team approves = human-in-the-loop (HITL)
```

## Monitoring
```bash
# Check recent commits passed all gates
tail -50 /var/log/l9/pre-commit-hooks.jsonl | jq '.[] | select(.status=="passed")'

# Check violations
cat /var/log/l9/ai_security.jsonl | jq '.[] | select(.severity=="CRITICAL")'
```

## Support
- Security questions: security@l9.ai
- Implementation issues: File GitHub issue
- SIEM integration: See SIEM_INTEGRATION.md
EOF

cat PRECOMMIT_SECURITY.md
```

### Step 13: Team Training Checklist
Send to team:

```markdown
## Pre-Commit Security Gates - Team Setup

**Before first commit, please:**

- [ ] Install missing tools: `pip install --upgrade ruff mypy pytest pytest-cov`
- [ ] Verify hook installation: `ls -la .git/hooks/pre-commit` (should be 600+ lines)
- [ ] Run test commit: `git commit --allow-empty -m "test: hook validation"`
- [ ] Check logs: `tail /var/log/l9/pre-commit-hooks.jsonl`
- [ ] Read runbook: PRECOMMIT_SECURITY.md
- [ ] Slack: @security with questions

**Gate timings (typical):**
- Secret scan: 2-3s
- Format/lint: 3-5s
- Type check: 5-8s
- AI security: 2-3s
- Tests: 10-30s (depends on coverage)
- **Total: ~25-50s per commit**

**Questions? Reach out:** security@l9.ai
```

---

## PHASE 5: MONITORING & MAINTENANCE

### Step 14: Setup Dashboard Queries
```bash
# Daily violations summary
jq -s 'group_by(.event_type) | map({event: .[0].event_type, count: length, latest: .[-1].timestamp})' /var/log/l9/pre-commit-hooks.jsonl

# Critical violations only
jq '.[] | select(.severity=="CRITICAL")' /var/log/l9/ai_security.jsonl

# Performance metrics (slowest commits)
jq -s 'sort_by(-.duration_seconds) | .[0:5]' /var/log/l9/pre-commit-hooks.jsonl
```

### Step 15: Weekly Health Check
```bash
#!/bin/bash
# Run weekly via cron

LOG_DIR=/var/log/l9

echo "📊 Pre-Commit Security Health Report"
echo "====================================="

# Check for concerning patterns
TOTAL_CHECKS=$(wc -l < "$LOG_DIR/pre-commit-hooks.jsonl")
FAILURES=$(grep -c '"status":"failure"' "$LOG_DIR/pre-commit-hooks.jsonl" || echo 0)
CRITICAL_AI=$(grep -c '"severity":"CRITICAL"' "$LOG_DIR/ai_security.jsonl" || echo 0)

echo "Total commits checked: $TOTAL_CHECKS"
echo "Failed checks: $FAILURES ($(echo "scale=2; $FAILURES*100/$TOTAL_CHECKS" | bc)%)"
echo "Critical AI violations: $CRITICAL_AI"

if [ $CRITICAL_AI -gt 0 ]; then
    echo ""
    echo "🚨 ALERT: Critical AI security violations detected!"
    grep '"severity":"CRITICAL"' "$LOG_DIR/ai_security.jsonl"
fi
```

---

## ROLLBACK PROCEDURE (If Needed)

```bash
# 1. Restore backup
cp .git/hooks/.backups/pre-commit.backup.YYYYMMDD .git/hooks/pre-commit

# 2. Verify restoration
.git/hooks/pre-commit --version

# 3. Test
git commit --allow-empty -m "rollback: restore previous pre-commit"

# 4. Document incident
echo "Rolled back to $(date)" >> .git/hooks/.backups/ROLLBACK_LOG

# 5. Notify team
# ...
```

---

## SUCCESS CRITERIA

✅ **All 8 gates execute without error**  
✅ **Audit logs being created at /var/log/l9/**  
✅ **Team can commit on feature branches**  
✅ **Bypass blocked on main branch**  
✅ **AI security checks find zero jailbreak patterns**  
✅ **Protected file validations trigger on changes**  
✅ **Tests execute and enforce ≥75% coverage**  
✅ **Prometheus metrics exported (optional)**  

---

## SUPPORT & ESCALATION

| Issue | Action |
|-------|--------|
| Hook fails on first commit | Run: `python3 -c "import sys; print(sys.version)"` (Python 3.8+ required) |
| Permission denied on logs | Run: `sudo chmod 777 /var/log/l9` |
| gitleaks not found | Run: `brew install gitleaks` (macOS) or `apt install gitleaks` (Linux) |
| Tests failing | Run locally first: `pytest --cov=. src/` |
| Bypass needed on main | Create GitHub issue with risk assessment, tag @security |
| Hook too slow (>60s) | Optimize test suite or split into separate modules |

**Emergency contact:** security@l9.ai
