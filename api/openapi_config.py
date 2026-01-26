"""
OpenAPI/Swagger Configuration for L9 API
=========================================

Comprehensive OpenAPI 3.0 configuration with:
- Enhanced metadata and documentation
- Security schemes (API Key authentication)
- Custom Swagger UI configuration
- ReDoc alternative documentation
- Example requests and responses

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "OpenAPIConfig",
    "module_version": "1.0.0",
    "created_by": "Manus AI",
    "created_at": "2026-01-21T00:00:00Z",
    "updated_at": "2026-01-21T00:00:00Z",
    "layer": "api",
    "domain": "documentation",
    "module_name": "openapi_config",
    "type": "configuration",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["All API endpoints"],
        "datasources": ["OpenAPI Specification"],
    },
}
# ============================================================================

from typing import Any

# OpenAPI Metadata
OPENAPI_METADATA = {
    "title": "L9 Agentic Intelligence Platform API",
    "version": "2.5.0",
    "description": """
# L9 Agentic Intelligence Platform

The L9 Platform provides a comprehensive suite of APIs for building, deploying, and managing AI agents with enterprise-grade governance, observability, and security.

## 🎯 Key Features

- **Agent Execution**: Deploy and orchestrate AI agents with kernel-based governance
- **Memory Substrate**: Packet/envelope architecture with semantic search and knowledge graphs
- **World Model**: Maintain system-wide state with entity relationships and temporal reasoning
- **Tool Integration**: Execute tools with MCP (Model Context Protocol) support
- **Observability**: Distributed tracing, metrics, and circuit breakers
- **Compliance**: Audit logs, policy enforcement, and governance reporting

## 🏗️ Architecture

The L9 platform follows a **kernel-governed microservices architecture**:

1. **Kernel Layer**: Immutable governance rules and security policies
2. **Runtime Layer**: Agent execution, task queuing, and lifecycle management
3. **Memory Layer**: PostgreSQL + pgvector for semantic memory, Neo4j for knowledge graphs
4. **API Layer**: FastAPI REST endpoints with WebSocket support
5. **Observability Layer**: Jaeger tracing, Prometheus metrics, structured logging

## 🔐 Authentication

