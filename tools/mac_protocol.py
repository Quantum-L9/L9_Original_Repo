"""
L9 Mac Protocol
Message schema for reverse tunnel communications.
JSON-only protocol definition.
"""


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


# Runtime execution trace - updated automatically on every execution
