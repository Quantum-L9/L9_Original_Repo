# =============================================================================
# L9 API Dockerfile (Production)
# Version: 2.0.0 - Matches VPS deployment
#
# This is the canonical Dockerfile for L9 API on VPS.
# Used by: docker-compose.yml → l9-api service
# =============================================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    L9_CONTAINER_ENV=true

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy all application code
COPY . /app

# Install Python dependencies (Docker-optimized, excludes playwright)
RUN python -m pip install -U pip setuptools wheel \
    && pip install --no-cache-dir -r requirements-docker.txt

# Create non-root user for security
RUN useradd -m -u 1000 l9user

# Create data directory for container-safe path (email_agent, etc.)
# email_agent.config uses /app/data/.l9/gmail when /app/data exists
RUN mkdir -p /app/data/.l9/gmail/attachments && chown -R l9user:l9user /app/data

USER l9user

EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]

