# L9 Architecture Diagrams

This directory contains comprehensive architecture diagrams for all major subsystems of the L9 Agentic Intelligence Platform.

## Overview

Each diagram provides a detailed view of a specific subsystem, showing:

- Component relationships and data flow
- Integration points and dependencies
- Governance and security enforcement
- External service connections

## Diagrams

### 1. Memory Substrate (`01-memory-substrate.mmd/png`)

**PostgreSQL + pgvector memory layer with envelope/packet architecture**

Shows the complete memory storage and retrieval system including:

- SubstrateService and ToolRouter
- Packet and Envelope builders
- PostgreSQL database with pgvector indexing
- Embedding generation via OpenAI
- Semantic search capabilities

### 2. Governance System (`02-governance-system.mmd/png`)

**Policy enforcement, credentials management, execution gating**

Illustrates the security and policy enforcement layer:

- ExecutionGate with pre/post-execution checks
- PolicyRegistry with multiple policy types
- Audit logging and metrics collection
- Fail-closed behavior on policy violations

### 3. Kernel & Runtime (`03-kernel-runtime.mmd/png`)

**Kernel loading, task execution, background processing**

Details the core runtime system:

- kernel_loader_ultimate.py with integrity checks
- TaskQueue and priority scheduling
- Background task management
- Fail-safe and tamper detection

### 4. Agent Execution (`04-agent-execution.mmd/png`)

**Agent lifecycle, prompt building, LLM integration**

Maps the agent execution flow:

- AgentExecutor and AgentInstance
- PromptBuilder with context integration
- LLM call handling with retry and rate limiting
- Tool invocation with governance gates

### 5. World Model (`05-world-model.mmd/png`)

**Knowledge graph, entity tracking, fact storage**

Represents the knowledge management system:

- KnowledgeIngestor and entity extraction
- EntityTracker with deduplication (SHA256)
- WorldModelEngine with temporal management
- Neo4j/Aura graph database integration

### 6. API & WebSocket (`06-api-websocket.mmd/png`)

**FastAPI server, REST endpoints, WebSocket connections**

Shows the API layer architecture:

- FastAPI server with middleware stack
- Authentication (API key, JWT, session)
- REST endpoints and WebSocket handler
- Connection pooling and heartbeat monitoring

### 7. Orchestration (`07-orchestration.mmd/png`)

**Multi-agent coordination, workflow execution**

Depicts multi-agent orchestration:

- UnifiedController with task decomposition
- PlanExecutor (parallel and sequential)
- AgentCoordinator with agent selection
- Result aggregation and validation

### 8. Singleton Registry (`08-singleton-registry.mmd/png`)

**Dependency injection, singleton management**

Explains service management:

- SingletonRegistry with lazy initialization
- AutoRegistry with service discovery
- Lifecycle management (startup/shutdown)
- Dependency resolution and wiring

### 9. Tool System (`09-tool-system.mmd/png`)

**Tool discovery, routing, execution**

Details the tool infrastructure:

- ToolRegistry with metadata catalog
- ToolRouter with semantic matching
- ToolEmbeddings with vector similarity
- Governance gate and result caching

### 10. MCP Integration (`10-mcp-integration.mmd/png`)

**Model Context Protocol server management**

Illustrates MCP server integration:

- MCPServerRegistry with lifecycle management
- Active MCP servers (Fireflies, Supabase, Notion, etc.)
- Protocol handling and serialization
- Connection pooling and health monitoring

## File Formats

Each diagram is provided in two formats:

- **`.mmd`** - Mermaid source (text-based, version-controllable)
- **`.png`** - Rendered PNG image (for viewing and documentation)

## Rendering Diagrams

To re-render diagrams after editing `.mmd` files:

```bash
# Render a single diagram
manus-render-diagram readme/diagrams/01-memory-substrate.mmd readme/diagrams/01-memory-substrate.png

# Render all diagrams
for mmd in readme/diagrams/*.mmd; do
    png="${mmd%.mmd}.png"
    manus-render-diagram "$mmd" "$png"
done
```

## Color Legend

Diagrams use consistent color coding:

- **🔵 Cyan (#4ecdc4)** - Primary services and controllers
- **🟡 Yellow (#ffe66d)** - Routing and coordination layers
- **🟢 Green (#95e1d3)** - Processing and execution components
- **🟢 Light Green (#a8e6cf)** - Storage and caching layers
- **🔴 Red (#ff6b6b)** - Security, governance, and critical paths

## Integration with Main Architecture

These subsystem diagrams complement the main system architecture diagram (`readme/architecture.mmd/png`), providing detailed views of each layer.

## Updates and Maintenance

When updating diagrams:

1. Edit the `.mmd` source file
2. Re-render to `.png` using `manus-render-diagram`
3. Commit both files to version control
4. Update this README if adding new diagrams

---

**Generated:** 2026-01-18
**L9 Version:** v3.0
**Diagram Count:** 10
