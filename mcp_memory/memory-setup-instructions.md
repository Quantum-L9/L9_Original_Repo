memory-governance-spec:
  version: 2.0
  description: >
    UNIFIED L9 Memory Substrate. L and Cursor share the SAME tables
    (packet_store, memory_embeddings) with scope-based access control.
    NO separate memory.* tables - single source of truth.

  # =============================================================================
  # ARCHITECTURE: Unified Memory with "developer" Scope
  # =============================================================================
  #
  # L9 MEMORY SUBSTRATE (Single Source)
  # ├── SCOPE: "developer"    ← Shared: L + Cursor (code-related collaboration)
  # │   • Code patterns & preferences
  # │   • GMP learnings
  # │   • Error fixes & solutions
  # │   • Architecture decisions
  # │   • Igor's coding preferences
  # │   • Session context for code work
  # │
  # ├── SCOPE: "l-private"    ← L only (not visible to Cursor)
  # │   • Reasoning traces
  # │   • World model entities/updates
  # │   • Approval decisions
  # │   • Internal agent operations
  # │   • Slack conversations
  # │
  # └── SCOPE: "global"       ← System-wide facts (Cursor: READ, L: READ/WRITE)
  #     • Kernel knowledge
  #     • Infrastructure facts (VPS IP, ports, etc.)
  #     • Tool registry state
  #     • Governance rules
  #
  # =============================================================================
  # MULTI-PROJECT ARCHITECTURE (LOCKED)
  # =============================================================================
  #
  # SCOPES:
  #   developer: Code collaboration (Cursor + L can both access)
  #   l-private: L's internal operations (Cursor BLOCKED)
  #
  # GLOBAL ACCESS = Cursor can read/write scope='developer' ACROSS ALL PROJECTS
  #                 (L9 is just one project, there will be others)
  #
  # ┌─────────────────────────────────────────────────────────────────────────┐
  # │                        UNIFIED MEMORY SUBSTRATE                         │
  # ├─────────────────────────────────────────────────────────────────────────┤
  # │                                                                         │
  # │   PROJECT: l9              PROJECT: future-x         PROJECT: future-y │
  # │   ┌─────────────────┐      ┌─────────────────┐       ┌─────────────────┐│
  # │   │ developer ✅    │      │ developer ✅    │       │ developer ✅    ││
  # │   │ (L + Cursor)    │      │ (L + Cursor)    │       │ (L + Cursor)    ││
  # │   ├─────────────────┤      ├─────────────────┤       ├─────────────────┤│
  # │   │ l-private ❌    │      │ l-private ❌    │       │ l-private ❌    ││
  # │   │ (L only)        │      │ (L only)        │       │ (L only)        ││
  # │   └─────────────────┘      └─────────────────┘       └─────────────────┘│
  # │                                                                         │
  # │   CURSOR GLOBAL ACCESS = scope='developer' across ALL projects          │
  # │   CURSOR QUERY FILTER: WHERE scope = 'developer'                        │
  # │                                                                         │
  # └─────────────────────────────────────────────────────────────────────────┘
  #
  # ACCESS MATRIX:
  # ┌─────────────┬────────────────────────────────┬─────────────────────────┐
  # │             │  developer (all projects)      │  l-private              │
  # ├─────────────┼────────────────────────────────┼─────────────────────────┤
  # │ Cursor (C)  │  READ/WRITE (global access)    │       BLOCKED           │
  # │ L-CTO       │  READ/WRITE                    │       READ/WRITE        │
  # └─────────────┴────────────────────────────────┴─────────────────────────┘

  substrate:
    db: l9memory
    schema: public  # Use L9 core tables, NOT separate memory.* schema
    tables:
      packets: packet_store           # Central event log (L9 core)
      embeddings: memory_embeddings   # Vector store (L9 core)
      facts: knowledge_facts          # Extracted facts (L9 core)
      reflections: reflection_store   # Lessons learned (L9 core)
    # DEPRECATED: memory.shortterm, memory.mediumterm, memory.longterm
    # These will be deleted - use packet_store with scope="developer" instead
    key_columns:
      project_id: project_id  # 'l9' | 'project-x' | etc. (NULL for global)
      scope: scope            # 'developer' | 'l-private' | 'global'
      metadata: metadata      # JSONB, holds creator/source/etc.
      timestamps:
        created_at: timestamp
        last_accessed: last_accessed
    multi_project_notes: |
      - project_id = NULL or empty for scope='global' (cross-project)
      - project_id = 'l9' for L9-specific developer/l-private
      - When querying, Cursor filters: scope IN ('developer', 'global')

  actors:
    L:
      id: L-CTO
      description: Primary system agent (L-CTO kernel).
      mcp_api_key_env: MCP_API_KEY_L
      scope_access:
        developer: READ/WRITE   # Collaboration with Cursor
        l-private: READ/WRITE   # L's private operations
        global: READ/WRITE      # System facts
      capabilities:
        read:   all_scopes
        write:  all_scopes
        delete: all_scopes
    C:
      id: Cursor-IDE
      description: Cursor IDE MCP client (code development assistant).
      mcp_api_key_env: MCP_API_KEY_C
      scope_access:
        developer: READ/WRITE   # Project-specific code collaboration
        l-private: BLOCKED      # Cannot see L's internals
        global: READ/WRITE      # Cross-project developer knowledge
      capabilities:
        read:   developer + global
        write:  developer + global
        delete: developer + global (own memories only)
      enforcement: "WHERE scope IN ('developer', 'global')" # Hard filter on ALL queries

  scope_strategy:
    description: >
      MULTI-PROJECT memory with scope-based visibility. Each project (l9, etc.)
      has developer + l-private scopes. "global" spans all projects for shared
      developer knowledge.
    
    key_principle: >
      CURSOR = "developer" + "global" SCOPES ONLY.
      - developer: Project-specific code collaboration
      - global: Cross-project developer knowledge (shared learnings)
      - l-private: L's internal ops (Cursor BLOCKED)
    
    projects:
      description: Each repo/project is a separate namespace
      current: ["l9"]
      future: ["project-x", "project-y", "..."]
      structure: |
        project_id + scope determines visibility:
        - l9:developer → L9 code work (Cursor ✅)
        - l9:l-private → L9 internal ops (Cursor ❌)
        - global → cross-project developer knowledge (Cursor ✅)
    
    scopes:
      developer:
        description: Code development collaboration within ONE project
        project_scoped: true  # Each project has its own developer scope
        l_access: READ/WRITE
        cursor_access: READ/WRITE
        visibility: Both L and Cursor see memories in this project's developer scope
        content: |
          - Code patterns & preferences for this project
          - GMP learnings and outcomes
          - Error fixes & solutions
          - Architecture decisions
          - Igor's coding preferences
          - Session context for code work
      l-private:
        description: L's internal operations for ONE project (invisible to Cursor)
        project_scoped: true  # Each project has its own l-private scope
        l_access: READ/WRITE
        cursor_access: BLOCKED (cannot read OR write)
        visibility: Only L sees memories in this scope
        content: |
          - Reasoning traces
          - World model entities/updates
          - Approval decisions
          - Internal agent operations
          - Slack conversations
      global:
        description: Shared developer knowledge ACROSS all projects
        project_scoped: false  # Spans all projects
        l_access: READ/WRITE
        cursor_access: READ/WRITE
        visibility: Both L and Cursor see cross-project developer knowledge
        content: |
          - Patterns that apply to multiple projects
          - Reusable solutions
          - Cross-project learnings
          - General coding preferences (not project-specific)

  metadata_contract:
    fields:
      creator:
        type: string
        required: true
        allowed_values: ["L-CTO", "Cursor-IDE"]
        semantics:
          "L-CTO": memory was created or last written by the L-CTO kernel
          "Cursor-IDE": memory was created or last written by the Cursor IDE client
      source:
        type: string
        required: true
        examples:
          L: "l9-kernel"
          C: "cursor-ide"
      agent:
        type: string
        required: false
        example: "l-cto"
      tool_name:
        type: string
        required: false
      notes:
        type: object
        required: false
        description: Arbitrary JSON with extra provenance data.

    write-policies:
      L:
        on_save:
          set:
            metadata.creator: "L-CTO"
            metadata.source: "l9-kernel"
            metadata.agent: "l-cto"
        on_update:
          allowed: true   # may update any memory for the shared userid
      C:
        on_save:
          set:
            metadata.creator: "Cursor-IDE"
            metadata.source: "cursor-ide"
        on_update:
          allowed: true
          constraints:
            - "UPDATE/DELETE queries MUST restrict by id AND metadata.creator = 'Cursor-IDE'"
            - "If no row matches (because creator != 'Cursor-IDE'), return authorization error and do not modify anything."

  mcp_server_rules:
    identify_caller:
      method: api_key
      mapping:
        env.MCP_API_KEY_L: "L"
        env.MCP_API_KEY_C: "C"
    tools:
      saveMemory:
        behavior:
          L:
            allowed: true
            notes: "Full insert; may write any kind/kind/scope for shared userid."
          C:
            allowed: true
            notes: "Insert only; creator locked to Cursor-IDE; cannot choose creator/source."
      searchMemory:
        behavior:
          L:
            allowed: true
            filter: "userid = shared_userid"
          C:
            allowed: true
            filter: "userid = shared_userid"
      getMemoryStats:
        behavior:
          L: { allowed: true }
          C: { allowed: true }
      deleteExpiredMemories:
        behavior:
          L: { allowed: true }
          C:
            allowed: false
            notes: "Cursor may not run global cleanup."

    update_tool (if implemented):
      L:
        allowed: true
        where_clause: "WHERE id = $1 AND userid = $2"
      C:
        allowed: true
        where_clause: "WHERE id = $1 AND userid = $2 AND metadata->>'creator' = 'Cursor-IDE'"
        failure_mode: "If 0 rows updated, return 403/authorization error."

  audit_log_policy:
    table: memory.auditlog
    required_on:
      - saveMemory
      - searchMemory
      - getMemoryStats
      - deleteExpiredMemories
      - any_future_update_or_delete
    fields:
      operation: INSERT | UPDATE | DELETE | SEARCH
      tablename: memory.shortterm | memory.mediumterm | memory.longterm
      memoryid: nullable BIGINT
      userid: TEXT
      status: success | error
      details:
        type: JSONB
        must_include:
          - creator
          - source
          - caller: "L" or "C"
          - tool_name
      createdat: TIMESTAMPTZ (default now)
    guarantees:
      - "Every memory write or deletion has at least one corresponding auditlog row."
      - "Search operations record filters, caller, and top-k/threshold settings."

  invariants:
    - "CURSOR = 'developer' + 'global' SCOPES ONLY."
    - "L may read/write/delete any memory in any scope (full access)."
    - "C may read/write memories with scope='developer' (project-specific)."
    - "C may read/write memories with scope='global' (cross-project developer knowledge)."
    - "C may NOT read/write memories with scope='l-private' (L's internals)."
    - "creator and source metadata are enforced server-side based on caller identity."
    - "All operations are captured in audit log with project_id, scope, caller, and full provenance."
    - "Any query from C MUST filter: WHERE scope IN ('developer', 'global')"
    - "Project isolation: developer scope is namespaced by project_id."

  # =============================================================================
  # MIGRATION PLAN: Unified Memory (v2.0)
  # =============================================================================
  migration_plan:
    status: PENDING
    description: >
      Migrate from separate memory.* tables to unified L9 Memory Substrate.
      MCP API will write to packet_store with scope="developer".
    
    phase_1_schema:
      description: Add project_id and new scopes to L9 substrate
      tasks:
        - "ADD COLUMN project_id TEXT to packet_store (nullable for global)"
        - "ALTER packet_store CHECK constraint to allow scope IN ('developer', 'l-private', 'global')"
        - "Add composite index on (project_id, scope) for fast filtering"
        - "Add index on scope for cross-project queries"
    
    phase_2_mcp_rewrite:
      description: Rewrite MCP handlers to use L9 tables
      tasks:
        - "MCP save_memory → INSERT into packet_store with scope='developer'"
        - "MCP search_memory → SELECT from packet_store WHERE scope IN ('developer', 'global')"
        - "MCP save uses memory_embeddings for vector storage"
        - "Delete handlers for memory.shortterm/mediumterm/longterm"
    
    phase_3_cleanup:
      description: Remove deprecated tables
      tasks:
        - "DROP TABLE memory.short_term"
        - "DROP TABLE memory.medium_term"
        - "DROP TABLE memory.long_term"
        - "DROP TABLE memory.audit_log (use L9 audit instead)"
        - "DROP SCHEMA memory CASCADE (if empty)"
    
    phase_4_validation:
      description: Verify multi-project access (Cursor = developer + global)
      tasks:
        - "Test: Cursor writes with scope='developer', L can read"
        - "Test: L writes with scope='developer', Cursor can read"
        - "Test: Cursor writes with scope='global', L can read"
        - "Test: L writes with scope='global', Cursor can read"
        - "Test: L writes with scope='l-private', Cursor CANNOT read"
        - "Test: Cursor query has WHERE scope IN ('developer', 'global')"
        - "Test: Cursor cannot write to scope='l-private'"
        - "Test: project_id isolation for developer scope"
