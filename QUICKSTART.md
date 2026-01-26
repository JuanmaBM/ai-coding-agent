# Quick Start Guide

Get the AI Coding Agent running in less than 10 minutes!

## Prerequisites

Ensure you have these tools installed:
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) (v1.32+)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/) (v3.0+)
- [Docker](https://docs.docker.com/get-docker/)
- [Python 3.11+](https://www.python.org/downloads/)
- [Make](https://www.gnu.org/software/make/) (optional, for convenience)

## Quick Deploy with Makefile

If you have `make` installed, you can deploy everything with a single command:

```bash
# Full automated setup (Iterations 1 & 2)
make all

# Test the deployment
make test

# Watch logs
make logs
```

## Manual Deployment

### Step 1: Start Minikube

```bash
minikube start --cpus 2 --memory 4096
minikube addons enable metrics-server ingress
```

### Step 2: Point Docker to Minikube

```bash
eval $(minikube docker-env)
```

### Step 3: Build Worker Image

```bash
cd worker
docker build -t ai-agent-worker:latest .
cd ..
```

### Step 4: Deploy Infrastructure

```bash
# Add Helm repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

# Create namespace
kubectl apply -f k8s/base/namespace.yaml

# Install RabbitMQ
helm install rabbitmq bitnami/rabbitmq \
  -f k8s/base/rabbitmq-values.yaml \
  -n ai-agent \
  --set auth.password=DevPassword123 \
  --wait

# Install KEDA
helm install keda kedacore/keda --namespace keda --create-namespace --wait
```

### Step 5: Configure Secrets

```bash
# RabbitMQ credentials
kubectl create secret generic rabbitmq-credentials \
  --from-literal=username=admin \
  --from-literal=password=DevPassword123 \
  -n ai-agent

# KEDA authentication
kubectl create secret generic keda-rabbitmq-secret \
  --from-literal=host="amqp://admin:DevPassword123@rabbitmq.ai-agent.svc.cluster.local:5672/" \
  -n ai-agent
```

### Step 6: Deploy Worker

```bash
kubectl apply -f k8s/base/keda-auth.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/scaledobject.yaml
```

### Step 7: Verify Deployment

```bash
# Check all pods are running (RabbitMQ should be running, worker at 0 replicas)
kubectl get pods -n ai-agent

# Check KEDA is installed
kubectl get pods -n keda
```

## Testing the Setup

### Publish Test Messages

```bash
# Port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 &

# Install dependencies and run test script
cd scripts
pip install -r requirements.txt
python test-queue.py --count 5 --delay 2
```

### Watch Auto-Scaling in Action

In another terminal:

```bash
kubectl get pods -n ai-agent -w
```

You should see:
1. Worker pods scaling from 0→5 (one per message)
2. Pods processing messages (check logs)
3. Pods scaling back to 0 after ~30 seconds of inactivity

### View Worker Logs

```bash
kubectl logs -n ai-agent -l app=ai-agent-worker -f
```

Expected output:
```json
{"event": "task_received", "repo_url": "https://github.com/example/test-repo", ...}
{"event": "processing", "msg": "Analyzing repository..."}
{"event": "task_completed", "duration_seconds": 3}
```

## Access RabbitMQ Management UI

```bash
kubectl port-forward -n ai-agent svc/rabbitmq 15672:15672
```

Open http://localhost:15672 in your browser:
- Username: `admin`
- Password: `DevPassword123`

## Troubleshooting

### Pods not scaling

```bash
# Check ScaledObject status
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent

# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator
```

### Worker failing to start

```bash
# Check deployment
kubectl describe deployment ai-agent-worker -n ai-agent

# Check logs
kubectl logs -n ai-agent -l app=ai-agent-worker
```

### RabbitMQ connection issues

```bash
# Verify RabbitMQ is running
kubectl get pods -n ai-agent -l app.kubernetes.io/name=rabbitmq

# Check service
kubectl get svc -n ai-agent rabbitmq
```

## Cleanup

```bash
# Using Makefile
make clean

# Or manually
helm uninstall rabbitmq -n ai-agent
helm uninstall keda -n keda
kubectl delete namespace ai-agent
kubectl delete namespace keda
```
