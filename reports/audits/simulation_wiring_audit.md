# Package Wiring Audit: simulation

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `simulation`

Files checked: 3
- WIRED: 1
- PARTIAL: 2
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `simulation/outcome_evaluator.py` | 0 | 0 | - | Y | PARTIAL |
| `simulation/scenario_loader.py` | 0 | 0 | - | Y | PARTIAL |
| `simulation/simulation_engine.py` | 3 | 1 | Y | Y | OK |

## Level C: API Instantiation — `simulation`

API Status: **HAS_API**
Symbols checked: 10
- USED: 6
- TEST_ONLY: 0
- UNUSED: 4

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `OutcomeEvaluator` | 0 | 0 | UNUSED |
| `ScenarioLoader` | 0 | 0 | UNUSED |
| `ScenarioType` | 0 | 0 | UNUSED |
| `SimulationMetrics` | 0 | 0 | UNUSED |
