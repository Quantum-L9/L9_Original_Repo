# L9 Deployment Philosophy

> **Core Principle:** Time spent planning and ironing out all creases prior to deployment saves time by avoiding redeployment.

---

## The Cost of Getting It Wrong

| Approach                  | Time Investment                                 | Risk |
| ------------------------- | ----------------------------------------------- | ---- |
| **Rush to deploy**        | 1 hour deploy + 4-8 hours debugging/redeploying | High |
| **Plan thoroughly first** | 2-3 hours planning + 1 hour deploy              | Low  |

**Net savings:** 2-6 hours per deployment cycle

---

## Pre-Deployment Checklist

### Before ANY Production Deployment:

1. **Resource Verification**

   - [ ] Server specs match manifest requirements (RAM, CPU, disk)
   - [ ] All ports will be accessible (firewall rules planned)
   - [ ] SSH access confirmed and tested

2. **Credential Management**

   - [ ] All passwords documented in `.env.local` (not committed)
   - [ ] Secrets are unique per environment (not shared between prod/staging)
   - [ ] Default passwords changed before deployment

3. **Rollback Plan**

   - [ ] Rollback script exists and tested
   - [ ] Data backup strategy documented
   - [ ] Know exactly how to undo each step

4. **Dependency Order**

   - [ ] Deployment order documented (namespace → secrets → databases → app)
   - [ ] Health checks will confirm each component before proceeding
   - [ ] Failure at any step has clear recovery path

5. **Validation Gates**
   - [ ] Each component has health endpoint
   - [ ] Success criteria defined (what does "working" look like?)
   - [ ] Smoke tests ready to run post-deployment

---

## Critical Deployment Rules

### Rule 1: Never Deploy Untested Configs

> If you haven't validated the YAML locally, don't deploy it remotely.

### Rule 2: One Change at a Time

> Deploy incrementally. Verify each component before adding the next.

### Rule 3: Document Everything

> If you can't explain how to undo it, don't do it.

### Rule 4: Assume Failure

> Every command should have a "what if this fails?" answer ready.

### Rule 5: Test SSH First

> If you can't SSH in, you can't fix anything. Verify access before deployment.

---

## Environment Separation

| Environment     | Purpose          | Data      | Credentials            |
| --------------- | ---------------- | --------- | ---------------------- |
| **Production**  | Live system      | Real      | Unique, rotated        |
| **Staging**     | Pre-prod testing | Synthetic | Separate from prod     |
| **Development** | Local testing    | Mock      | Can share with staging |

**Rule:** Staging credentials MUST NOT work on production. Ever.

---

## When Staging Becomes Production

If a staging environment is promoted to production:

1. **Rotate ALL credentials** - staging passwords are now compromised
2. **Audit all access** - who had staging access?
3. **Update documentation** - server names, IPs, access lists
4. **Notify stakeholders** - deployment URLs change
5. **Update monitoring** - alerts should reflect production SLAs

---

## Lessons Learned

_Add entries here after each deployment:_

### 2026-01-21: C1 Initial Setup

- **Issue:** SSH key not pre-configured on server rebuild
- **Lesson:** Add SSH keys to Hetzner project BEFORE creating servers
- **Resolution:** Use Hetzner SSH Keys feature + Rebuild

---

_"Measure twice, cut once."_ — Every carpenter who doesn't waste wood
