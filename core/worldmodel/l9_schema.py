"""
L9 World Model - Entity and Relationship Schema
================================================

Defines L9-specific entity types and relationships for the world model.
These entities represent L9 operational components: agents, tools,
infrastructure, repositories, memory segments, and external systems.

Version: 1.0.0 (GMP-18)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Entity and Relationship Schema",
    "module_version": "1.0.0 (GMP-18)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "l9_schema",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "core.worldmodel.__init__",
            "core.worldmodel.service",
            "tests.integration.test_world_model",
        ],
    },
}
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class EntityType(str, Enum):
    """Types of entities in the L9 world model."""

    AGENT = "agent"
    REPOSITORY = "repository"
    INFRASTRUCTURE = "infrastructure"
    TOOL = "tool"
    MEMORY_SEGMENT = "memory_segment"
    EXTERNAL_SYSTEM = "external_system"


class InfrastructureType(str, Enum):
    """Types of infrastructure components."""

    DATABASE = "database"
    CACHE = "cache"
    GRAPH_DB = "graph_db"
    MESSAGE_QUEUE = "message_queue"
    REVERSE_PROXY = "reverse_proxy"
    CONTAINER = "container"


class ToolCategory(str, Enum):
    """Categories of tools."""

    MEMORY = "memory"
    CODE = "code"
    GOVERNANCE = "governance"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    FILE_SYSTEM = "file_system"
    EXTERNAL_API = "external_api"


class ToolRiskLevel(str, Enum):
    """Risk levels for tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectionStatus(str, Enum):
    """Connection status for external systems."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class L9RelationshipType(str, Enum):
    """Types of relationships between entities."""

    HAS_TOOL = "HAS_TOOL"
    DEPENDS_ON = "DEPENDS_ON"
    WRITES_TO = "WRITES_TO"
    READS_FROM = "READS_FROM"
    INTEGRATES_WITH = "INTEGRATES_WITH"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    MANAGES = "MANAGES"
    CONTAINS = "CONTAINS"


# =============================================================================
# Entity Models
# =============================================================================


class L9Agent(BaseModel):
    """Agent entity in the L9 world model."""

    id: UUID = Field(default_factory=uuid4, description="Unique agent identifier")
    name: str = Field(..., description="Agent name (e.g., 'L', 'CA', 'QA', 'Mac')")
    role: str = Field(
        ..., description="Agent role (e.g., 'CTO', 'Research', 'Testing')"
    )
    capabilities: list[str] = Field(
        default_factory=list, description="List of capability names"
    )
    kernel_version: str | None = Field(
        None, description="Version of kernels used by agent"
    )
    last_active: datetime | None = Field(None, description="Last activity timestamp")
    status: str = Field(default="active", description="Agent status")
    entity_type: EntityType = Field(default=EntityType.AGENT)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "kernel_version": self.kernel_version,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "status": self.status,
        }


class L9Repository(BaseModel):
    """Repository entity in the L9 world model."""

    id: UUID = Field(default_factory=uuid4, description="Unique repo identifier")
    name: str = Field(..., description="Repository name (e.g., 'L9', 'configs')")
    path: str = Field(..., description="Local or remote path")
    integration_type: str = Field(
        default="git", description="Integration type (git, svn, etc.)"
    )
    last_push: datetime | None = Field(None, description="Last push timestamp")
    default_branch: str = Field(default="main", description="Default branch name")
    remote_url: str | None = Field(None, description="Remote repository URL")
    entity_type: EntityType = Field(default=EntityType.REPOSITORY)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "path": self.path,
            "integration_type": self.integration_type,
            "last_push": self.last_push.isoformat() if self.last_push else None,
            "default_branch": self.default_branch,
            "remote_url": self.remote_url,
        }


class L9Infrastructure(BaseModel):
    """Infrastructure component entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique infra identifier")
    name: str = Field(
        ..., description="Infrastructure name (e.g., 'l9-postgres', 'l9-redis')"
    )
    infra_type: InfrastructureType = Field(..., description="Type of infrastructure")
    status: str = Field(default="running", description="Current status")
    endpoints: list[str] = Field(default_factory=list, description="Service endpoints")
    health_check_url: str | None = Field(None, description="Health check endpoint")
    container_name: str | None = Field(None, description="Docker container name")
    port: int | None = Field(None, description="Service port")
    entity_type: EntityType = Field(default=EntityType.INFRASTRUCTURE)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "infra_type": self.infra_type.value,
            "status": self.status,
            "endpoints": self.endpoints,
            "health_check_url": self.health_check_url,
            "container_name": self.container_name,
            "port": self.port,
        }


