# =============================================================================
# L9 Docker Image for Kubernetes Deployment (C1)
# =============================================================================
# Version: 2.0.0 - Production-ready with all dependencies
# Target: C1 server (8GB RAM, 4 vCPU)
#
# Build from repo root:
#   docker build -f deploy/k8s/c1/Dockerfile -t l9-api:latest .
#
# Or with the build script:
#   ./deploy/k8s/c1/scripts/build-images.sh
# =============================================================================

# =============================================================================
# Stage 1: Builder - Install all dependencies
# =============================================================================
FROM python:3.12-slim AS builder

# Build arguments for labels
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

WORKDIR /build

# Install build dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the PRODUCTION requirements (all deps, no dev tools)
# First try c1-specific, fallback to root
COPY deploy/k8s/c1/requirements-production.txt requirements-production.txt
COPY requirements.txt requirements-fallback.txt

# Install Python dependencies to /install directory
# Use production requirements (excludes playwright, dev tools)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --prefix=/install --no-warn-script-location -r requirements-production.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

# Labels
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="L9 Team" \
      org.opencontainers.image.url="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.source="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="L9 API" \
      org.opencontainers.image.description="L9 Agentic Intelligence Platform - Production Image"

# Security: Create non-root user
RUN groupadd -r l9 -g 1000 && useradd -r -u 1000 -g l9 -m -s /bin/bash l9

WORKDIR /app

# Install runtime dependencies only (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy L9 codebase - ALL required modules
COPY --chown=l9:l9 core/ ./core/
COPY --chown=l9:l9 memory/ ./memory/
COPY --chown=l9:l9 orchestration/ ./orchestration/
COPY --chown=l9:l9 runtime/ ./runtime/
COPY --chown=l9:l9 api/ ./api/
COPY --chown=l9:l9 config/ ./config/
COPY --chown=l9:l9 agents/ ./agents/
COPY --chown=l9:l9 services/ ./services/
COPY --chown=l9:l9 tools/ ./tools/
COPY --chown=l9:l9 workers/ ./workers/
COPY --chown=l9:l9 orchestrators/ ./orchestrators/
COPY --chown=l9:l9 telemetry/ ./telemetry/
COPY --chown=l9:l9 world_model/ ./world_model/
COPY --chown=l9:l9 workflows/ ./workflows/
COPY --chown=l9:l9 clients/ ./clients/
COPY --chown=l9:l9 adapters/ ./adapters/
COPY --chown=l9:l9 simulation/ ./simulation/

# Copy private configs if they exist (will fail silently if not present)
COPY --chown=l9:l9 private/ ./private/ 2>/dev/null || true

# Copy SQL migrations for memory substrate initialization
COPY --chown=l9:l9 migrations/ ./migrations/

# Copy prompts and kernels
COPY --chown=l9:l9 prompts/ ./prompts/ 2>/dev/null || true

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/data/.l9 && \
    chown -R l9:l9 /app

# Switch to non-root user
USER l9

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    L9_CONTAINER_ENV=true \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 9000

# Default command - FastAPI via uvicorn
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
