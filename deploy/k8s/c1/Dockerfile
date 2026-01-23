# =============================================================================
# L9 Docker Image for Kubernetes Deployment
# =============================================================================
# This Dockerfile builds the actual L9 codebase for K8s deployment
# Target: C1 server (8GB RAM, CPU only)
#
# Build: docker build -f Dockerfile.l9 -t l9:latest .
# Push:  docker tag l9:latest ghcr.io/igor-beylin/l9:latest
#        docker push ghcr.io/igor-beylin/l9:latest
# =============================================================================

FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
FROM python:3.12-slim

# Security: Run as non-root user
RUN groupadd -r l9 && useradd -r -g l9 l9

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy L9 codebase (selective - only what's needed for runtime)
COPY core/ ./core/
COPY memory/ ./memory/
COPY orchestration/ ./orchestration/
COPY runtime/ ./runtime/
COPY api/ ./api/
COPY config/ ./config/
COPY agents/ ./agents/
COPY services/ ./services/
COPY tools/ ./tools/
COPY workers/ ./workers/
COPY private/ ./private/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R l9:l9 /app

# Switch to non-root user
USER l9

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 9000

# Default command - runs FastAPI via uvicorn (api.server is the correct entrypoint)
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
