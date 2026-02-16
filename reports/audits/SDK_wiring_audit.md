# Package Wiring Audit: SDK

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `SDK`

Files checked: 1
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `SDK/SDK.py` | 0 | 0 | - | Y | PARTIAL |

## Level C: API Instantiation — `SDK`

API Status: **HAS_API**
Symbols checked: 21
- USED: 3
- TEST_ONLY: 2
- UNUSED: 16

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `CheckpointsInterface` | 0 | 0 | UNUSED |
| `ComplianceInterface` | 0 | 0 | UNUSED |
| `GovernanceInterface` | 0 | 0 | UNUSED |
| `L9Facade` | 0 | 0 | UNUSED |
| `L9SDK` | 0 | 1 | TEST_ONLY |
| `LearningInterface` | 0 | 0 | UNUSED |
| `MCPInterface` | 0 | 0 | UNUSED |
| `ObservabilityInterface` | 0 | 0 | UNUSED |
| `ReasoningInterface` | 0 | 0 | UNUSED |
| `TaskQueueInterface` | 0 | 0 | UNUSED |
| `WorldModelInterface` | 0 | 0 | UNUSED |
| `close_l9` | 0 | 0 | UNUSED |
| `close_l9_facade` | 0 | 0 | UNUSED |
| `close_l9_sdk` | 0 | 0 | UNUSED |
| `get_l9` | 0 | 0 | UNUSED |
| `get_l9_facade` | 0 | 0 | UNUSED |
| `get_l9_sdk` | 0 | 1 | TEST_ONLY |
| `query_memory` | 0 | 0 | UNUSED |
