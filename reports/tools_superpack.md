# TOOLS & REPORTS SUPERPACK

**Risk Tier:** T1 (Read-Only) | **Auto-Generated**

---

## Purpose

Catalog utility tools, automation scripts, and reporting infrastructure.

---

## Tool Modules (AST Scanned)

| Module                                                  | Classes | Functions | LOC       |
| ------------------------------------------------------- | ------- | --------- | --------- |
| `scripts.__init__`                                      | 0       | 0         | 1         |
| `scripts.agents.neo4j_merge_agent_nodes`                | 0       | 7         | 441       |
| `scripts.agents.neo4j_unify_relationships`              | 0       | 8         | 430       |
| `scripts.agents.run_bootstrap_l_graph`                  | 0       | 1         | 158       |
| `scripts.agents.verify_agent_executor`                  | 0       | 7         | 313       |
| `scripts.audit.audit_api_signatures`                    | 4       | 7         | 562       |
| `scripts.audit.audit_shared_core`                       | 10      | 1         | 564       |
| `scripts.audit.categorize_dead_code`                    | 4       | 4         | 635       |
| `scripts.audit.cleanup_audit_reports`                   | 0       | 10        | 374       |
| `scripts.audit.ensure_logger_instantiated`              | 1       | 7         | 564       |
| `scripts.audit.find_dead_code`                          | 4       | 27        | 2280      |
| `scripts.audit.generate_gmp_todos`                      | 2       | 6         | 658       |
| `scripts.audit.inject_dora_complete`                    | 5       | 1         | 2261      |
| `scripts.audit.inject_dora_multiformat_complete`        | 4       | 1         | 929       |
| `scripts.audit.migrate_dora_legacy`                     | 2       | 1         | 512       |
| `scripts.audit.resolve_dead_code_refs`                  | 3       | 2         | 683       |
| `scripts.audit.run_all`                                 | 4       | 2         | 1161      |
| `scripts.audit.run_dead_code_audit`                     | 0       | 2         | 275       |
| `scripts.audit.tier1.audit_capability_inventory`        | 7       | 7         | 697       |
| `scripts.audit.tier1.audit_code_integrity`              | 9       | 7         | 1102      |
| `scripts.audit.tier1.audit_infrastructure_health`       | 10      | 6         | 755       |
| `scripts.audit.validate_dora_complete`                  | 2       | 1         | 536       |
| `scripts.audit.verify_memory_spec_v3`                   | 0       | 11        | 541       |
| `scripts.audit.verify_wiring_alignment`                 | 2       | 7         | 446       |
| `scripts.batch.batch_generate_specs`                    | 4       | 2         | 521       |
| `scripts.benchmark_caching_and_vector`                  | 1       | 4         | 251       |
| `scripts.benchmark_performance`                         | 0       | 3         | 126       |
| `scripts.benchmark_standalone`                          | 0       | 0         | 180       |
| `scripts.check_n_plus_1`                                | 1       | 6         | 352       |
| `scripts.diagnose_memory_search`                        | 0       | 2         | 201       |
| `scripts.extract_code_facts`                            | 1       | 3         | 490       |
| `scripts.fix_async_decorators`                          | 0       | 5         | 323       |
| `scripts.fix_untyped_decorators`                        | 2       | 13        | 622       |
| `scripts.generate_gmp_report`                           | 6       | 7         | 711       |
| `scripts.generate_readme_superprompt`                   | 6       | 10        | 867       |
| `scripts.generate_subsystem_readmes`                    | 3       | 10        | 1158      |
| `scripts.gmp-validate-stage`                            | 2       | 1         | 385       |
| `scripts.memory.__init__`                               | 0       | 0         | 1         |
| `scripts.memory.audit_graphs`                           | 0       | 6         | 623       |
| `scripts.memory.audit_graphs_vps`                       | 0       | 8         | 513       |
| `scripts.memory.bootstrap_neo4j_schema`                 | 0       | 8         | 661       |
| `scripts.memory.check_embeddings_via_api`               | 0       | 1         | 185       |
| `scripts.memory.cleanup_trash_embeddings`               | 0       | 3         | 338       |
| `scripts.memory.cleanup_trash_embeddings_via_api`       | 0       | 3         | 261       |
| `scripts.memory.delete_trash_embeddings`                | 0       | 2         | 264       |
| `scripts.memory.delete_trash_via_service`               | 0       | 2         | 196       |
| `scripts.memory.execute_cleanup_and_reindex`            | 0       | 3         | 261       |
| `scripts.memory.generate_delete_sql`                    | 0       | 3         | 213       |
| `scripts.memory.index_architecture`                     | 0       | 6         | 495       |
| `scripts.memory.index_error_patterns`                   | 0       | 4         | 389       |
| `scripts.memory.index_gmp_reports`                      | 0       | 3         | 404       |
| `scripts.memory.index_preferences`                      | 0       | 3         | 425       |
| `scripts.memory.index_tool_usage`                       | 0       | 5         | 350       |
| `scripts.memory.inspect_embeddings`                     | 0       | 2         | 339       |
| `scripts.memory.load_gmp_reports_to_graph`              | 0       | 5         | 431       |
| `scripts.memory.load_indexes_to_neo4j`                  | 1       | 1         | 646       |
| `scripts.memory.load_indexes_to_neo4j_vps`              | 1       | 1         | 707       |
| `scripts.memory.migrate_kernels_to_graph`               | 0       | 3         | 299       |
| `scripts.memory.seed_golden_strategies`                 | 0       | 6         | 465       |
| `scripts.memory.test_all_graphs_access`                 | 0       | 1         | 373       |
| `scripts.migrate_substrate_models`                      | 0       | 6         | 321       |
| `scripts.pr_review.gemini_auto_editor`                  | 1       | 0         | 195       |
| `scripts.pr_review.perplexity_reviewer`                 | 1       | 0         | 215       |
| `scripts.refactoring.__init__`                          | 0       | 0         | 16        |
| `scripts.refactoring.aios_validate`                     | 1       | 3         | 172       |
| `scripts.refactoring.bootstrap_refactor`                | 3       | 1         | 722       |
| `scripts.research.delegate_deep_research`               | 0       | 5         | 357       |
| `scripts.research.extract_perplexity_pack`              | 0       | 3         | 242       |
| `scripts.research.factory_extract`                      | 0       | 3         | 318       |
| `scripts.research.run_single_deep_research`             | 0       | 1         | 195       |
| `scripts.research.send_perplexity_spec_request`         | 0       | 3         | 255       |
| `scripts.research.test_research_factory`                | 0       | 2         | 94        |
| `scripts.run_pattern`                                   | 0       | 5         | 348       |
| `scripts.setup_gmail_accounts`                          | 0       | 2         | 244       |
| `scripts.validate_gmp_report`                           | 3       | 3         | 801       |
| `scripts.workflow.generate_gmp_report`                  | 0       | 4         | 316       |
| `scripts.workflow.update_workflow_state`                | 0       | 12        | 291       |
| `scripts.workspace.init_workspace`                      | 1       | 3         | 352       |
| `scripts.workspace.init_workspace_NEW`                  | 0       | 6         | 496       |
| `scripts.workspace.rename_l_to_l_cto`                   | 0       | 4         | 314       |
| `tools.__init__`                                        | 0       | 0         | 4         |
| `tools.adr.__init__`                                    | 0       | 0         | 15        |
| `tools.adr.adr_cli`                                     | 0       | 12        | 390       |
| `tools.adr.adr_compliance_check_enhanced`               | 2       | 1         | 360       |
| `tools.adr.adr_enforcer`                                | 3       | 1         | 643       |
| `tools.adr.adr_generator`                               | 0       | 3         | 159       |
| `tools.adr.adr_indexer`                                 | 0       | 4         | 206       |
| `tools.adr.adr_scanner`                                 | 0       | 1         | 47        |
| `tools.adr.adr_validator`                               | 0       | 3         | 197       |
| `tools.architecture_reports.__init__`                   | 0       | 0         | 3         |
| `tools.architecture_reports.architecture_report`        | 0       | 1         | 38        |
| `tools.architecture_reports.async_function_map_report`  | 1       | 2         | 63        |
| `tools.architecture_reports.class_definitions_report`   | 0       | 3         | 55        |
| `tools.architecture_reports.config`                     | 1       | 3         | 68        |
| `tools.architecture_reports.config_files_report`        | 0       | 1         | 35        |
| `tools.architecture_reports.file_metrics_report`        | 1       | 3         | 60        |
| `tools.architecture_reports.filesystem`                 | 0       | 2         | 14        |
| `tools.architecture_reports.function_signatures_report` | 0       | 3         | 77        |
| `tools.architecture_reports.imports_report`             | 0       | 2         | 47        |
| `tools.architecture_reports.inheritance_graph_report`   | 0       | 3         | 50        |
| `tools.architecture_reports.main`                       | 0       | 2         | 85        |
| `tools.architecture_reports.pydantic_models_report`     | 0       | 3         | 50        |
| `tools.architecture_reports.route_handlers_report`      | 0       | 1         | 55        |
| `tools.export_repo_indexes`                             | 0       | 37        | 2229      |
| `tools.l9_cli`                                          | 0       | 4         | 195       |
| `tools.mac_protocol`                                    | 2       | 2         | 148       |
| `tools.superpack_reports.__init__`                      | 0       | 0         | 3         |
| `tools.superpack_reports.api_report`                    | 0       | 2         | 84        |
| `tools.superpack_reports.ast_scanner`                   | 3       | 4         | 169       |
| `tools.superpack_reports.config`                        | 1       | 3         | 131       |
| `tools.superpack_reports.filesystem`                    | 0       | 4         | 30        |
| `tools.superpack_reports.governance_report`             | 0       | 2         | 106       |
| `tools.superpack_reports.index_report`                  | 0       | 1         | 69        |
| `tools.superpack_reports.main`                          | 0       | 2         | 85        |
| `tools.superpack_reports.memory_report`                 | 0       | 2         | 123       |
| `tools.superpack_reports.tools_report`                  | 0       | 2         | 82        |
| `tools.superpack_reports.workers_report`                | 0       | 2         | 101       |
| **TOTAL**                                               |         |           | **44444** |