All API endpoints require an API key passed in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" https://api.l9.ai/health
```

## 📚 Documentation

- **Swagger UI**: Interactive API documentation (this page)
- **ReDoc**: Alternative documentation view at `/redoc`
- **OpenAPI Spec**: Download the spec at `/openapi.json`

## 🚀 Quick Start

### 1. Health Check
```bash
GET /health
```

### 2. Execute Agent Task
```bash
POST /agent/execute
{
  "agent_id": "research_agent",
  "task": "Analyze market trends",
  "context": {}
}
```

### 3. Search Memory
```bash
POST /memory/semantic/search
{
  "query": "What are the latest findings?",
  "limit": 10
}
```

## 📖 API Categories

| Category | Endpoints | Description |
|---|---|---|
| **System** | `/health`, `/metrics` | System health and monitoring |
| **Agents** | `/agent/*`, `/cursor/*` | Agent execution and management |
| **Memory** | `/memory/*`, `/packet/*` | Memory operations and search |
| **World Model** | `/world-model/*` | Entity management and state |
| **Tools** | `/tools/*`, `/mcp/*` | Tool execution and MCP integration |
| **Governance** | `/compliance/*`, `/governance/*` | Policy enforcement and auditing |
| **Integrations** | `/slack/*`, `/twilio/*` | External service integrations |

## 🔗 External Resources

- **Documentation**: https://docs.l9.ai
- **GitHub**: https://github.com/cryptoxdog/L9
- **Support**: https://help.l9.ai

## 📝 License

Proprietary - All Rights Reserved
""",
    "contact": {
        "name": "L9 Platform Support",
        "url": "https://help.l9.ai",
        "email": "support@l9.ai",
    },
    "license_info": {
        "name": "Proprietary",
        "url": "https://l9.ai/license",
    },
    "terms_of_service": "https://l9.ai/terms",
}

# OpenAPI Tags (for endpoint grouping)
OPENAPI_TAGS = [
    {
        "name": "System",
        "description": "System health, metrics, and status endpoints",
    },
    {
        "name": "Agents",
        "description": "Agent execution, task management, and lifecycle operations",
    },
    {
        "name": "Memory",
        "description": "Memory substrate operations: packets, envelopes, semantic search",
    },
    {
        "name": "World Model",
        "description": "Entity management, relationships, and world state",
    },
    {
        "name": "Tools",
        "description": "Tool execution, MCP integration, and tool registry",
    },
    {
        "name": "Governance",
        "description": "Policy enforcement, compliance reporting, and audit logs",
    },
    {
        "name": "Integrations",
        "description": "External service integrations (Slack, Twilio, WhatsApp)",
    },
    {
        "name": "Observability",
        "description": "Metrics, traces, circuit breakers, and monitoring",
    },
]

# Security Schemes
OPENAPI_SECURITY_SCHEMES = {
    "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key for authentication. Contact support@l9.ai to obtain an API key.",
    }
}

# Swagger UI Configuration
SWAGGER_UI_PARAMETERS = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "filter": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "syntaxHighlight.theme": "monokai",
    "tryItOutEnabled": True,
    "persistAuthorization": True,
    "docExpansion": "list",  # "list", "full", or "none"
    "defaultModelsExpandDepth": 3,
    "defaultModelExpandDepth": 3,
    "displayOperationId": False,
}

# ReDoc Configuration
REDOC_PARAMETERS = {
    "hideDownloadButton": False,
    "expandResponses": "200,201",
    "jsonSampleExpandLevel": 2,
    "hideSingleRequestSampleTab": True,
    "menuToggle": True,
    "nativeScrollbars": False,
    "pathInMiddlePanel": True,
    "requiredPropsFirst": True,
    "sortPropsAlphabetically": True,
    "theme": {
        "colors": {
            "primary": {"main": "#2196F3"},
        },
        "typography": {
            "fontSize": "14px",
            "fontFamily": "'Roboto', sans-serif",
            "headings": {
                "fontFamily": "'Roboto', sans-serif",
            },
            "code": {
                "fontSize": "13px",
                "fontFamily": "'Source Code Pro', monospace",
            },
        },
    },
}


def get_openapi_config() -> dict[str, Any]:
    """
    Get complete OpenAPI configuration for FastAPI app.

    Returns:
        Dictionary with all OpenAPI configuration parameters
    """
    return {
        **OPENAPI_METADATA,
        "openapi_tags": OPENAPI_TAGS,
        "swagger_ui_parameters": SWAGGER_UI_PARAMETERS,
        "redoc_parameters": REDOC_PARAMETERS,
    }


def get_security_schemes() -> dict[str, dict[str, Any]]:
    """
    Get OpenAPI security schemes.

    Returns:
        Dictionary of security scheme definitions
    """
    return OPENAPI_SECURITY_SCHEMES


# Example responses for common scenarios
EXAMPLE_RESPONSES = {
    "success": {
        "200": {
            "description": "Successful operation",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {},
                        "timestamp": "2026-01-21T00:00:00Z",
                    }
                }
            },
        }
    },
    "created": {
        "201": {
            "description": "Resource created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "created",
                        "id": "resource-id-123",
                        "timestamp": "2026-01-21T00:00:00Z",
                    }
                }
            },
        }
    },
    "unauthorized": {
        "401": {
            "description": "Unauthorized - Invalid or missing API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key",
                        "status": "unauthorized",
                    }
                }
            },
        }
    },
    "forbidden": {
        "403": {
            "description": "Forbidden - Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Insufficient permissions for this operation",
                        "status": "forbidden",
                    }
                }
            },
        }
    },
    "not_found": {
        "404": {
            "description": "Resource not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Resource not found",
                        "status": "not_found",
                    }
                }
            },
        }
    },
    "validation_error": {
        "422": {
            "description": "Validation error - Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "field_name"],
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    }
                }
            },
        }
    },
    "internal_error": {
        "500": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Internal server error",
                        "status": "error",
                        "timestamp": "2026-01-21T00:00:00Z",
                    }
                }
            },
        }
    },
}
