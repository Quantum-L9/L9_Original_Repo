"""
L-CTO Tool Input Schemas
========================

Pydantic models for validating tool inputs.
Used by ExecutorToolRegistry to validate tool arguments before dispatch.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-27T02:00:41Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "l_tools",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any

from pydantic import BaseModel, Field


class MemorySearchInput(BaseModel):
    """Input schema for memory search tool."""

    query: str = Field(
        ...,
        description="Natural language search query",
        min_length=1,
        max_length=1000,
    )
    segment: str = Field(
        "all",
        description="Memory segment: 'all', 'governance', 'project', 'session'",
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum results to return",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "L's capabilities with tools",
                "segment": "all",
                "limit": 10,
            }
        }
    }


class MemoryWriteInput(BaseModel):
    """Input schema for memory write tool."""

    packet: dict[str, Any] = Field(
        ...,
        description="Packet data to write",
    )
    segment: str = Field(
        ...,
        description="Target memory segment",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "packet": {
                    "content": "decision log",
                    "timestamp": "2025-12-27T05:15:00Z",
                },
                "segment": "governance",
            }
        }
    }


class GMPRunInput(BaseModel):
    """Input schema for GMP run tool (high-risk, requires approval)."""

    gmp_id: str = Field(
        ...,
        description="GMP identifier",
        min_length=1,
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="GMP execution parameters",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "gmp_id": "GMP-L-CTO-P0-TOOLS",
                "params": {"target": "all_tools"},
            }
        }
    }


class GitCommitInput(BaseModel):
    """Input schema for git commit tool (high-risk, requires approval)."""

    message: str = Field(
        ...,
        description="Commit message",
        min_length=1,
        max_length=500,
    )
    files: list[str] = Field(
        default_factory=list,
        description="Files to commit (empty = all staged)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Add L-CTO tool wiring",
                "files": ["core/tools/registry.py", "runtime/l_tools.py"],
            }
        }
    }


class MacAgentExecInput(BaseModel):
    """Input schema for Mac agent execution (high-risk, requires approval)."""

    command: str = Field(
        ...,
        description="Shell command to execute",
        min_length=1,
    )
    timeout: int = Field(
        30,
        ge=5,
        le=300,
        description="Timeout in seconds",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "command": "ls -la /opt/l9/",
                "timeout": 30,
            }
        }
    }


class MCPCallToolInput(BaseModel):
    """Input schema for MCP tool call."""

    tool_name: str = Field(
        ...,
        description="Tool name in MCP catalog",
        min_length=1,
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool parameters",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tool_name": "web_search",
                "params": {"query": "L9 OS", "limit": 5},
            }
        }
    }


class WorldModelQueryInput(BaseModel):
    """Input schema for world model query."""

    query_type: str = Field(
        ...,
        description="Query type: 'get_entity', 'list_entities', 'state_version'",
        min_length=1,
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Query parameters",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query_type": "list_entities",
                "params": {"entity_type": "user", "limit": 10},
            }
        }
    }


class KernelReadInput(BaseModel):
    """Input schema for kernel read."""

    kernel_name: str = Field(
        ...,
        description="Kernel identifier: 'identity', 'safety', 'execution', etc.",
        min_length=1,
    )
    property: str = Field(
        ...,
        description="Property to read from kernel",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "kernel_name": "identity",
                "property": "designation",
            }
        }
    }


# =============================================================================
# Export all schemas
# =============================================================================

__all__ = [
    "MemorySearchInput",
    "MemoryWriteInput",
    "GMPRunInput",
    "GitCommitInput",
    "MacAgentExecInput",
    "MCPCallToolInput",
    "WorldModelQueryInput",
    "KernelReadInput",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-075",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "data-models",
        "foundation",
        "messaging",
        "pydantic",
        "schema",
        "validation",
    ],
    "keywords": ["agent", "commit", "exec", "git", "kernel", "mac", "memory", "model"],
    "business_value": "Provides l tools components including MemorySearchInput, MemoryWriteInput, GMPRunInput",
    "last_modified": "2026-01-07T13:35:57Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
