# Component Wiring Audit Guide

**Purpose:** Systematically audit each component (package) in the L9 repo so that:
- All public symbols are **re-exported** from the package’s `__init__.py` and `__all__`.
- All files in the component are **wired** (importable, have consumers or are entrypoints).
- Public APIs are **fully instantiated** (used somewhere, not dead code).

**Context:** The repo was built piece-by-piece without a strict export roadmap, so import/export consistency varies. This guide and the audit script make the same checks we did for `memory` repeatable for any package.

---

## 1. Definitions

| Term | Meaning |
|------|--------|
| **Component** | A Python package (directory with `__init__.py`) that exposes a public API, e.g. `memory`, `core`, `runtime`, `api`, `orchestration`. |
| **Properly wired (package)** | Every symbol in `__all__` is imported in `__init__.py`; every symbol imported in `__init__.py` from that package’s submodules is in `__all__` (or explicitly documented as “import directly when needed”). |
| **Properly wired (file)** | The file imports resolve, try-run passes (or import-only passes), and at least one consumer exists (or it’s a CLI/entrypoint). |
| **Fully instantiated** | Public classes/functions are used somewhere (tests, other modules, or app entrypoints); no orphan public API. |

---

## 2. Audit levels

### Level A: Package export consistency (like `memory_export_audit.md`)

For **one component** (e.g. `memory`, `core`, `runtime`):

1. **List `__all__`** in that package’s `__init__.py`.
2. **List every name** bound by imports in that `__init__.py` (from submodules and from other packages).
3. **Compare:**
   - **Gap 1:** Names in `__all__` but not imported → broken re-export (fix imports or remove from `__all__`).
   - **Gap 2:** Names imported from the package’s own submodules but not in `__all__` → inconsistent API (add to `__all__`).
4. **Document** “import directly when needed” (e.g. to avoid circular deps) so they are not treated as missing from `__all__`.

**Output:** A table per submodule: “Imported names / All in __all__? / Consumers (wired?)”.  
**Automation:**
```bash
python tools/validation/audit_package_exports.py memory
python tools/validation/audit_package_exports.py core runtime api --quiet   # summary only
python tools/validation/audit_package_exports.py memory --report reports/memory_export_audit.md
```
Makefile: `make audit-exports PACKAGE=memory` (optional target).

### Level B: File-level wiring (per file in the component)

For **each `.py` file** in the component (excluding `__init__.py` if you already did Level A):

1. **Resolve imports** — `python3 -c "from <package>.<module> import <main_symbol>"` or equivalent.
2. **Try-run** — `make try-run FILE=<path> MODE=--import-only` (or full run for scripts).
3. **Exports** — If the file is a submodule, check its public names are re-exported by the parent `__init__.py` (already covered in Level A for the top-level package).
4. **Consumers** — `rg "from.*<module>|import.*<module>" --type py -l` (exclude the file itself and its tests).
5. **Tests** — At least one test file that imports or exercises the module; run it.

**Output:** PASS/FAIL per file; list of orphans (no consumers, not entrypoint).  
**Automation:** Use `/confirm-wiring` (or the confirm-wiring DAG) per file; optionally a batch script that loops over files and runs the DAG steps.

### Level C: Instantiation check (optional, for public API)

For **each public class or `get_*` / `create_*` function** in the component:

1. **Consumers** — `rg "<ClassName>|<func_name>" --type py -l` (exclude definition and tests if you only want “used in production code”).
2. **Singleton/entrypoint** — If it’s a singleton or created at startup, confirm it’s registered or called from a known entry (e.g. `api/server.py`, `core/di/bootstrap_integration.py`).

**Output:** List of public symbols with zero consumers (candidates for removal or documentation as “reserved API”).  
**Automation:** Script that parses `__all__` and key classes from each module and runs grep for each.

---

## 3. Recommended order of operations

1. **List components to audit**  
   Top-level packages that define a public API: e.g. `memory`, `core`, `runtime`, `api`, `orchestration`, `orchestrators`, `workflows`, `agents`, `services`, `config`, `clients`, `world_model`, `motifs`, `telemetry`, `mcp_memory` (if treated as a component).

2. **Run Level A (export consistency) for each**  
   Use `tools/validation/audit_package_exports.py <package>`. Fix:
   - Add missing names to `__all__` (like we did for `memory` deduplication and vector_search_config).
   - Fix or remove broken `__all__` entries that aren’t imported.

3. **Run Level B (file wiring) for critical components first**  
   Start with KERNEL_TIER / RUNTIME_TIER (e.g. `core`, `memory`, `runtime`). For each important file, run `/confirm-wiring <file or module>`. Fix import/try-run/consumer/test gaps.

4. **Run Level C where it matters**  
   For components with many public symbols (e.g. `core`, `memory`), run an instantiation check so you can flag or document unused public API.

5. **Record results**  
   Save one report per component under `reports/`, e.g. `reports/<package>_export_audit.md`, and optionally a single index: `reports/COMPONENT_AUDIT_INDEX.md` with links and status (Not started / In progress / Done).

---

## 4. Per-component checklist (copy-paste template)

```markdown
## Component: <package>

- [ ] Level A: Export audit run (`audit_package_exports.py <package>`)
- [ ] Level A: All imported-from-submodule names in __all__ (or documented as direct import)
- [ ] Level A: All __all__ names have a corresponding import
- [ ] Level B: Confirm-wiring run for each non-__init__.py file (or sampled critical files)
- [ ] Level B: No orphan files (every file has consumer or is entrypoint)
- [ ] Level C (optional): Public API instantiation check
- [ ] Report saved: reports/<package>_export_audit.md
```

---

## 5. References

- **Existing audit:** `reports/memory_export_audit.md` — template for Level A.
- **File-level wiring:** `workflows/dags/confirm_wiring_dag.py` and `/confirm-wiring` command.
- **Try-run:** `make try-run FILE=path MODE=--import-only`; `tools/validation/try_run.py`.
- **Module tier mapping:** `.cursor/rules/86-module-tier-mapping.mdc` (prioritize KERNEL_TIER / RUNTIME_TIER).
