FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    build-essential \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY symbolic_computation/ ./symbolic_computation/
COPY tests/ ./tests/
COPY .env.example .env

# Create logs directory
RUN mkdir -p /app/logs

# Set Python path
ENV PYTHONPATH=/app

# NOTE: Tests disabled - this service is not actively used
# TODO: Review and re-enable symbolic_computation service when needed
# See TODO.md for tracking
#
# Original command (disabled):
# CMD ["python", "-m", "pytest", "tests/"]
CMD ["echo", "Symbolic computation service is disabled. See TODO.md"]
