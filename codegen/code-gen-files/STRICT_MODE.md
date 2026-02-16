# L9 STRICT MODE - CI Enforcement Policy

## Overview

L9 operates in STRICT MODE for all CI pipelines. This document defines what is enforced and what is NOT allowed.

## Enforcement Points

### 1. Before Codegen Merge
- `ci/validate_spec_v25.py` MUST pass
- ALL v2.5 required sections must be present
- NO placeholders allowed in production specs
- NO missing keystone blocks

### 2. Before Docker Build
- `ci/validate_codegen.py` MUST pass
- ALL files in repo manifest
- ALL tests present
- NO forbidden imports (logging, aiohttp, requests)
- NO print() statements

### 3. Before Deployment
- ALL specs in repo pass validation
- Docker smoke tests pass
- No unacknowledged global invariants

## What is FORBIDDEN

### In Specs
- `if applicable` - All sections are required
- Optional runtime wiring - Must be explicit
- Inferred dependencies - Must be declared
- Undeclared packet emission - Must be in packet_contract
- Implicit boot behavior - Must be explicit
- Silent failure - Must emit error packet
- Undeclared tier - Must be in MODULE_REGISTRY

### In Code Generation
- Files outside allowed_new_files or allowed_modified_files
- Missing test files when acceptance criteria exists
- Using `logging` instead of `structlog`
- Using `aiohttp` or `requests` instead of `httpx`
- Using `uuid4` for thread_id (must be UUIDv5)
- Using `print()` for output

### In Parsers
- `model_config = {"extra": "allow"}` for spec models
- `default_factory` for required sections
- Falling back to defaults when section missing
- Inferring tier from context
- Inferring dependencies from imports

## What is ALLOWED

### Best-Effort Patterns (Runtime Only)
These patterns are allowed at RUNTIME for resilience, but NOT for spec/code validation:

1. **Packet Emission**: Best-effort, non-blocking
   - Observability should not break execution
   - Documented explicitly in executor

2. **Metric Collection**: Best-effort
   - Telemetry should not break execution

3. **Logging Flush on Shutdown**: Best-effort
   - Graceful degradation allowed

## Validation Commands

```bash
# Validate single spec
make ci-spec SPEC=path/to/spec.yaml

# Validate generated code
make ci-code SPEC=path/to/spec.yaml FILES='file1.py file2.py'

# Full CI gate check
./ci/run_ci_gates.sh spec.yaml file1.py file2.py

# Validate all specs in repo
make ci-all-specs
```

## Exit Codes

- **0**: All validations passed
- **1**: Validation failed - FIX REQUIRED
- **2**: Configuration error (file not found, parse error)

## Consequences of Failure

When CI gates fail:
1. **Merge blocked**: Cannot merge to main
2. **Build blocked**: Cannot build Docker image
3. **Deploy blocked**: Cannot deploy to VPS
4. **Human intervention required**: C must fix issues manually

This is intentional. Bad output cannot enter the repo.

