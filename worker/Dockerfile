# Multi-stage Dockerfile for AI Agent Worker

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (git is needed for GitPython)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY *.py .
COPY modes/ ./modes/
COPY git/ ./git/

# Create workspace directory
RUN mkdir -p /tmp/workspace

# Run as non-root user for security (optional, commented for now)
# RUN useradd -m -u 1000 worker && chown -R worker:worker /app /tmp/workspace
# USER worker

# Health check (will be implemented in later iterations)
# HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
#   CMD python -c "import sys; sys.exit(0)"

# Run the worker
CMD ["python", "-u", "main.py"]

