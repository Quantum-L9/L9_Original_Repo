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

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP memory server code
COPY mcp_memory/ /app/mcp_memory/

# Copy core schemas (needed for PacketEnvelope)
COPY core/schemas/ /app/core/schemas/

# Copy memory module (needed for substrate)
COPY memory/ /app/memory/

# Copy config (needed for settings)
COPY config/ /app/config/

# Set Python path
ENV PYTHONPATH=/app

# Expose MCP port
EXPOSE 9002

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -f http://localhost:9002/health || exit 1

# Run MCP server
CMD ["uvicorn", "mcp_memory.src.main:app", "--host", "0.0.0.0", "--port", "9002"]
