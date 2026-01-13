ib-mac@MackBookAirIB L9 %    # Cancel current process with Ctrl+C, then:
   python3 scripts/audit/verify_wiring_alignment.py
zsh: command not found: #
======================================================================
L9 WIRING ALIGNMENT VERIFICATION
======================================================================

Status: ❌ VIOLATIONS FOUND
Files scanned: 670
Paths verified: 126

----------------------------------------------------------------------
BROKEN PATH REFERENCES (1083):
----------------------------------------------------------------------
  ❌ api/routes/memory.py
     Source: gap-analysis-memory.md:26
  ❌ memory/router.py
     Source: gap-analysis-memory.md:26
  ❌ core/governance/cursor_memory_kernel.py
     Source: gap-analysis-memory.md:27
  ❌ memory/router.py
     Source: gap-analysis-memory.md:500
  ❌ memory/router.py
     Source: gap-analysis-memory.md:723
  ❌ memory/router.py
     Source: gap-analysis-memory.md:824
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1008
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1101
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1234
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1381
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1393
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1404
  ❌ memory/router.py
     Source: gap-analysis-memory.md:1421
  ❌ api/test_e2e_slack_audit.py
     Source: workflow_state.md:126
  ❌ memory/test_e2e_memory_audit.py
     Source: workflow_state.md:126
  ❌ api/routes/codegen.py
     Source: TODO.md:109
  ❌ memory/cursor_memory_client.py
     Source: TODO.md:207
  ❌ core/tools/test_tool_graph.py
     Source: VPS-Repo-Files/README.md:78
  ❌ api/test_server_health.py
     Source: VPS-Repo-Files/README.md:84
  ❌ api/adapters/slack_adapter/tests/conftest.py
     Source: VPS-Repo-Files/VPS-DIAGNOSTIC-OUTPUT.md:206
  ... and 1063 more

======================================================================
ib-mac@MackBookAirIB L9 % python3 scripts/audit/run_all.py
2026-01-13 13:57:40 [info     ] ======================================================================
2026-01-13 13:57:40 [info     ] L9 AUDIT MASTER RUNNER v2.0 — Tier 1
2026-01-13 13:57:40 [info     ] ======================================================================
2026-01-13 13:57:40 [info     ] Running 3 audits...           
2026-01-13 13:57:40 [info     ] Starting audit: code_integrity
2026-01-13 13:57:40 [info     ] Starting audit: infrastructure_health
2026-01-13 13:57:40 [info     ] ✓ infrastructure_health: 0 items in 0ms
2026-01-13 13:57:40 [info     ] Starting audit: capability_inventory
2026-01-13 13:57:40 [info     ] ✓ capability_inventory: 0 items in 29ms
2026-01-13 13:57:41 [info     ] Loading analysis results from cache...
2026-01-13 13:57:41 [info     ] Using cached code integrity results
2026-01-13 13:57:41 [info     ] ✓ code_integrity: 36 items in 186ms
2026-01-13 13:57:41 [info     ] Generating JSON report...     
2026-01-13 13:57:41 [info     ] ✓ JSON report: /Users/ib-mac/Projects/l9/reports/audit_run_audit_run_20260113_135740_c693dc26.json
2026-01-13 13:57:41 [info     ] Generating HTML report...     
2026-01-13 13:57:41 [info     ] ✓ HTML report: /Users/ib-mac/Projects/l9/reports/audit_run_audit_run_20260113_135740_c693dc26.html
2026-01-13 13:57:41 [warning  ] ======================================================================
2026-01-13 13:57:41 [warning  ] WIRING INVARIANT VIOLATION: Deprecated paths in audit cache
2026-01-13 13:57:41 [warning  ] ======================================================================
2026-01-13 13:57:41 [warning  ]   DEPRECATED: tools/cursor_client.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ]   DEPRECATED: core/governance/cursor_memory_kernel.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ]   DEPRECATED: memory/extractor/cursor_action_extractor.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ]   DEPRECATED: scripts/cursor_check_mistakes.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ] These files were moved per architecture_decisions.md (2026-01-11)
2026-01-13 13:57:41 [warning  ] Run with --skip-cache to regenerate, or delete .audit_cache/
2026-01-13 13:57:41 [warning  ] ======================================================================
2026-01-13 13:57:41 [info     ]                               
2026-01-13 13:57:41 [info     ] ======================================================================
2026-01-13 13:57:41 [info     ] AUDIT RUN COMPLETE            
2026-01-13 13:57:41 [info     ] ======================================================================
2026-01-13 13:57:41 [info     ] Run ID: audit_run_20260113_135740_c693dc26
2026-01-13 13:57:41 [info     ] Duration: 188ms               
2026-01-13 13:57:41 [info     ] Audits completed: 3           
2026-01-13 13:57:41 [info     ] Items found: 36               
2026-01-13 13:57:41 [info     ] Critical: 0                   
2026-01-13 13:57:41 [info     ] High: 7                       
2026-01-13 13:57:41 [warning  ] Errors: 4                     
2026-01-13 13:57:41 [warning  ]  - DEPRECATED: tools/cursor_client.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ]  - DEPRECATED: core/governance/cursor_memory_kernel.py (moved to agents/cursor/)
2026-01-13 13:57:41 [warning  ]  - DEPRECATED: memory/extractor/cursor_action_extractor.py (moved to agents/cursor/)
2026-01-13 13:57:41 [info     ] ======================================================================
ib-mac@MackBookAirIB L9 % python3 scripts/audit/verify_wiring_alignment.py
