# MCP Memory Server Dockerfile
# L9 Secure AI OS - Memory Protocol Server
# Version: 1.0.0
#
# This is the ONLY supported memory path for Cursor IDE integration.
# l9-memory-api (port 8080) is DEPRECATED.

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy MCP-specific requirements (NOT root requirements.txt)
COPY mcp_memory/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP memory server code
COPY mcp_memory/ /app/mcp_memory/

# Copy entire core/ (many memory imports depend on core modules)
COPY core/ /app/core/

# Copy memory module (needed for substrate)
COPY memory/ /app/memory/

# Copy config (needed for settings)
COPY config/ /app/config/

# Copy telemetry (needed for memory metrics)
COPY telemetry/ /app/telemetry/

# Copy private kernels (needed for governance context)
COPY private/ /app/private/

# Copy SQL migrations (needed for MigrationRunner startup)
COPY migrations/ /app/migrations/

# Set Python path (include /app/mcp_memory for 'from src.xxx' imports)
ENV PYTHONPATH=/app:/app/mcp_memory

# Expose MCP port
EXPOSE 9002

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -f http://localhost:9002/health || exit 1

# Run MCP server
CMD ["uvicorn", "mcp_memory.src.main:app", "--host", "0.0.0.0", "--port", "9002"]
