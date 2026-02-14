# Package Wiring Audit: ci

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `ci`

Files checked: 20
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 19
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `ci/auto_fix_adr.py` | 0 | 1 | - | - | ENTRY |
| `ci/check_adr_compliance.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_definition_of_done.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_dependency_patterns.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_global_state.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_imports.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_memory_bypass.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_no_deprecated_services.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_noqa_placement.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_packet_type_naming.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_report_naming.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_schema_deprecation.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_substrate_api.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_syntax.py` | 1 | 0 | - | - | PARTIAL |
| `ci/check_tool_naming.py` | 0 | 0 | - | - | ENTRY |
| `ci/check_tool_wiring.py` | 0 | 0 | - | - | ENTRY |
| `ci/dora_compliance_check.py` | 0 | 0 | - | - | ENTRY |
| `ci/lint_forbidden_imports.py` | 0 | 0 | - | - | ENTRY |
| `ci/validate_codegen.py` | 0 | 0 | - | - | ENTRY |
| `ci/validate_spec_v25.py` | 0 | 0 | - | - | ENTRY |

## Level C: API Instantiation — `ci`

API Status: **NO_API_NEEDED**
Symbols checked: 0
- USED: 0
- TEST_ONLY: 0
- UNUSED: 0
