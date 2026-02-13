# Deployment Guide

## Table of Contents

- [Local Development](#local-development)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.11+
- Podman or Docker
- Ollama installed locally
- Git

### Step 1: Start Local Services

```bash
chmod +x scripts/setup-local.sh
./scripts/setup-local.sh
```

This starts:

- **RabbitMQ** on port 5672 (Management UI: <http://localhost:15672>, user: admin, password: password)
- **Ollama** on port 11434

### Step 2: Pull LLM Model

```bash
ollama pull qwen2.5-coder:14b
```

Verify it works:

```bash
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5-coder:14b", "prompt": "Hello", "stream": false}'
```

### Step 3: Install Worker

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install as editable package
pip install -e .
```

### Step 4: Configure Environment

Create a `.env` file in the project root or export the variables:

```bash
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=admin
export RABBITMQ_PASSWORD=password
export RABBITMQ_QUEUE=agent-tasks
export GITHUB_TOKEN=ghp_your_token_here
export LLM_MODEL=qwen2.5-coder:14b
export OLLAMA_BASE_URL=http://localhost:11434
export GIT_CLIENT=github
export LOG_LEVEL=DEBUG
```

### Step 5: Run Worker

```bash
python -m worker.main
```

You should see:

```
INFO - FastStream app starting...
INFO - agent-tasks | - `ProcessTask` waiting for messages
```

### Step 6: Test

In another terminal:

```bash
cd scripts
pip install -r requirements.txt

python test-iteration3.py \
  --repo-url https://github.com/your-user/your-repo \
  --issue-id 1 \
  --mode quickfix
```

Monitor the worker logs in the first terminal.

### Cleanup

```bash
./scripts/cleanup-local.sh
```

---

## Kubernetes Deployment

### Prerequisites

- Minikube installed
- kubectl configured
- Helm 3.x
- Podman or Docker

### Step 1: Start Minikube

```bash
minikube start --cpus 4 --memory 8192
minikube addons enable metrics-server
minikube addons enable ingress
```

### Step 2: Automated Deployment

```bash
chmod +x install.sh
./install.sh
```

This script automatically:

1. Creates namespace `ai-agent`
2. Deploys RabbitMQ
3. Installs KEDA for auto-scaling
4. Creates all required secrets
5. Deploys Ollama LLM service
6. Deploys the worker

### Step 3: Build and Load Worker Image

```bash
# Build the image
podman build -t localhost/ai-agent-worker:latest -f Dockerfile .

# Load into Minikube
podman save localhost/ai-agent-worker:latest -o /tmp/ai-agent-worker.tar
minikube image load /tmp/ai-agent-worker.tar
rm -f /tmp/ai-agent-worker.tar

# Restart deployment to use new image
kubectl rollout restart deployment/ai-agent-worker -n ai-agent
```

### Step 4: Configure GitHub Token

```bash
chmod +x scripts/setup-github-token.sh
./scripts/setup-github-token.sh ghp_your_token_here
```

Or manually:

```bash
kubectl create secret generic github-credentials \
  --from-literal=token=ghp_your_token_here \
  -n ai-agent \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 5: Verify Deployment

```bash
# Check all pods
kubectl get pods -n ai-agent

# Expected:
# rabbitmq-xxx     1/1  Running
# ollama-xxx       1/1  Running
# worker           0/0  (scaled to zero by KEDA)

# Check KEDA
kubectl get scaledobject -n ai-agent

# Check secrets
kubectl get secrets -n ai-agent
```

### Step 6: Test

```bash
# Port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 &

# Publish test message
cd scripts
python test-iteration3.py \
  --repo-url https://github.com/your-user/your-repo \
  --issue-id 1 \
  --mode quickfix
```

### Monitoring

```bash
# Watch pods scale up/down
kubectl get pods -n ai-agent -w

# View worker logs
kubectl logs -f -n ai-agent -l app=ai-agent-worker

# Check KEDA metrics
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent

# RabbitMQ Management UI
kubectl port-forward -n ai-agent svc/rabbitmq 15672:15672
# Open http://localhost:15672 (admin/DevPassword123)
```

### Rebuilding After Code Changes

```bash
make rebuild
```

Or manually:

```bash
podman build -t localhost/ai-agent-worker:latest -f Dockerfile .
podman save localhost/ai-agent-worker:latest -o /tmp/ai-agent-worker.tar
minikube image load /tmp/ai-agent-worker.tar
kubectl rollout restart deployment/ai-agent-worker -n ai-agent
```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace ai-agent
helm uninstall keda -n keda
kubectl delete namespace keda

# Stop Minikube
minikube stop

# Delete cluster entirely
minikube delete
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `RABBITMQ_HOST` | RabbitMQ hostname | `localhost` |
| `RABBITMQ_PORT` | RabbitMQ port | `5672` |
| `RABBITMQ_USER` | RabbitMQ username | `admin` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `password` |
| `RABBITMQ_VHOST` | RabbitMQ virtual host | `/` |
| `RABBITMQ_QUEUE` | Queue name | `agent-tasks` |
| `RABBITMQ_GRACEFUL_TIMEOUT` | Graceful shutdown timeout (seconds) | `300` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Required |
| `GIT_CLIENT` | Git provider (`github`) | `github` |
| `GIT_CLONE_DEPTH` | Shallow clone depth | `1` |
| `WORKSPACE_DIR` | Temp directory for git operations | `/tmp/workspace` |
| `LLM_PROVIDER` | LLM provider | `ollama` |
| `LLM_MODEL` | Model name | `qwen2.5-coder:14b` |
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `LOG_LEVEL` | Logging level | `INFO` |

### GitHub Token

Create a Personal Access Token at <https://github.com/settings/tokens> with scope: `repo`

### Kubernetes Resources

| Resource | File | Purpose |
|---|---|---|
| Namespace | `k8s/base/namespace.yaml` | Isolation |
| RabbitMQ | `k8s/base/rabbitmq-simple.yaml` | Message broker |
| KEDA Auth | `k8s/base/keda-auth.yaml` | KEDA authentication |
| ScaledObject | `k8s/base/scaledobject.yaml` | Auto-scaling config |
| ConfigMap | `k8s/base/configmap.yaml` | Worker configuration |
| Deployment | `k8s/base/deployment.yaml` | Worker pods |
| Ollama | `k8s/base/ollama-deployment.yaml` | LLM service |

---

## Troubleshooting

### Worker Not Scaling

```bash
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent
kubectl logs -n keda -l app=keda-operator
```

Common cause: KEDA can't authenticate to RabbitMQ. Recreate the secret:

```bash
kubectl delete secret keda-rabbitmq-secret -n ai-agent
kubectl create secret generic keda-rabbitmq-secret \
  --from-literal=host="amqp://admin:DevPassword123@rabbitmq.ai-agent.svc.cluster.local:5672/" \
  -n ai-agent
```

### Worker Image Not Found

```bash
# Verify image in Minikube
minikube image ls | grep ai-agent

# If not found, rebuild and load
podman build -t localhost/ai-agent-worker:latest -f Dockerfile .
podman save localhost/ai-agent-worker:latest -o /tmp/ai-agent-worker.tar
minikube image load /tmp/ai-agent-worker.tar
```

### GitHub API Errors (401/404)

```bash
# Verify token
kubectl get secret github-credentials -n ai-agent -o jsonpath='{.data.token}' | base64 -d

# Test token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### Ollama Not Responding

```bash
# Local
curl http://localhost:11434/api/tags

# Kubernetes
kubectl get pods -n ai-agent -l app=ollama
kubectl logs -n ai-agent -l app=ollama
```

### RabbitMQ Connection Refused

```bash
# Local
podman ps | grep rabbitmq

# Kubernetes
kubectl get pods -n ai-agent -l app=rabbitmq
kubectl logs -n ai-agent -l app=rabbitmq
```
