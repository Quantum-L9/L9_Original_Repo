"""
L9 Docker Tests - Configuration and Fixtures
Version: 1.1.0

Provides auto-detection of execution context (Docker vs host) for service URL resolution.
This allows the same tests to run:
- Inside Docker containers (using Docker DNS: l9-api, l9-postgres, etc.)
- From host machine (using localhost: 127.0.0.1)

No docker-compose.yml changes required. No environment variables required.
Manual override still works: API_BASE_URL=http://custom pytest ...

NOTE: l9-memory-api (port 8080) is DEPRECATED.
      MCP Memory Server (l9-mcp-memory, port 9002) is the ONLY supported memory path.
"""

import os
import socket
from typing import Literal


def get_execution_context() -> Literal["docker", "host"]:
    """
    Detect if running inside Docker or on host machine.
    
    Detection methods:
    1. Check for /.dockerenv file (present in Docker containers)
    2. Try to resolve Docker service DNS name
    
    Returns:
        "docker" if running inside Docker network
        "host" if running on host machine
    """
    # Method 1: Check for Docker environment file
    if os.path.exists("/.dockerenv"):
        return "docker"
    
    # Method 2: Check if Docker DNS resolves
    try:
        socket.gethostbyname("l9-api")
        return "docker"
    except socket.gaierror:
        return "host"


def resolve_service_url(service_name: str, port: int) -> str:
    """
    Auto-resolve service URL based on execution context.
    
    Priority:
    1. Environment variable override (SERVICE_NAME_URL)
    2. Docker DNS if inside Docker network
    3. localhost (127.0.0.1) if on host
    
    Args:
        service_name: Docker service name (e.g., "l9-api", "l9-postgres")
        port: Service port number
        
    Returns:
        Resolved URL (e.g., "http://l9-api:8000" or "http://127.0.0.1:8000")
        
    Examples:
        >>> resolve_service_url("l9-api", 8000)
        'http://127.0.0.1:8000'  # from host
        
        >>> resolve_service_url("l9-api", 8000)
        'http://l9-api:8000'  # from Docker
        
        >>> os.environ["L9_API_URL"] = "http://custom:9000"
        >>> resolve_service_url("l9-api", 8000)
        'http://custom:9000'  # manual override
    """
    # Check for manual override via environment variable
    # Convert service name to env var format: l9-api -> L9_API_URL
    env_key = f"{service_name.upper().replace('-', '_')}_URL"
    if url := os.environ.get(env_key):
        return url
    
    # Also check common override patterns
    if service_name == "l9-api":
        if url := os.environ.get("API_BASE_URL"):
            return url
    elif service_name == "l9-mcp-memory":
        if url := os.environ.get("MCP_MEMORY_URL"):
            return url
        # Legacy fallback (DEPRECATED - will be removed)
        if url := os.environ.get("MEMORY_API_BASE_URL"):
            return url
    
    # Auto-detect based on execution context
    context = get_execution_context()
    if context == "docker":
        return f"http://{service_name}:{port}"
    else:
        return f"http://127.0.0.1:{port}"


# Pre-resolved URLs for common services (can be imported directly)
API_BASE_URL = resolve_service_url("l9-api", 8000)
MCP_MEMORY_URL = resolve_service_url("l9-mcp-memory", 9002)
POSTGRES_URL = resolve_service_url("l9-postgres", 5432)
REDIS_URL = resolve_service_url("l9-redis", 6379)
NEO4J_URL = resolve_service_url("l9-neo4j", 7687)

# DEPRECATED: Keep for backwards compatibility, but points to MCP Memory now
MEMORY_API_BASE_URL = MCP_MEMORY_URL  # l9-memory-api:8080 is DEPRECATED
