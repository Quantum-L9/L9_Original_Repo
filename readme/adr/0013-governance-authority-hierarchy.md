# ADR 0013: Governance Authority Hierarchy

## Status
Accepted

## Pattern
Strict authority hierarchy: Igor > L > Research Agents > Mac Agent; high-risk tools require approval.

## Files
- `core/governance/approval_manager.py` - Approval flow
- `config/policies/high_risk_tools.yaml` - Tool classifications
- `readme/repo-index/governance_model.txt` - Authority model

## Authority Hierarchy
```
IGOR (Human) ─────────────────────────────────────────
    │  FULL authority. Approves/rejects all high-risk.
    │  Only Igor can:
    │    - Approve high-risk tools
    │    - Grant permanent approvals
    │    - Override safety constraints
    ▼
L (CTO Agent) ─────────────────────────────────────────
    │  Autonomous within safety envelope.
    │  Must escalate high-risk to Igor.
    ▼
Research/Coder Agents ─────────────────────────────────
    │  Limited scope. Read-only + approved actions.
    ▼
Mac Agent ─────────────────────────────────────────────
       Lowest authority. Shell only with approval.
```

## High-Risk Tools (Require Igor Approval)
| Tool | Risk | Why |
|------|------|-----|
| `gmp_run` | Code changes | Modifies production code |
| `git_commit` | Persistence | Creates permanent record |
| `git_push` | Propagation | Sends to remote |
| `file_delete` | Destruction | Irreversible |
| `deploy` | Production | Affects live system |
| `mac_agent_exec` | Shell | Arbitrary commands |

## Approval Flow
```
Agent requests tool
       │
       ▼
ApprovalManager.requires_approval(tool_id)
       │
       ├── NO ──→ Execute immediately
       │
       └── YES ──→ request_approval()
                       │
                       ├── Store approval_request packet
                       ├── Notify Igor via Slack
                       └── Wait for approve_task() / reject_task()
```

## Igor Commands
| Command | Action |
|---------|--------|
| `@L approve <task_id>` | Approve pending task |
| `@L reject <task_id> <reason>` | Reject with reason |
| `@L rollback <task_id>` | Rollback completed task |
| `@L status` | Show pending approvals |

## Rules
1. HIGH_RISK_TOOLS always require Igor approval
2. Approval valid for single execution
3. Rejection logs reason for learning
4. All approvals create GovernancePattern packet
5. Mac Agent NEVER executes without approval

## AI Guidance
**DO:**
- Check `requires_approval()` before tool dispatch
- Emit approval_request packet
- Wait for explicit approve/reject
- Log all governance decisions

**DO NOT:**
- Auto-approve high-risk tools
- Skip approval for "simple" commands
- Let agents approve their own requests
- Execute rejected tools
