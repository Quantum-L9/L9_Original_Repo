# ADR-0100: Slash Commands Are DAG-Triggered Only — No CLI Executors

## Status

**Accepted** — 2026-02-13

## Context

Slash commands (e.g., `/harvest`, `/wire`, `/readme`) are agent-facing protocols executed by Cursor when the user types a `/command` in chat. The execution flow is:

1. Agent reads `.cursor-commands/commands/{command}.md`
2. Agent parses the YAML frontmatter (`dag:`, `dag_file:`)
3. Agent reads the referenced DAG file (e.g., `workflows/dags/harvest_deploy_dag.py`)
4. Agent walks the DAG nodes, following each node's `action` field

### Problem

During development of the `/harvest` command, a standalone CLI executor (`workflows/harvest_executor.py`, 903 lines) was created as a Python script that could be run directly from the terminal:

```bash
python3 workflows/harvest_executor.py path/to/doc.md
```

This pattern is unnecessary because:

- **Slash commands are never invoked from the CLI.** They are always triggered by a user typing `/command` in Cursor chat, which causes the agent to read and execute the DAG.
- **CLI executors duplicate logic** that already exists in DAG node `action` fields.
- **CLI executors add maintenance burden** — two places to update when the workflow changes.
- **The DAG is the single source of truth** for workflow steps, gates, and sequencing.

## Decision

**Slash commands execute via their DAG only. Do not create CLI executor scripts for slash commands.**

### Rules

1. **Every slash command that has a workflow** MUST reference a DAG via `dag:` and `dag_file:` in its YAML frontmatter.
2. **The DAG file** (`workflows/dags/*.py`) contains all execution instructions in its node `action` fields.
3. **Do NOT create** standalone Python executor scripts (e.g., `workflows/*_executor.py`) for slash commands.
4. **Existing CLI executors** (e.g., `harvest_executor.py`) may remain as legacy but are not the primary execution path and should not be replicated for new commands.

### Execution Flow (Canonical)

```
User types /harvest doc.md
    → Agent reads .cursor-commands/commands/harvest.md
    → Agent sees dag: harvest-deploy-v1, dag_file: workflows/dags/harvest_deploy_dag.py
    → Agent reads workflows/dags/harvest_deploy_dag.py
    → Agent walks nodes: start → parse_plan → verify_sources → extract_files → ...
    → Agent follows each node's action field exactly
```

### What NOT to Do

```
❌ Create workflows/new_command_executor.py with a CLI interface
❌ Add argparse/click wrappers for slash command logic
❌ Duplicate DAG node actions into a standalone script
❌ Reference CLI executors as the primary execution path in command files
```

## Consequences

- **Simpler architecture**: One execution path per slash command (DAG), not two.
- **Less code to maintain**: No parallel CLI scripts that drift from DAG definitions.
- **Clear ownership**: DAG file is the single source of truth for the workflow.
- **Existing executors**: `harvest_executor.py` and similar remain in the repo but are not the canonical path. They may be useful for debugging or standalone use outside Cursor.

## References

- Slash command registry: `.cursor/rules/02-slash-commands.mdc`
- Command files: `.cursor-commands/commands/*.md`
- DAG files: `workflows/dags/*.py`
- Session DAG interface: `workflows/session/interface.py`
