# Deployment Guide - AI Coding Agent POC

This guide covers deployment of Iterations 1 and 2: Infrastructure setup and Hello World worker.

## Prerequisites

- **Minikube**: Version 1.32+ installed
- **kubectl**: Configured to work with Minikube
- **Helm**: Version 3.0+ installed
- **Docker**: For building worker images

## Step 1: Initialize Minikube Cluster

Start Minikube with appropriate resources:

```bash
# Start Minikube with 4GB RAM and 2 CPUs (auto-detects best driver)
minikube start --cpus 2 --memory 4096

# Enable required addons
minikube addons enable metrics-server
minikube addons enable ingress

# Verify cluster is running
kubectl cluster-info
```

Configure Docker environment to use Minikube's Docker daemon (for local image builds):

```bash
eval $(minikube docker-env)
```

## Step 2: Create Namespace

Create the dedicated namespace for the AI agent:

```bash
kubectl apply -f k8s/base/namespace.yaml

# Verify namespace creation
kubectl get namespace ai-agent
```

## Step 3: Deploy RabbitMQ

Install RabbitMQ using Helm with Bitnami chart:

```bash
# Add Bitnami repository (if not already added)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install RabbitMQ with custom values
helm install rabbitmq bitnami/rabbitmq \
  -f k8s/base/rabbitmq-values.yaml \
  -n ai-agent \
  --set auth.password=StrongPassword123

# Wait for RabbitMQ to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=rabbitmq -n ai-agent --timeout=300s
```

Get RabbitMQ credentials:

```bash
# Get the password (if auto-generated)
kubectl get secret --namespace ai-agent rabbitmq -o jsonpath="{.data.rabbitmq-password}" | base64 -d
echo
```

## Step 4: Create RabbitMQ Credentials Secret

Create a Kubernetes secret with RabbitMQ credentials for the worker:

```bash
kubectl create secret generic rabbitmq-credentials \
  --from-literal=username=admin \
  --from-literal=password=StrongPassword123 \
  -n ai-agent
```

## Step 5: Update KEDA Authentication

Update the KEDA authentication secret with the actual RabbitMQ password:

```bash
# Edit keda-auth.yaml and replace CHANGEME with your password
# Or apply directly:
kubectl create secret generic keda-rabbitmq-secret \
  --from-literal=host="amqp://admin:StrongPassword123@rabbitmq.ai-agent.svc.cluster.local:5672/" \
  -n ai-agent \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply the TriggerAuthentication
kubectl apply -f k8s/base/keda-auth.yaml
```

## Step 6: Deploy KEDA

Install KEDA using Helm:

```bash
# Add KEDA Helm repository
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

# Install KEDA
helm install keda kedacore/keda --namespace keda --create-namespace

# Wait for KEDA to be ready
kubectl wait --for=condition=ready pod -l app=keda-operator -n keda --timeout=300s
```

## Step 7: Apply Configuration

Apply the ConfigMap for worker configuration:

```bash
kubectl apply -f k8s/base/configmap.yaml
```

## Step 8: Build Worker Docker Image

Build the worker Docker image in Minikube's Docker environment:

```bash
# Make sure you're using Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image
cd worker
docker build -t ai-agent-worker:latest .

# Verify image was built
docker images | grep ai-agent-worker
```

## Step 9: Deploy Worker

Deploy the worker deployment:

```bash
cd ..
kubectl apply -f k8s/base/deployment.yaml

# Note: You should see 0 pods initially (KEDA scaling)
kubectl get pods -n ai-agent
```

## Step 10: Deploy KEDA ScaledObject

Apply the ScaledObject to enable autoscaling:

```bash
kubectl apply -f k8s/base/scaledobject.yaml

# Verify ScaledObject is configured
kubectl get scaledobject -n ai-agent
```

## Step 11: Test the Setup

### Option A: Port-forward RabbitMQ and use test script

```bash
# In one terminal, port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 15672:15672

# In another terminal, install dependencies and run test script
cd scripts
pip install -r requirements.txt
python test-queue.py --count 3 --delay 2
```

### Option B: Access RabbitMQ Management UI

```bash
# Port-forward the management interface
kubectl port-forward -n ai-agent svc/rabbitmq 15672:15672

# Open browser to http://localhost:15672
# Login: admin / StrongPassword123
# Publish messages manually through the UI
```

## Step 12: Monitor KEDA Scaling

Watch pods scale up and down:

```bash
# Watch pods in real-time
kubectl get pods -n ai-agent -w

# Check KEDA metrics
kubectl get hpa -n ai-agent

# Check ScaledObject status
kubectl describe scaledobject ai-agent-worker-scaler -n ai-agent
```

## Step 13: View Worker Logs

Check that workers are processing messages correctly:

```bash
# Get logs from worker pods
kubectl logs -n ai-agent -l app=ai-agent-worker --tail=50 -f

# Expected output: JSON structured logs showing task processing
```

## Verification Checklist

- [ ] Minikube cluster is running with sufficient resources
- [ ] Namespace `ai-agent` exists
- [ ] RabbitMQ pod is running and healthy
- [ ] KEDA operator is running in `keda` namespace
- [ ] Worker image is built (`ai-agent-worker:latest`)
- [ ] ScaledObject is active
- [ ] Publishing messages triggers pod creation (0→1→N)
- [ ] Worker pods process messages and log output
- [ ] Pods scale to zero after queue is empty (after cooldown period)

## Troubleshooting

### RabbitMQ not starting

```bash
# Check pod status
kubectl describe pod -n ai-agent -l app.kubernetes.io/name=rabbitmq

# Check persistent volume
kubectl get pvc -n ai-agent
```

### KEDA not scaling

```bash
# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator

# Verify trigger authentication
kubectl get triggerauthentication -n ai-agent -o yaml

# Check if queue has messages
# Access management UI and verify queue "agent-tasks" exists
```

### Worker pods not starting

```bash
# Check deployment status
kubectl describe deployment ai-agent-worker -n ai-agent

# Check for image pull issues
kubectl describe pod -n ai-agent -l app=ai-agent-worker

# Verify secrets exist
kubectl get secrets -n ai-agent
```

### Worker crashing

```bash
# Check logs for errors
kubectl logs -n ai-agent -l app=ai-agent-worker --previous

# Common issues:
# - Wrong RabbitMQ credentials
# - Queue name mismatch
# - Network connectivity to RabbitMQ
```

## Cleanup

To tear down the entire setup:

```bash
# Delete all resources in ai-agent namespace
kubectl delete namespace ai-agent

# Uninstall KEDA
helm uninstall keda -n keda
kubectl delete namespace keda

# Stop Minikube
minikube stop

# Or delete the entire cluster
minikube delete
```

## Next Steps

Once Iterations 1 and 2 are validated:

- Proceed to Iteration 3: Git & LLM Integration
- Add real GitHub API integration
- Implement Ollama for code generation
- Extend worker with git operations

