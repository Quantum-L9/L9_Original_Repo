# L9 API Documentation

Comprehensive guide to the L9 Agentic Intelligence Platform API with OpenAPI/Swagger documentation.

## 📚 Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Documentation](#api-documentation)
- [API Categories](#api-categories)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Versioning](#versioning)
- [Client SDKs](#client-sdks)

---

## Overview

The L9 Platform provides **184 REST API endpoints** across 44 modules for building, deploying, and managing AI agents with enterprise-grade governance.

**Key Features:**
- ✅ **OpenAPI 3.0 Specification** - Industry-standard API documentation
- ✅ **Interactive Swagger UI** - Test APIs directly in your browser
- ✅ **ReDoc Documentation** - Alternative, clean documentation view
- ✅ **Auto-generated Schemas** - Request/response models from Pydantic
- ✅ **Authentication Docs** - API key security scheme documented
- ✅ **Example Requests** - Copy-paste ready code examples

---

## Getting Started

### 1. Access the Documentation

**Swagger UI (Interactive):**
```
http://localhost:8000/docs
```

**ReDoc (Clean View):**
```
http://localhost:8000/redoc
```

**OpenAPI Spec (JSON):**
```
http://localhost:8000/openapi.json
```

### 2. Get an API Key

Contact `support@l9.ai` to obtain an API key for authentication.

### 3. Make Your First Request

```bash
curl -H "X-API-Key: your-api-key-here" \
     http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.5.0",
  "timestamp": "2026-01-21T00:00:00Z"
}
```

---

## Authentication

All API endpoints (except `/health`) require an API key passed in the `X-API-Key` header.

### Using cURL

```bash
curl -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/memory/packet \
     -d '{"content": "Hello, L9!"}'
```

### Using Python

```python
import requests

headers = {
    "X-API-Key": "your-api-key-here",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/memory/packet",
    headers=headers,
    json={"content": "Hello, L9!"}
)

print(response.json())
```

### Using JavaScript/TypeScript

```typescript
const response = await fetch('http://localhost:8000/memory/packet', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ content: 'Hello, L9!' }),
});

const data = await response.json();
console.log(data);
```

---

## API Documentation

### Swagger UI Features

The interactive Swagger UI at `/docs` provides:

- **Try It Out** - Execute API calls directly from the browser
- **Request/Response Schemas** - See all fields, types, and validations
- **Example Values** - Pre-filled example requests
- **Authentication** - Set your API key once, use for all requests
- **Filtering** - Search endpoints by name or tag
- **Deep Linking** - Share links to specific endpoints

### ReDoc Features

The alternative ReDoc view at `/redoc` provides:

- **Clean Layout** - Easier to read than Swagger UI
- **Three-Panel Design** - Menu, content, and examples side-by-side
- **Markdown Support** - Rich text descriptions
- **Download Spec** - Export OpenAPI specification
- **Print-Friendly** - Better for PDF export

---

## API Categories

The L9 API is organized into **8 categories**:

### 1. System APIs

**Endpoints:** 21  
**Base Path:** `/health`, `/metrics`, `/status`

**Purpose:** System health checks, monitoring, and status

**Key Endpoints:**
- `GET /health` - Overall system health
- `GET /health/neo4j` - Neo4j database health
- `GET /health/services` - All service health checks
- `GET /metrics` - Prometheus metrics
- `GET /status` - Detailed system status

---

### 2. Agent APIs

**Endpoints:** 31  
**Base Path:** `/agent`, `/cursor`, `/research`, `/reflection`

**Purpose:** Agent execution, task management, and lifecycle operations

**Key Endpoints:**
- `POST /agent/execute` - Execute an agent task
- `POST /cursor/task` - Create a Cursor agent task
- `POST /research/execute` - Run research agent
- `POST /reflection/reflect` - Trigger reflection on execution
- `GET /agent/status` - Get agent status

**Example:**
```bash
POST /agent/execute
{
  "agent_id": "research_agent",
  "task": "Analyze market trends for Q1 2026",
  "context": {
    "industry": "AI",
    "timeframe": "Q1 2026"
  }
}
```

---

### 3. Memory APIs

**Endpoints:** 45  
**Base Path:** `/memory`, `/packet`, `/cache`

**Purpose:** Memory substrate operations, semantic search, knowledge management

**Key Endpoints:**
- `POST /memory/packet` - Create a memory packet
- `POST /memory/semantic/search` - Semantic similarity search
- `GET /memory/packet/{packet_id}` - Retrieve packet by ID
- `GET /memory/thread/{thread_id}` - Get conversation thread
- `POST /memory/hybrid/search` - Hybrid search (semantic + keyword)
- `POST /cache/set` - Set cache value
- `GET /cache/get/{key}` - Get cache value

**Example:**
```bash
POST /memory/semantic/search
{
  "query": "What are the latest AI governance policies?",
  "limit": 10,
  "min_confidence": 0.7
}
```

---

### 4. World Model APIs

**Endpoints:** 14  
**Base Path:** `/world-model`, `/entity`

**Purpose:** Entity management, relationships, and world state

**Key Endpoints:**
- `POST /world-model/entity` - Create entity
- `GET /world-model/entity/{entity_id}` - Get entity
- `POST /world-model/relationship` - Create relationship
- `GET /world-model/context/{domain}` - Get domain context
- `POST /world-model/snapshot` - Create state snapshot
- `POST /world-model/restore` - Restore from snapshot

**Example:**
```bash
POST /world-model/entity
{
  "entity_type": "agent",
  "entity_id": "research_agent_001",
  "properties": {
    "name": "Research Agent",
    "capabilities": ["web_search", "document_analysis"],
    "status": "active"
  }
}
```

---

### 5. Tool APIs

**Endpoints:** 13  
**Base Path:** `/tools`, `/mcp`

**Purpose:** Tool execution, MCP integration, and tool registry

**Key Endpoints:**
- `POST /tools/execute` - Execute a tool
- `GET /mcp/tools` - List all MCP tools
- `POST /mcp/call` - Call MCP tool
- `GET /mcp/health` - MCP server health

**Example:**
```bash
POST /tools/execute
{
  "tool_name": "web_search",
  "parameters": {
    "query": "latest AI research papers",
    "limit": 5
  }
}
```

---

### 6. Governance APIs

**Endpoints:** 15  
**Base Path:** `/governance`, `/compliance`

**Purpose:** Policy enforcement, compliance reporting, audit logs

**Key Endpoints:**
- `GET /compliance/report` - Get compliance report
- `GET /compliance/audit-log` - Retrieve audit logs
- `POST /governance/feedback` - Submit governance feedback
- `GET /compliance/report/daily` - Daily compliance summary

**Example:**
```bash
GET /compliance/audit-log?start_date=2026-01-01&end_date=2026-01-21
```

---

### 7. Integration APIs

**Endpoints:** 11  
**Base Path:** `/slack`, `/twilio`, `/waba`

**Purpose:** External service integrations (Slack, Twilio, WhatsApp)

**Key Endpoints:**
- `POST /slack/events` - Slack event webhook
- `POST /slack/commands` - Slack slash commands
- `POST /twilio/webhook` - Twilio SMS webhook
- `GET /waba/webhook` - WhatsApp webhook verification
- `POST /waba/webhook` - WhatsApp message webhook

---

### 8. Observability APIs

**Endpoints:** 34  
**Base Path:** `/observability`, `/metrics`, `/spans`

**Purpose:** Metrics, traces, circuit breakers, and monitoring

**Key Endpoints:**
- `GET /observability/metrics` - System metrics
- `GET /observability/spans` - Distributed traces
- `GET /observability/failures` - Failure tracking
- `GET /observability/circuit-breakers` - Circuit breaker states

---

## Common Patterns

### Pagination

Many list endpoints support pagination:

```bash
GET /memory/facts?limit=20&offset=0
```

**Parameters:**
- `limit` (int): Number of results per page (default: 20, max: 100)
- `offset` (int): Number of results to skip (default: 0)

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 156,
    "has_more": true
  }
}
```

### Filtering

Use query parameters for filtering:

```bash
GET /memory/packets?status=active&created_after=2026-01-01
```

### Sorting

Use `sort_by` and `order` parameters:

```bash
GET /memory/packets?sort_by=created_at&order=desc
```

### Batch Operations

Some endpoints support batch operations:

```bash
POST /memory/batch
{
  "operations": [
    {"action": "create", "data": {...}},
    {"action": "update", "id": "123", "data": {...}}
  ]
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message",
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2026-01-21T00:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|---|---|---|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Validation Error | Request data validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Codes

| Code | Description |
|---|---|
| `VALIDATION_ERROR` | Request data validation failed |
| `AUTH_ERROR` | Authentication failed |
| `PERMISSION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Internal server error |

---

## Rate Limiting

**Default Limits:**
- **100 requests per minute** per API key
- **1,000 requests per hour** per API key

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642780800
```

**When rate limited:**
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "status": "rate_limited",
  "retry_after": 45
}
```

---

## Versioning

The L9 API uses **semantic versioning** (MAJOR.MINOR.PATCH).

**Current Version:** `2.5.0`

**Version Header:**
```
X-API-Version: 2.5.0
```

**Breaking Changes:**
- Major version changes (e.g., 2.x → 3.x) may include breaking changes
- Minor version changes (e.g., 2.5 → 2.6) are backward compatible
- Patch version changes (e.g., 2.5.0 → 2.5.1) are bug fixes only

---

## Client SDKs

### Generate Client SDKs

Use the OpenAPI specification to generate client SDKs in any language:

**Python:**
```bash
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g python \
  -o ./l9-python-client
```

**TypeScript:**
```bash
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-axios \
  -o ./l9-typescript-client
```

**Go:**
```bash
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g go \
  -o ./l9-go-client
```

### Official SDKs (Coming Soon)

- **Python SDK** - `pip install l9-client`
- **TypeScript SDK** - `npm install @l9/client`
- **Go SDK** - `go get github.com/l9/client-go`

---

## Support

**Documentation:** https://docs.l9.ai  
**GitHub:** https://github.com/cryptoxdog/L9  
**Support:** https://help.l9.ai  
**Email:** support@l9.ai

---

**Last Updated:** 2026-01-21  
**API Version:** 2.5.0
