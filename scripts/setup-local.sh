#!/bin/bash
set -e

echo "🚀 Setting up local development environment..."
echo ""

# Check if containers are already running
if podman ps | grep -q rabbitmq-local; then
  echo "✓ RabbitMQ already running"
else
  echo "Starting RabbitMQ..."
  podman run -d --name rabbitmq-local \
    -p 5672:5672 \
    -p 15672:15672 \
    -e RABBITMQ_DEFAULT_USER=admin \
    -e RABBITMQ_DEFAULT_PASS=DevPassword123 \
    rabbitmq:3-management
  echo "✓ RabbitMQ started (port 5672, UI at http://localhost:15672)"
fi

if podman ps | grep -q ollama-local; then
  echo "✓ Ollama already running"
else
  echo "Starting Ollama..."
  podman run -d --name ollama-local \
    -p 11434:11434 \
    -v ollama-data:/root/.ollama \
    ollama/ollama

  echo "Waiting for Ollama to start..."
  sleep 5

  echo "Pulling qwen2.5-coder:1.5b model..."
  podman exec ollama-local ollama pull qwen2.5-coder:1.5b
  echo "✓ Ollama started and model downloaded"
fi

echo ""
echo "✅ Local environment ready!"
echo ""
echo "RabbitMQ Management: http://localhost:15672 (admin/password)"
echo "Ollama API: http://localhost:11434"
echo ""
echo "Next steps:"
echo "  cd worker"
echo "  python -m venv .venv"
echo "  source .venv/bin/activate"
echo "  pip install -e .  # Install as editable package"
echo "  cp .env.example .env"
echo "  # Edit .env with your GitHub token"
echo "  python main.py"
