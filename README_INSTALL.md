# Installation Instructions

## Quick Install (Automated)

Run the installation script to set up everything automatically:

```bash
chmod +x install.sh
./install.sh
```

This script will:
1. ✓ Check prerequisites (minikube, kubectl, helm, docker)
2. ✓ Start Minikube cluster (2 CPUs, 4GB RAM)
3. ✓ Enable required addons (metrics-server, ingress)
4. ✓ Create namespace `ai-agent`
5. ✓ Build worker Docker image
6. ✓ Add Helm repositories
7. ✓ Deploy RabbitMQ
8. ✓ Install KEDA
9. ✓ Create all secrets
10. ✓ Deploy Ollama (LLM service)
11. ✓ Deploy worker
12. ✓ Configure KEDA autoscaling

**Time:** ~5-10 minutes (depending on your internet connection)

## Configure GitHub Token

After installation, configure your GitHub token:

```bash
chmod +x scripts/setup-github-token.sh
./scripts/setup-github-token.sh ghp_YOUR_GITHUB_TOKEN
```

To get a token:
1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `repo`
4. Copy the token

## Verify Installation

```bash
# Check all components
kubectl get all -n ai-agent

# Check secrets
kubectl get secrets -n ai-agent
```

Expected output:
- RabbitMQ: 1/1 Running
- Ollama: 1/1 Running
- Worker: 0/0 (scaled to zero - this is normal!)
- Secrets: rabbitmq-credentials, keda-rabbitmq-secret, github-credentials

## Test the System

```bash
# Port-forward RabbitMQ
kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 &

# Install test dependencies
cd scripts
pip install -r requirements.txt

# Run test (replace with your repo and issue)
python test-iteration3.py \
  --repo-url https://github.com/YOUR_USERNAME/YOUR_REPO \
  --issue-id 1
```

Monitor the process:

```bash
# Watch pods scale up
kubectl get pods -n ai-agent -w

# View logs
kubectl logs -f -n ai-agent -l app=ai-agent-worker
```

## Uninstall

To remove everything:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

This will:
- Delete namespace `ai-agent` (all resources)
- Uninstall KEDA
- Optionally stop/delete Minikube

## Manual Installation

If you prefer manual control, follow the complete guide:  
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Verify Worker Image

If the worker isn't starting, verify the image is available:

```bash
make verify
```

Or manually:

```bash
chmod +x scripts/verify-image.sh
./scripts/verify-image.sh
```

## Rebuild Worker

If you make changes to the worker code:

```bash
make rebuild
```

This will:
1. Build the image in Minikube's Docker
2. Verify the image exists
3. Restart the deployment
4. Wait for rollout to complete

## Troubleshooting

### Worker image not found

```bash
# Manually build in Minikube environment
eval $(minikube docker-env)
cd worker
docker build -t ai-agent-worker:latest .
docker images | grep ai-agent-worker

# Verify it's there
cd ..
make verify
```

### Installation fails

```bash
# Check Minikube status
minikube status

# View detailed logs
kubectl get events -n ai-agent --sort-by='.lastTimestamp'
```

### Worker not starting

```bash
# Check deployment
kubectl describe deployment ai-agent-worker -n ai-agent

# Check if image exists
minikube ssh docker images | grep ai-agent-worker
```

### Ollama model download stuck

```bash
# Check job logs
kubectl logs -f job/ollama-pull-model -n ai-agent

# If stuck, delete and recreate
kubectl delete job ollama-pull-model -n ai-agent
kubectl apply -f k8s/base/ollama-deployment.yaml
```

## Next Steps

After successful installation:

1. **Configure GitHub token** (if not done)
2. **Test with a real issue** (see above)
3. **Monitor the execution** (kubectl logs)
4. **Check GitHub** (draft PR should be created)

For detailed documentation, see:
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Complete deployment guide
- [docs/ITERATION_3.md](docs/ITERATION_3.md) - Technical details
- [STATUS.md](STATUS.md) - Current implementation status

