from __future__ import annotations

from .ast_scanner import scan_directories
from .config import SuperpackLayout
from .filesystem import open_report, write_markdown_footer, write_markdown_header


def generate_memory_superpack(layout: SuperpackLayout) -> None:
    """Generate core_memory_superpack.md from AST scan of memory modules."""
    output = layout.reports_dir / "core_memory_superpack.md"
    modules = scan_directories(layout.memory_dirs, layout.root)

    with open_report(output) as f:
        write_markdown_header(
            f,
            "CORE KERNELS & MEMORY SUPERPACK",
            "T3 (High-Impact)",
            "Map kernel runtime contracts, memory pipeline, substrate protocols, and type system.",
        )

        # Bootstrap Sequence
        f.write("## Kernel Runtime Architecture\n\n")
        f.write("```\n")
        f.write("7-Phase Bootstrap (immutable sequence):\n")
        f.write("Phase 1: Load config & credentials\n")
        f.write("Phase 2: Initialize memory substrates (PostgreSQL + Redis + Neo4j)\n")
        f.write("Phase 3: Wire kernel runtime (ExecutorComposer)\n")
        f.write("Phase 4: Load governance engine\n")
        f.write("Phase 5: Load dynamic tools registry\n")
        f.write("Phase 6: Bind orchestrators (session + background)\n")
        f.write("Phase 7: Start listener (HTTP/WebSocket)\n")
        f.write("```\n\n")

        # Memory Pipeline
        f.write("## Memory Pipeline (Canonical Path)\n\n")
        f.write("```\n")
        f.write("Entry: Orchestrator → PacketEnvelope\n")
        f.write("  ↓\n")
        f.write("write_packet() ← CANONICAL PATH (all writes must go here)\n")
        f.write("  ├─ ingest_packet() [LLM context, metadata extraction]\n")
        f.write("  ├─ emit_packet() [dag node creation]\n")
        f.write("  └─ Substrate adapters (PostgreSQL, Redis, Neo4j)\n")
        f.write("  ↓\n")
        f.write("Exit: DAG node stored, memory service notified\n")
        f.write("```\n\n")

        # Scanned Modules
        f.write("## Memory Modules (AST Scanned)\n\n")
        f.write("| Module | Classes | Functions | Async | LOC |\n")
        f.write("|--------|---------|-----------|-------|-----|\n")

        total_loc = 0
        async_modules = 0

        for mod in sorted(modules, key=lambda m: m.module_name):
            cls_count = len(mod.classes)
            func_count = len(mod.functions)
            total_loc += mod.loc
            async_flag = "✓" if mod.is_async else ""
            if mod.is_async:
                async_modules += 1
            f.write(
                f"| `{mod.module_name}` | {cls_count} | {func_count} | {async_flag} | {mod.loc} |\n"
            )

        f.write(
            f"\n**Total:** {len(modules)} modules, {total_loc} LOC, {async_modules} async\n\n"
        )

        # Pydantic Models
        f.write("## Pydantic Models (BaseModel subclasses)\n\n")
        pydantic_found = False
        for mod in modules:
            for cls in mod.classes:
                if cls.is_pydantic:
                    pydantic_found = True
                    f.write(f"- `{mod.module_name}.{cls.name}`\n")
        if not pydantic_found:
            f.write("_No Pydantic models found in scanned directories._\n")
        f.write("\n")

        # Key Services
        f.write("## Key Services\n\n")
        for mod in modules:
            for cls in mod.classes:
                if (
                    "Service" in cls.name
                    or "Repository" in cls.name
                    or "Adapter" in cls.name
                ):
                    f.write(f"- `{mod.module_name}.{cls.name}`\n")
                    for method in cls.methods[:3]:
                        f.write(f"  - `{method}()`\n")
        f.write("\n")

        # Change Checklist
        f.write("## Change Checklist\n\n")
        f.write("Before modifying memory modules:\n\n")
        f.write("1. [ ] Verify all writes go through `write_packet()`\n")
        f.write("2. [ ] Test with all substrate adapters\n")
        f.write("3. [ ] Update memory integration tests\n")
        f.write("4. [ ] Verify 7-phase bootstrap sequence unchanged\n")

        write_markdown_footer(f)


def generate_memory_integration_map(layout: SuperpackLayout) -> None:
    """Generate memory_integration_map.txt from module imports."""
    output = layout.architecture_dir / "memory_integration_map.txt"
    modules = scan_directories(layout.memory_dirs, layout.root)

    with open_report(output) as f:
        f.write("# L9 MEMORY INTEGRATION MAP\n")
        f.write("# Auto-generated from AST scan\n\n")

        f.write("## Module Dependencies\n\n")

        for mod in sorted(modules, key=lambda m: m.module_name):
            # Filter to internal imports only
            internal_imports = [
                imp
                for imp in mod.imports
                if imp.startswith(("memory", "core", "world_model", "orchestrat"))
            ]
            if internal_imports:
                f.write(f"{mod.module_name}\n")
                for imp in sorted(set(internal_imports)):
                    f.write(f"  ← {imp}\n")
                f.write("\n")

        f.write("---\n")
        f.write("Auto-generated by tools/superpack_reports/\n")