class L9Tool(BaseModel):
    """Tool entity in the L9 world model."""

    id: UUID = Field(default_factory=uuid4, description="Unique tool identifier")
    name: str = Field(..., description="Tool name (e.g., 'memory_write', 'gmprun')")
    category: ToolCategory = Field(..., description="Tool category")
    risk_level: ToolRiskLevel = Field(
        default=ToolRiskLevel.LOW, description="Risk level"
    )
    requires_approval: bool = Field(default=False, description="Requires Igor approval")
    last_used: datetime | None = Field(None, description="Last usage timestamp")
    use_count: int = Field(default=0, description="Total usage count")
    description: str | None = Field(None, description="Tool description")
    entity_type: EntityType = Field(default=EntityType.TOOL)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "description": self.description,
        }


class L9MemorySegment(BaseModel):
    """Memory segment entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique segment identifier")
    name: str = Field(..., description="Segment name (e.g., 'governance_patterns')")
    segment_type: str = Field(..., description="Type of content stored")
    last_updated: datetime | None = Field(None, description="Last update timestamp")
    size_bytes: int = Field(default=0, description="Approximate size in bytes")
    query_count: int = Field(default=0, description="Total queries to this segment")
    retention_days: int | None = Field(None, description="Retention period in days")
    entity_type: EntityType = Field(default=EntityType.MEMORY_SEGMENT)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "segment_type": self.segment_type,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "size_bytes": self.size_bytes,
            "query_count": self.query_count,
            "retention_days": self.retention_days,
        }


class L9ExternalSystem(BaseModel):
    """External system integration entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique system identifier")
    name: str = Field(
        ..., description="System name (e.g., 'GitHub', 'Slack', 'Perplexity')"
    )
    integration_type: str = Field(
        ..., description="Integration type (api, webhook, mcp)"
    )
    api_endpoint: str | None = Field(None, description="API endpoint URL")
    connection_status: ConnectionStatus = Field(
        default=ConnectionStatus.UNKNOWN, description="Current connection status"
    )
    last_contact: datetime | None = Field(None, description="Last successful contact")
    auth_method: str | None = Field(
        None, description="Authentication method (api_key, oauth, etc.)"
    )
    entity_type: EntityType = Field(default=EntityType.EXTERNAL_SYSTEM)

    def to_node_dict(self) -> dict[str, Any]:
        """Convert to world model node dict."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "integration_type": self.integration_type,
            "api_endpoint": self.api_endpoint,
            "connection_status": self.connection_status.value,
            "last_contact": (
                self.last_contact.isoformat() if self.last_contact else None
            ),
            "auth_method": self.auth_method,
        }


# =============================================================================
# Relationship Model
# =============================================================================


class L9Relationship(BaseModel):
    """Relationship between two entities in the world model."""

    id: UUID = Field(default_factory=uuid4, description="Unique relationship ID")
    relationship_type: L9RelationshipType = Field(
        ..., description="Type of relationship"
    )
    source_id: UUID = Field(..., description="Source entity ID")
    source_type: EntityType = Field(..., description="Source entity type")
    target_id: UUID = Field(..., description="Target entity ID")
    target_type: EntityType = Field(..., description="Target entity type")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Relationship properties"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    def to_edge_dict(self) -> dict[str, Any]:
        """Convert to world model edge dict."""
        return {
            "id": str(self.id),
            "type": self.relationship_type.value,
            "source_id": str(self.source_id),
            "source_type": self.source_type.value,
            "target_id": str(self.target_id),
            "target_type": self.target_type.value,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ConnectionStatus",
    # Enums
    "EntityType",
    "InfrastructureType",
    # Entity models
    "L9Agent",
    "L9ExternalSystem",
    "L9Infrastructure",
    "L9MemorySegment",
    # Relationship model
    "L9Relationship",
    "L9RelationshipType",
    "L9Repository",
    "L9Tool",
    "ToolCategory",
    "ToolRiskLevel",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-081",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "caching",
        "data-access",
        "data-models",
        "enum",
        "foundation",
        "messaging",
        "pydantic",
        "queue",
    ],
    "keywords": [
        "agent",
        "category",
        "connection",
        "edge",
        "entity",
        "external",
        "infrastructure",
        "memory",
    ],
    "business_value": "Provides l9 schema components including EntityType, InfrastructureType, ToolCategory",
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
