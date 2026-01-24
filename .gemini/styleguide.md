# L9 Repository Style Guide for Gemini Code Assist

## Project Overview
L9 is a frontier-tier AI agent system with:
- **PacketEnvelope protocol**: Inter-component messaging standard
- **Kernel system**: Immutable core logic (protected files)
- **Memory substrates**: PostgreSQL (relational), Neo4j (graph), Redis (cache)
- **Governance layer**: Tool usage policies, rate limits, approval workflows

## Protected Files (DO NOT MODIFY)
These files contain critical invariants and require explicit approval:
- `api/websocket_orchestrator.py` — WebSocket event routing
- `docker-compose.yml` — Infrastructure configuration
- `core/kernel_loader.py` — Kernel initialization
- `memory/substrate_service.py` — Memory abstraction layer
- `core/schemas/packet_envelope.py` — Protocol definitions
- All files in `private/kernels/` — Kernel implementations

## Code Quality Standards

### Python Style
- **Type hints**: Required on all public functions/methods
  ```python
  def process_packet(packet: PacketEnvelope) -> PacketResponse:
  ```

- **Docstrings**: Google style with Args/Returns/Raises
  ```python
  """Process incoming packet through governance layer.
  
  Args:
      packet: PacketEnvelope with routing metadata
  
  Returns:
      PacketResponse with execution result
  
  Raises:
      GovernanceViolation: If packet fails policy checks
  """
  ```

- **Error handling**: No bare `except:` — always specify exception types
- **Async patterns**: Use `async`/`await` for I/O operations
- **Imports**: Absolute imports from project root (`from core.schemas import ...`)

### L9 Architectural Patterns

#### PacketEnvelope Protocol
All inter-component communication uses PacketEnvelope:
```python
packet = PacketEnvelope(
    packet_id=str(uuid.uuid4()),
    packet_type=PacketType.TOOL_REQUEST,
    sender="agent-executor",
    receiver="tool-registry",
    payload=ToolCallRequest(...)
)
```

#### Memory Substrate Usage
Never write directly to databases. Always use MemorySubstrateService:
```python
# ❌ BAD
await pg_pool.execute("INSERT INTO memories ...")

# ✅ GOOD
await substrate_service.store_memory(
    agent_id="L",
    content="...",
    metadata={...}
)
```

#### Governance Checks
All tool executions must pass governance:
```python
approval = await governance_engine.check_tool_approval(
    tool_id="filesystem_write",
    agent_id="L",
    context={...}
)
if not approval.allowed:
    raise GovernanceViolation(approval.reason)
```

### Production Readiness
- **No TODOs/FIXMEs**: Remove or convert to GitHub issues
- **No placeholders**: Implement complete logic or raise `NotImplementedError` with issue link
- **No print statements**: Use structured logging (`logger.info/warning/error`)
- **Environment variables**: Always provide defaults or fail-fast validation

## Security Requirements
- **Input validation**: Sanitize all external inputs (API, WebSocket, file uploads)
- **Secret management**: Never hardcode API keys — use environment variables
- **SQL injection**: Use parameterized queries (we use SQLAlchemy/asyncpg)
- **Path traversal**: Validate file paths against allowed directories

## Testing Expectations
- **Critical paths**: Add tests for governance checks, memory operations, packet routing
- **Edge cases**: Test error conditions, malformed inputs, boundary values
- **Async tests**: Use `pytest-asyncio` with proper fixtures

## Performance Considerations
- **Async I/O**: Database/API calls should be async
- **Caching**: Use Redis for frequently accessed data
- **Batch operations**: Prefer bulk inserts/updates over loops
- **Connection pooling**: Reuse DB connections (already configured in L9)

## Review Priorities (Ordered by Impact)
1. **Governance violations** (bypassing approval checks)
2. **Memory substrate misuse** (direct DB writes)
3. **Kernel modifications** (changes to protected files)
4. **Security issues** (injection, secrets exposure)
5. **Type safety** (missing type hints)
6. **Documentation** (missing docstrings)
7. **Code style** (formatting, naming conventions)

## Common L9 Anti-Patterns to Flag
- ❌ Direct database access bypassing `MemorySubstrateService`
- ❌ Synchronous blocking calls in async functions
- ❌ Hardcoded agent IDs (use registry lookups)
- ❌ Missing error handling for external API calls
- ❌ Tool execution without governance checks
- ❌ PacketEnvelope fields set incorrectly (missing `sender`/`receiver`)

## Enhancement Opportunities
When reviewing code, suggest:
- **Performance**: Async patterns, caching opportunities, batch operations
- **Architecture**: Better separation of concerns, dependency injection
- **Observability**: Add metrics, tracing spans, structured logs
- **Resilience**: Retry logic, circuit breakers, graceful degradation
