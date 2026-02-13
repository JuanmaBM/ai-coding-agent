# Multi-stage Dockerfile for AI Agent Worker

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files for installation
COPY ../../pyproject.toml ./pyproject.toml
COPY . ./src/worker/

# Install package with dependencies
RUN pip install --no-cache-dir --user .

# Install aider using official installer
RUN curl -LsSf https://aider.chat/install.sh | sh

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.aider /root/.aider

# Make sure scripts are usable
ENV PATH=/root/.local/bin:$PATH

# Copy installed package
COPY --from=builder /build/src/worker /app/worker

# Create workspace directory
RUN mkdir -p /tmp/workspace

# Run the worker as module
CMD ["python", "-u", "-m", "worker.main"]
