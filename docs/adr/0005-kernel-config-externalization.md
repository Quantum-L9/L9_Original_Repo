# ADR-0005: Kernel Configuration Externalization

## Status

**Status:** Accepted  
**Date:** 2026-01-20  
**Author:** @l-cto  
**Stakeholders:** @kernel-team, @devops-team  
**Supersedes:** None  
**Superseded by:** None

## Context

L9's kernel loading order (`KERNEL_ORDER`) was hard-coded in `runtime/kernel_loader.py`. This approach had several limitations:

1. **No Environment-Specific Config** - Same kernel order for dev/test/staging/prod
2. **Code Changes Required** - Changing kernel order requires code changes
3. **No Feature Flags** - Can't gradually roll out kernel changes
4. **No Validation** - No validation of kernel configuration
5. **No Governance** - No approval gates for kernel changes (T3 finding)
6. **No Observability** - Hard to track kernel configuration changes

As L9 deploys to multiple environments (dev, test, staging, production), we need environment-specific kernel configuration without code changes.

## Decision

Externalize kernel configuration to `config/kernel_discovery.yaml` with:

1. **Environment-Specific Overrides** - Different kernel order per environment
2. **Feature Flags** - Gradual rollout with `L9_USE_KERNEL_CONFIG`
3. **Validation** - Validate required fields, types, values
4. **Fallback** - Fall back to hard-coded config if loading fails
5. **Observability** - Log kernel configuration loading

**Configuration Structure:**
```yaml
kernel_order:
  - "00_system"
  - "01_memory"
  - "02_cognitive"
  - ...

required_kernels:
  - "00_system"
  - "01_memory"

minimum_kernel_count: 2

environments:
  dev:
    kernel_order: ["00_system"]  # Minimal for fast iteration
  test:
    kernel_order: ["00_system", "01_memory"]  # 2 kernels for tests
  staging:
    kernel_order: [...]  # Full kernel set
  production:
    kernel_order: [...]  # Full kernel set + strict validation
```

## Rationale

1. **Environment Awareness** - Different kernel order per environment
2. **No Code Changes** - Change config without code changes
3. **Feature Flags** - Gradual rollout with `L9_USE_KERNEL_CONFIG`
4. **Validation** - Catch config errors early
5. **Governance** - Config changes go through PR review (T3 protection)
6. **Observability** - Track kernel configuration changes
7. **Backward Compatibility** - Falls back to hard-coded config

## Alternatives Considered

### Alternative 1: Keep Hard-Coded Kernel Order

- **Pros:** Simple, no config file needed
- **Cons:** No environment-specific config, code changes required
- **Why rejected:** Doesn't scale to multiple environments

### Alternative 2: Use Environment Variables for Kernel Order

- **Pros:** No config file, easy to override
- **Cons:** Hard to manage complex config, no validation, no version control
- **Why rejected:** Environment variables are for secrets, not complex config

### Alternative 3: Use Python Config File (config.py)

- **Pros:** Python syntax, can use logic
- **Cons:** Requires Python execution, harder to validate, security risk
- **Why rejected:** YAML is safer and easier to validate

### Alternative 4: Use Database for Kernel Config

- **Pros:** Dynamic config, no deployment needed
- **Cons:** Adds dependency, harder to version control, overkill
- **Why rejected:** Config should be in git for traceability

## Consequences

### Positive

1. **Environment Awareness** - Different kernel order per environment
2. **No Code Changes** - Change config without code changes
3. **Feature Flags** - Gradual rollout with `L9_USE_KERNEL_CONFIG`
4. **Validation** - Catch config errors early
5. **Governance** - Config changes go through PR review
6. **Observability** - Track kernel configuration changes
7. **Backward Compatibility** - Falls back to hard-coded config

### Negative

1. **Config File Management** - Need to maintain `kernel_discovery.yaml`
2. **Validation Overhead** - Config validation adds startup time (~10ms)
3. **Complexity** - Another layer of configuration
4. **Potential Misconfiguration** - Wrong config can break kernel loading

### Neutral

1. **Feature Flag** - `L9_USE_KERNEL_CONFIG` controls config loading
2. **Fallback** - Falls back to hard-coded config if loading fails

## Implementation

### Migration Path

**Phase 1: Create Config File (PR #23)** ✅ Complete
1. Create `config/kernel_discovery.yaml`
2. Define kernel order for all environments
3. Add validation rules

**Phase 2: Create Config Loader (PR #23)** ✅ Complete
1. Create `runtime/kernel_config_loader.py`
2. Implement config loading with validation
3. Implement environment override logic
4. Add 27 comprehensive tests

**Phase 3: Integrate with Kernel Loader (PR #23)** ✅ Complete
1. Modify `runtime/kernel_loader.py` to load config
2. Add fallback to hard-coded config
3. Add feature flag `L9_USE_KERNEL_CONFIG`

**Phase 4: Rollout (Week 3-4)**
1. Week 1: Deploy to dev with `L9_ENV=dev`
2. Week 2: Deploy to test with `L9_ENV=test`
3. Week 3: Deploy to staging with `L9_ENV=staging`
4. Week 4: Deploy to production with `L9_ENV=production`

### Rollback Strategy

If config loading causes issues:

1. **Disable Config Loading**
   ```bash
   export L9_USE_KERNEL_CONFIG=false
   ```
   This reverts to hard-coded `KERNEL_ORDER` in `kernel_loader.py`.

2. **Fix Config File**
   - Update `config/kernel_discovery.yaml`
   - Deploy fixed config

3. **Revert PR**
   ```bash
   git revert <pr-23-commit>
   git push origin main
   ```

### Validation

Success criteria:
- ✅ Config file created with all environments
- ✅ Config loader implemented and tested
- ✅ Kernel loader integrated with config
- ✅ 27 tests passing
- ✅ Feature flag working
- ✅ Fallback working
- ✅ Validation working

## Metadata

**Category:** Infrastructure  
**Impact:** High  
**Tier:** T3 (Kernel modification, requires approval)  
**Related PRs:** #23  
**Related ADRs:** ADR-0004 (DI/DIP Foundation)  
**References:**
- [Phase 0-6 Execution Roadmap](../../L9-PHASE-0-6-EXECUTION-ROADMAP.md)
- [T3-1: Kernel Governance Gap](../../L9-PHASE-0-6-EXECUTION-ROADMAP.md#t3-1-kernel-governance-gap)

## Notes

This is a **T3 decision** (kernel modification) that requires approval from @l-cto and @kernel-team.

The kernel configuration externalization addresses the **T3-1: Kernel Governance Gap** finding from the Phase 0-6 Execution Roadmap. It enables environment-specific kernel configuration without code changes, improving governance and observability.

The key insight is that **kernel configuration should be externalized** to enable environment-specific behavior without code changes. This aligns with the 12-factor app principle of "config in environment".

The feature flag `L9_USE_KERNEL_CONFIG` enables gradual rollout and easy rollback if issues arise.
