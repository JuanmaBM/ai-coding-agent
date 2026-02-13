#!/bin/bash

echo "🧹 Cleaning up local environment..."

podman stop rabbitmq-local ollama-local 2>/dev/null || true
podman rm rabbitmq-local ollama-local 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "To remove data volumes:"
echo "  podman volume rm ollama-data"

