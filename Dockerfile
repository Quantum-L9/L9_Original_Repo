# =============================================================================
# L9 API Dockerfile - PRODUCTION & DEVELOPMENT
# =============================================================================
# Version: 4.0.0
# Created: 2026-01-31
# Purpose: Consolidated Dockerfile for L9 API with multi-stage builds
#
# STAGES:
#   - base: Common dependencies and user setup
#   - development: Hot-reload friendly, includes dev tools
#   - production: Optimized, immutable, security-hardened
#
# USAGE:
#   Development:
#     docker build --target development -t l9-api:dev .
#
#   Production:
#     docker build --target production \
#       --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
#       --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#       --build-arg VERSION=4.0.0 \
#       -t l9-api:4.0.0 .
# =============================================================================

# =============================================================================
# BASE STAGE - Common dependencies
# =============================================================================
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    L9_CONTAINER_ENV=true

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 l9user && \
    mkdir -p /app/data/.l9/gmail/attachments && \
    chown -R l9user:l9user /app

# =============================================================================
# DEVELOPMENT STAGE - Hot-reload friendly
# =============================================================================
FROM base AS development

# Copy requirements first (layer caching optimization)
COPY requirements-docker.txt /app/

# Install Python dependencies (includes dev tools)
# NOTE: Install CPU-only PyTorch FIRST to avoid 3GB+ CUDA dependencies
# sentence-transformers depends on torch, but we don't need GPU support
RUN python -m pip install -U pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-docker.txt

# Copy application code (will be overridden by volume mounts in dev)
COPY --chown=l9user:l9user . /app/

USER l9user

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# PRODUCTION STAGE - Immutable, optimized
# =============================================================================
FROM base AS production

# Build arguments for image metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=4.0.0

# Image metadata (OCI standard)
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="QuantumAI Partners" \
      org.opencontainers.image.url="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.source="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="L9 API" \
      org.opencontainers.image.description="L9 Secure AI OS - Main API Server" \
      com.l9.component="api" \
      com.l9.layer="application"

# Copy requirements first (layer caching optimization)
COPY requirements-docker.txt /app/

# Install Python dependencies (production only, no dev tools)
# NOTE: Install CPU-only PyTorch FIRST to avoid 3GB+ CUDA dependencies
# sentence-transformers depends on torch, but we don't need GPU support
RUN python -m pip install -U pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-docker.txt && \
    pip cache purge

# Copy application code
COPY --chown=l9user:l9user . /app/

# Validation: Ensure critical environment variables are set at runtime
# (We check files exist here, actual secret validation happens in healthcheck)
RUN test -f /app/api/server.py || (echo "ERROR: api/server.py not found" && exit 1) && \
    test -f /app/requirements-docker.txt || (echo "ERROR: requirements-docker.txt not found" && exit 1)

USER l9user

EXPOSE 8000

# Production healthcheck (stricter timing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no --reload)
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--log-level", "info"]
