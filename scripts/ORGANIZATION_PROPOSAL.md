# Scripts Folder Organization Proposal

## ✅ Completed: Memory Scripts Moved

All memory-related scripts have been moved to `scripts/memory/`:

- **Indexing scripts**: `index_*.py` (5 scripts)
- **Cleanup scripts**: `cleanup_*.py`, `delete_*.py`, `generate_delete_sql.py`
- **Inspection scripts**: `check_embeddings_via_api.py`, `inspect_embeddings.py`
- **Graph scripts**: `load_*.py`, `bootstrap_neo4j_schema.py`, `migrate_kernels_to_graph.py`
- **Audit scripts**: `audit_graphs.py`, `audit_graphs_vps.py`
- **Test scripts**: `test_all_graphs_access.py`
- **Shell scripts**: `cleanup_and_reindex.sh`, `run_index_vps.sh`
- **Documentation**: `DELETE_TRASH_INSTRUCTIONS.md`

**Total moved**: 26 files

---

## 📋 Proposed Organization for Remaining Scripts

### Current State (after memory move)

```
scripts/
├── memory/                    # ✅ Memory/graph scripts (26 files)
├── audit/                     # ✅ Audit scripts (existing)
├── reports/                   # ✅ Audit reports (existing)
├── [root level scripts]       # ⚠️  Needs organization
```

### Proposed Structure

```
scripts/
├── memory/                    # ✅ Memory/graph operations
│   ├── indexing/              # Indexing scripts (index_*.py)
│   ├── cleanup/               # Cleanup scripts (cleanup_*, delete_*)
│   ├── graph/                 # Neo4j graph scripts (load_*, bootstrap_*)
│   └── inspection/            # Inspection/test scripts
│
├── audit/                     # ✅ Audit scripts (keep as-is)
│   ├── tier1/
│   └── L9_AUDIT_SUITE_EXPANSION/
│
├── deployment/                 # 🆕 Deployment & VPS operations
│   ├── deploy_agent_executor.sh
│   ├── pull_to_vps.sh
│   ├── rollback_vps.sh
│   ├── vps-mri.sh
│   └── run_index_vps.sh       # (move from memory/)
│
├── development/                # 🆕 Development & testing
│   ├── dev_up.sh
│   ├── test_everything.sh
│   ├── precommit_docker_smoke.sh
│   ├── docker-validator.sh
│   └── check_env.sh
│
├── research/                   # 🆕 Research factory operations
│   ├── delegate_deep_research.py
│   ├── run_single_deep_research.py
│   ├── send_perplexity_spec_request.py
│   ├── extract_perplexity_pack.py
│   ├── factory_extract.py
│   └── test_research_factory.py
│
├── agents/                     # 🆕 Agent operations
│   ├── verify_agent_executor.py
│   ├── neo4j_merge_agent_nodes.py
│   ├── neo4j_unify_relationships.py
│   └── run_bootstrap_l_graph.py
│
├── workspace/                  # 🆕 Workspace initialization
│   ├── init_workspace.py
│   ├── init_workspace_NEW.py
│   └── rename_l_to_l_cto.py
│
├── batch/                      # 🆕 Batch operations
│   └── batch_generate_specs.py
│
└── reports/                    # ✅ Audit reports (keep as-is)
```

---

## 📊 Script Categorization

### Deployment & VPS (5 scripts)
- `deploy_agent_executor.sh` - Deploy agent executor
- `pull_to_vps.sh` - Pull code to VPS
- `rollback_vps.sh` - Rollback VPS deployment
- `vps-mri.sh` - VPS MRI (diagnostics?)
- `run_index_vps.sh` - Run indexing on VPS (currently in memory/)

**Why**: All VPS/deployment related, should be together for easy access during deployments.

---

### Development & Testing (5 scripts)
- `dev_up.sh` - Development environment setup
- `test_everything.sh` - Run all tests
- `precommit_docker_smoke.sh` - Pre-commit smoke tests
- `docker-validator.sh` - Docker validation
- `check_env.sh` - Environment check

**Why**: Development workflow scripts used during local development and CI/CD.

---

### Research Factory (6 scripts)
- `delegate_deep_research.py` - Delegate research tasks
- `run_single_deep_research.py` - Run single research task
- `send_perplexity_spec_request.py` - Send Perplexity requests
- `extract_perplexity_pack.py` - Extract Perplexity results
- `factory_extract.py` - Factory extraction
- `test_research_factory.py` - Test research factory

**Why**: All related to research factory operations, Perplexity integration, and research task orchestration.

---

### Agents (4 scripts)
- `verify_agent_executor.py` - Verify agent executor
- `neo4j_merge_agent_nodes.py` - Merge agent nodes in Neo4j
- `neo4j_unify_relationships.py` - Unify agent relationships
- `run_bootstrap_l_graph.py` - Bootstrap L agent graph

**Why**: Agent-specific operations, graph management for agents, and agent verification.

---

### Workspace (3 scripts)
- `init_workspace.py` - Initialize workspace
- `init_workspace_NEW.py` - New workspace initialization
- `rename_l_to_l_cto.py` - Rename agent

**Why**: Workspace setup and initialization scripts, typically run once or rarely.

---

### Batch Operations (1 script)
- `batch_generate_specs.py` - Batch generate specifications

**Why**: Batch processing script, could grow into a category for batch operations.

---

## 🎯 Benefits of This Organization

1. **Clear Separation of Concerns**
   - Memory operations isolated
   - Deployment scripts grouped
   - Research factory operations together
   - Agent operations centralized

2. **Easier Navigation**
   - Developers know where to find scripts by purpose
   - New scripts have clear home
   - Reduces root-level clutter

3. **Better Maintainability**
   - Related scripts are co-located
   - Easier to find and update related functionality
   - Clear ownership boundaries

4. **Scalability**
   - Easy to add new categories as needed
   - Subfolders can be created within categories if they grow
   - Doesn't require restructuring existing audit/ structure

---

## ⚠️  Considerations

1. **Import Paths**: Some scripts may import from each other or reference paths. These will need to be updated.

2. **Documentation**: Update any docs that reference script paths.

3. **CI/CD**: Update any CI/CD pipelines that reference script paths.

4. **Gradual Migration**: Could move one category at a time to minimize disruption.

---

## 📝 Recommendation

**Start with high-value categories first:**
1. ✅ Memory (already done)
2. **Deployment** (high impact, frequently used)
3. **Research Factory** (cohesive group, clear purpose)
4. **Agents** (small group, easy to move)
5. **Development** (frequently used, good to organize)
6. **Workspace** (rarely used, low priority)

**Alternative: Keep root-level for frequently-used scripts, create subfolders only for larger groups.**

