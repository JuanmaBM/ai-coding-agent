# Quick Start Guide

Get the AI Coding Agent (Iterations 1 & 2) running in less than 10 minutes!

## Prerequisites

- Minikube installed
- kubectl configured  
- Helm 3.x installed
- Docker or Podman

## Quick Deploy with Makefile

```bash
# Full automated setup
make all

# Test the deployment
make test

# Watch logs
make logs

# Cleanup
make clean
```

## Manual Deployment

### 1. Start Minikube

```bash
minikube start --cpus 2 --memory 4096
minikube addons enable metrics-server ingress
```

### 2. Build Worker Image

```bash
eval $(minikube docker-env)
cd worker && docker build -t ai-agent-worker:latest .
cd ..
```

### 3. Deploy Infrastructure

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

### 4. Configure Secrets

```bash
kubectl create secret generic rabbitmq-credentials \
  --from-literal=username=admin \
  --from-literal=password=DevPassword123 \
  -n ai-agent

kubectl create secret generic keda-rabbitmq-secret \
  --from-literal=host="amqp://admin:DevPassword123@rabbitmq.ai-agent.svc.cluster.local:5672/" \
  -n ai-agent
```

### 5. Deploy Worker

```bash
kubectl apply -f k8s/base/keda-auth.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/scaledobject.yaml
```

### 6. Verify

```bash
kubectl get pods -n ai-agent
kubectl get scaledobject -n ai-agent
```

## Test the Setup

### Publish Test Messages

```bash
# Port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 &

# Run test script
cd scripts
pip install -r requirements.txt
python test-queue.py --count 5 --delay 2
```

### Watch Auto-Scaling

```bash
# In another terminal
kubectl get pods -n ai-agent -w
```

You should see:
1. Worker pods scaling from 0→5
2. Pods processing messages
3. Pods scaling back to 0 after ~30 seconds

### View Worker Logs

```bash
kubectl logs -n ai-agent -l app=ai-agent-worker -f
```

Expected output (JSON logs):
```json
{"event": "task_received", "repo_url": "https://github.com/example/test-repo", ...}
{"event": "processing", "msg": "Analyzing repository..."}
{"event": "task_completed", "duration_seconds": 3}
```

## Access RabbitMQ Management UI

```bash
kubectl port-forward -n ai-agent svc/rabbitmq 15672:15672
```

Open http://localhost:15672
- Username: `admin`
- Password: `DevPassword123`

## Troubleshooting

### Pods Not Scaling

```bash
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent
kubectl logs -n keda -l app=keda-operator
```

### Worker Failing

```bash
kubectl describe deployment ai-agent-worker -n ai-agent
kubectl logs -n ai-agent -l app=ai-agent-worker
```

### RabbitMQ Issues

```bash
kubectl get pods -n ai-agent -l app.kubernetes.io/name=rabbitmq
kubectl logs -n ai-agent -l app.kubernetes.io/name=rabbitmq
```

## Cleanup

```bash
# Using Makefile
make clean

# Or manually
helm uninstall rabbitmq -n ai-agent
helm uninstall keda -n keda
kubectl delete namespace ai-agent keda
minikube stop
```

## What's Deployed?

✅ **Iteration 1: Infrastructure**
- RabbitMQ message broker
- KEDA autoscaler  
- Kubernetes namespace and configs

✅ **Iteration 2: Hello World Worker**
- Python worker with FastStream
- Auto-scales 0→N based on queue
- Logs task processing (JSON format)

## Next Steps

See [README.md](README.md) for the full technical design and roadmap.

## Useful Commands

```bash
# View all resources
kubectl get all -n ai-agent

# Restart worker
kubectl rollout restart deployment/ai-agent-worker -n ai-agent

# Scale manually
kubectl scale deployment ai-agent-worker -n ai-agent --replicas=3

# Check KEDA metrics
kubectl get hpa -n ai-agent

# Delete and redeploy worker
kubectl delete deployment ai-agent-worker -n ai-agent
kubectl apply -f k8s/base/deployment.yaml
```
