"""
L9 Mac Protocol
Message schema for reverse tunnel communications.
JSON-only protocol definition.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Mac Protocol",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "mac_protocol",
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

from datetime import UTC
from typing import Any

from pydantic import BaseModel, Field


class MacMessage(BaseModel):
    """
    Mac protocol message schema.
    Used for reverse tunnel communications from Mac to VPS.
    """

    token: str = Field(..., description="Authentication token")
    cmd: str = Field(..., description="Command to execute")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    cwd: str | None = Field(None, description="Working directory")
    timeout: int | None = Field(None, description="Command timeout in seconds")

    class Config:
        """
        Represents configuration schema for L9 Mac Protocol reverse tunnel communications.

        Args:
            json_schema_extra (dict): Additional schema details, including example message structure.


        Raises:
            KeyError: If required schema keys are missing in the configuration.
        """

        json_schema_extra = {
            "example": {
                "token": "abc123",
                "cmd": "ls",
                "args": ["-la"],
                "cwd": "/opt/l9",
                "timeout": 30,
            }
        }


class MacResponse(BaseModel):
    """
    Mac protocol response schema.
    """

    success: bool = Field(..., description="Whether command succeeded")
    output: str = Field(default="", description="Command stdout")
    error: str = Field(default="", description="Command stderr")
    exit_code: int = Field(..., description="Command exit code")
    timestamp: str = Field(..., description="ISO8601 timestamp")

    class Config:
        """
        Represents configuration schema details for the L9 Mac Protocol's reverse tunnel JSON messages.

        Args:
            json_schema_extra: Dictionary containing example schema data for validation and documentation purposes.


        Raises:
            KeyError: If expected schema keys are missing in json_schema_extra.
        """

        json_schema_extra = {
            "example": {
                "success": True,
                "output": "file1.txt\nfile2.txt\n",
                "error": "",
                "exit_code": 0,
                "timestamp": "2025-01-29T12:00:00Z",
            }
        }


def parse_mac_message(data: dict[str, Any]) -> MacMessage:
    """Parse and validate Mac protocol message."""
    return MacMessage(**data)


def create_mac_response(
    success: bool,
    output: str = "",
    error: str = "",
    exit_code: int = 0,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Create Mac protocol response dict."""
    from datetime import datetime, timezone

    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    response = MacResponse(
        success=success,
        output=output,
        error=error,
        exit_code=exit_code,
        timestamp=timestamp,
    )
    return response.dict()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "data-models",
        "messaging",
        "operations",
        "pydantic",
        "schema",
        "validation",
    ],
    "keywords": ["create", "mac", "parse", "protocol"],
    "business_value": "Provides mac protocol components including MacMessage, MacResponse, Config",
    "last_modified": "2026-01-07T13:35:58Z",
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
