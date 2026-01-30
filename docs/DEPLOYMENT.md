# Deployment Guide

Complete step-by-step guide for deploying the AI Coding Agent with Git, LLM, and GitHub integration.

## Prerequisites

- Minikube installed
- kubectl configured
- Helm 3.x
- Docker or Podman

## Step 1: Start Minikube

```bash
minikube start --cpus 2 --memory 4096
minikube addons enable metrics-server
minikube addons enable ingress
```

## Step 2: Create Namespace

```bash
kubectl apply -f k8s/base/namespace.yaml
```

## Step 3: Build Worker Image

```bash
eval $(minikube docker-env)
cd worker
docker build -t ai-agent-worker:latest .
cd ..
```

## Step 4: Deploy RabbitMQ

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install rabbitmq bitnami/rabbitmq \
  -f k8s/base/rabbitmq-values.yaml \
  -n ai-agent \
  --set auth.password=DevPassword123 \
  --wait --timeout=5m
```

## Step 5: Deploy KEDA

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace \
  --wait
```

## Step 6: Create Secrets

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

## Step 7: Deploy Configuration

```bash
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/keda-auth.yaml
```

## Step 8: Deploy Ollama (LLM Service)

```bash
kubectl apply -f k8s/base/ollama-deployment.yaml

# Wait for Ollama to be ready
kubectl wait --for=condition=ready pod -l app=ollama -n ai-agent --timeout=120s

# Check model download progress
kubectl logs -f job/ollama-pull-model -n ai-agent
```

**Note:** Model download can take 5-10 minutes

## Step 9: Create GitHub Token Secret

```bash
# Replace with your GitHub token
kubectl create secret generic github-credentials \
  --from-literal=token=ghp_YOUR_GITHUB_TOKEN \
  -n ai-agent
```

To get a GitHub token:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scope: `repo`
4. Copy the token

## Step 10: Deploy Worker

```bash
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/scaledobject.yaml
```

## Step 11: Verify Deployment

```bash
kubectl get all -n ai-agent
```

Expected output:
- RabbitMQ: 1/1 Running
- Ollama: 1/1 Running  
- Worker: 0/0 (scaled to zero by KEDA)

```bash
# Check secrets
kubectl get secrets -n ai-agent
```

Should show: `rabbitmq-credentials`, `keda-rabbitmq-secret`, `github-credentials`

## Step 12: Test Plan Mode

### Prepare Test

```bash
# Port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 &

# Install test dependencies
cd scripts
pip install -r requirements.txt
```

### Run Test

```bash
# Test with your GitHub repository
python test-iteration3.py \
  --repo-url https://github.com/YOUR_USERNAME/YOUR_REPO \
  --issue-id 1
```

### Monitor Execution

```bash
# Watch pods scale (in another terminal)
kubectl get pods -n ai-agent -w

# View worker logs
kubectl logs -f -n ai-agent -l app=ai-agent-worker
```

### Expected Results

After 2-5 minutes:
- ✓ Worker scaled from 0→1
- ✓ Repository cloned
- ✓ Issue analyzed
- ✓ Plan generated with Ollama
- ✓ Draft PR created on GitHub
- ✓ Comment posted on issue
- ✓ Labels added: `ai-agent`, `plan-pending`
- ✓ Worker scaled back to 0

## Cleanup

```bash
helm uninstall rabbitmq -n ai-agent
helm uninstall keda -n keda
kubectl delete namespace ai-agent keda
minikube stop
```

## Troubleshooting

### Worker Not Scaling

```bash
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent
kubectl logs -n keda -l app=keda-operator
```

### RabbitMQ Connection Issues

```bash
kubectl logs -n ai-agent -l app=rabbitmq
kubectl get svc -n ai-agent
```

### View Worker Logs

```bash
kubectl logs -f -n ai-agent -l app=ai-agent-worker
```