## CLI Entry Points

- `tools.export_repo_indexes.main()`
- `tools.l9_cli.cli()`
- `tools.adr.adr_enforcer.main()`
- `tools.adr.adr_compliance_check_enhanced.main()`
- `tools.adr.adr_cli.main()`
- `tools.adr.adr_scanner.main()`
- `tools.architecture_reports.main.main()`
- `tools.superpack_reports.main.main()`
- `scripts.generate_gmp_report.main()`
- `scripts.fix_async_decorators.main()`
- `scripts.check_n_plus_1.main()`
- `scripts.diagnose_memory_search.main()`
- `scripts.benchmark_performance.main()`
- `scripts.run_pattern.main()`
- `scripts.setup_gmail_accounts.main()`
- `scripts.fix_untyped_decorators.main()`
- `scripts.gmp-validate-stage.main()`
- `scripts.benchmark_caching_and_vector.main()`
- `scripts.validate_gmp_report.main()`
- `scripts.generate_readme_superprompt.main()`
- `scripts.generate_subsystem_readmes.main()`
- `scripts.extract_code_facts.main()`
- `scripts.migrate_substrate_models.main()`
- `scripts.research.delegate_deep_research.main()`
- `scripts.research.factory_extract.main()`
- `scripts.research.send_perplexity_spec_request.main()`
- `scripts.research.extract_perplexity_pack.main()`
- `scripts.research.test_research_factory.main()`
- `scripts.memory.execute_cleanup_and_reindex.main()`
- `scripts.memory.audit_graphs_vps.main()`
- `scripts.memory.index_tool_usage.main()`
- `scripts.memory.audit_graphs.main()`
- `scripts.memory.load_indexes_to_neo4j.main()`
- `scripts.memory.load_indexes_to_neo4j_vps.main()`
- `scripts.memory.seed_golden_strategies.main()`
- `scripts.memory.delete_trash_embeddings.main()`
- `scripts.memory.index_preferences.main()`
- `scripts.memory.migrate_kernels_to_graph.main()`
- `scripts.memory.bootstrap_neo4j_schema.main()`
- `scripts.memory.index_gmp_reports.main()`
- `scripts.memory.inspect_embeddings.main()`
- `scripts.memory.index_architecture.main()`
- `scripts.memory.delete_trash_via_service.main()`
- `scripts.memory.cleanup_trash_embeddings.main()`
- `scripts.memory.cleanup_trash_embeddings_via_api.main()`
- `scripts.memory.generate_delete_sql.main()`
- `scripts.memory.index_error_patterns.main()`
- `scripts.memory.load_gmp_reports_to_graph.main()`
- `scripts.workspace.init_workspace_NEW.main()`
- `scripts.workspace.init_workspace.main()`
- `scripts.workspace.rename_l_to_l_cto.main()`
- `scripts.agents.verify_agent_executor.main()`
- `scripts.agents.neo4j_merge_agent_nodes.main()`
- `scripts.agents.run_bootstrap_l_graph.main()`
- `scripts.agents.neo4j_unify_relationships.main()`
- `scripts.audit.run_dead_code_audit.main()`
- `scripts.audit.verify_memory_spec_v3.main()`
- `scripts.audit.migrate_dora_legacy.main()`
- `scripts.audit.validate_dora_complete.main()`
- `scripts.audit.inject_dora_complete.main()`
- `scripts.audit.verify_wiring_alignment.main()`
- `scripts.audit.inject_dora_multiformat_complete.main()`
- `scripts.audit.resolve_dead_code_refs.main()`
- `scripts.audit.audit_api_signatures.main()`
- `scripts.audit.run_all.main()`
- `scripts.audit.ensure_logger_instantiated.main()`
- `scripts.audit.categorize_dead_code.main()`
- `scripts.audit.generate_gmp_todos.main()`
- `scripts.audit.find_dead_code.main()`
- `scripts.audit.cleanup_audit_reports.main()`
- `scripts.batch.batch_generate_specs.main()`
- `scripts.workflow.generate_gmp_report.main()`
- `scripts.workflow.update_workflow_state.main()`
- `scripts.refactoring.bootstrap_refactor.main()`
- `scripts.refactoring.aios_validate.main()`
- `scripts.audit.tier1.audit_capability_inventory.main()`
- `scripts.audit.tier1.audit_infrastructure_health.main()`
- `scripts.audit.tier1.audit_code_integrity.main()`

## Automation Hooks

```
Pre-commit: ruff, mypy, gitleaks (.pre-commit-config.yaml)
Makefile: lint, format, test, architecture-reports, superpacks
```

## Report Generation

```bash
make architecture-reports  # Generate architecture/*.txt
make superpacks            # Generate superpack docs
```

---

_Auto-generated by `tools/superpack_reports/` | Regenerate: `make superpacks`_
