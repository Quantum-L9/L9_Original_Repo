# README slash command trigger

_Exported on 1/31/2026 at 19:10:48 EST from Cursor (2.4.23)_

---

**User**

initiate the readme-pipeline-v1 README Generation Pipeline 11 DAG
update slash command /README so that it triggers the DAG instead of telling you with prose what to do - make it enforceable!

---

**Cursor**

I'll find the readme-pipeline DAG and the README command to make this update.

Now I understand - the `README.md` in commands is actually the general documentation for all commands. I need to create a new `/readme` command that triggers the DAG. Let me check how `/wire` triggers its DAG as a pattern.

I see the pattern. Now I'll create the `/readme` command that triggers the `readme-pipeline-v1` DAG. This will be an enforceable command following the same structure as `/wire`.

Now let me update the commands README to include `/readme` in the quick reference table.

Let me also add `/readme` to the auto-chaining table and add an explanation section.

Let me also add `/readme` to the slash command recognition rule.

Let me verify all the changes were applied correctly.

I see the issue - macOS has a case-insensitive filesystem, so README.md and readme.md are the same file. I need to rename the documentation file first, then create the command file.

Now let me create the proper `/readme` command file.

Now let me fix the commands-index.md to update the self-reference and verify all changes.

Let me verify all files are now correct.

Let me verify the DAG is importable and test the integration.

All done. Here's a summary of what was created:

## Summary

### Created `/readme` Command

**File:** `.cursor-commands/commands/readme.md`

The new `/readme` slash command now triggers the **`readme-pipeline-v1`** DAG with:

- **11 nodes** in the workflow
- **6 phases**: Gap Analysis → Config Enrichment → Template Update → Generate → Validate → Report
- **User gates** for config and template changes
- **Validation loops** that return to fix issues if validation fails
- **Auto-chains** to `/ynp` on completion

### Files Modified

| File                                          | Change                                             |
| --------------------------------------------- | -------------------------------------------------- |
| `.cursor-commands/commands/readme.md`         | Created - DAG-enforced command                     |
| `.cursor-commands/commands/commands-index.md` | Renamed from README.md - added `/readme` to tables |
| `.cursor/rules/02-slash-commands.mdc`         | Added `/readme` to available commands table        |

### DAG Verification

```
ID: readme-pipeline-v1
Name: README Generation Pipeline
Nodes: 11 (start → gap_analysis → gates → enrich_config → update_template → generate → validate → report → end)
```

### Usage

```
/readme                    # Full pipeline (all subsystems)
/readme --tier core        # Only core tier
/readme --subsystem memory # Single subsystem
/readme --validate-only    # Just validate existing
```

---

**User**

@.cursor-commands/commands/readme-dag.md why is this so long if it is just supposed to trigger the DAG which has all the instructions/steps in it!?

---

**Cursor**

You're right - that's redundant. If the DAG contains all the instructions, the command file should just be a minimal trigger. Let me fix this.

You're absolutely right. The DAG at `readme_pipeline_dag.py` already has all the detailed instructions in each node's `action` field. The command file should just be a minimal trigger.

Fixed. Now it's **34 lines** instead of 312.

The command file is just a trigger with:

- YAML frontmatter pointing to the DAG
- Brief usage examples
- Key file references

All the actual instructions live in the DAG's node `action` fields where they belong.
