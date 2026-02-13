# ==========================================
# Base Stage: System & Global Dependencies
# ==========================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir aider-chat

# ==========================================
# Project Stage: Application Code
# ==========================================
COPY pyproject.toml .

COPY src/worker/ ./src/worker/

RUN pip install --no-cache-dir .

RUN mkdir -p /tmp/workspace

CMD ["python", "-u", "-m", "worker.main"]
