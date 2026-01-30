#!/bin/bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CPUS=4
MEMORY=8192
NAMESPACE="ai-agent"
RABBITMQ_PASSWORD="DevPassword123"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}AI Coding Agent - Installation${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}➜${NC} $1"
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

command -v minikube >/dev/null 2>&1 || { print_error "minikube is not installed. Aborting."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { print_error "kubectl is not installed. Aborting."; exit 1; }
command -v helm >/dev/null 2>&1 || { print_error "helm is not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || command -v podman >/dev/null 2>&1 || { print_error "docker or podman is not installed. Aborting."; exit 1; }

print_status "All prerequisites found"
echo ""

# Step 1: Start Minikube
echo -e "${BLUE}Step 1: Starting Minikube...${NC}"
minikube status >/dev/null 2>&1 && MINIKUBE_RUNNING=true || MINIKUBE_RUNNING=false

if [ "$MINIKUBE_RUNNING" = true ]; then
    print_info "Minikube is already running"
else
    print_info "Starting Minikube with ${CPUS} CPUs and ${MEMORY}MB RAM..."
    minikube start --cpus ${CPUS} --memory ${MEMORY}
    print_status "Minikube started"
fi
echo ""

# Step 2: Enable addons
echo -e "${BLUE}Step 2: Enabling Minikube addons...${NC}"
minikube addons enable metrics-server
minikube addons enable ingress
print_status "Addons enabled"
echo ""

# Step 3: Create namespace
echo -e "${BLUE}Step 3: Creating namespace...${NC}"
kubectl apply -f k8s/base/namespace.yaml
print_status "Namespace '${NAMESPACE}' created"
echo ""

# Step 4: Build worker image
echo -e "${BLUE}Step 4: Building worker Docker image...${NC}"
print_info "Configuring Docker to use Minikube's daemon..."
eval $(minikube docker-env)

print_info "Building image (this may take a few minutes)..."
cd worker
if docker build -t ai-agent-worker:latest .; then
    print_status "Worker image built successfully"
else
    print_error "Failed to build worker image"
    exit 1
fi
cd ..

# Verify image exists in Minikube
print_info "Verifying image in Minikube..."
eval $(minikube docker-env)
if docker images | grep -q "ai-agent-worker"; then
    print_status "Image verified in Minikube's Docker"
    docker images | grep "ai-agent-worker"
else
    print_error "Image not found in Minikube"
    exit 1
fi
echo ""

# Step 5: Add Helm repositories
echo -e "${BLUE}Step 5: Adding Helm repositories...${NC}"
helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
helm repo update > /dev/null 2>&1
print_status "Helm repositories added and updated"
echo ""

# Step 6: Deploy RabbitMQ
echo -e "${BLUE}Step 6: Deploying RabbitMQ...${NC}"
kubectl get deployment rabbitmq -n ${NAMESPACE} >/dev/null 2>&1 && RABBITMQ_EXISTS=true || RABBITMQ_EXISTS=false

if [ "$RABBITMQ_EXISTS" = true ]; then
    print_info "RabbitMQ already deployed, skipping..."
else
    print_info "Deploying RabbitMQ..."
    kubectl apply -f k8s/base/rabbitmq-simple.yaml
    print_info "Waiting for RabbitMQ to be ready (this may take up to 2 minutes)..."
    kubectl wait --for=condition=ready pod -l app=rabbitmq -n ${NAMESPACE} --timeout=120s
    print_status "RabbitMQ deployed and ready"
fi
echo ""

# Step 7: Deploy KEDA
echo -e "${BLUE}Step 7: Deploying KEDA...${NC}"
kubectl get namespace keda >/dev/null 2>&1 && KEDA_EXISTS=true || KEDA_EXISTS=false

if [ "$KEDA_EXISTS" = true ]; then
    print_info "KEDA already installed, skipping..."
else
    print_info "Installing KEDA..."
    helm install keda kedacore/keda --namespace keda --create-namespace --wait > /dev/null 2>&1
    print_status "KEDA installed"
fi
echo ""

# Step 8: Create secrets
echo -e "${BLUE}Step 8: Creating secrets...${NC}"

# RabbitMQ credentials
kubectl get secret rabbitmq-credentials -n ${NAMESPACE} >/dev/null 2>&1 || \
    kubectl create secret generic rabbitmq-credentials \
        --from-literal=username=admin \
        --from-literal=password=${RABBITMQ_PASSWORD} \
        -n ${NAMESPACE}
print_status "RabbitMQ credentials secret created"

# KEDA RabbitMQ auth
kubectl get secret keda-rabbitmq-secret -n ${NAMESPACE} >/dev/null 2>&1 || \
    kubectl create secret generic keda-rabbitmq-secret \
        --from-literal=host="amqp://admin:${RABBITMQ_PASSWORD}@rabbitmq.${NAMESPACE}.svc.cluster.local:5672/" \
        -n ${NAMESPACE}
print_status "KEDA RabbitMQ secret created"

# GitHub token (if not exists, create placeholder)
kubectl get secret github-credentials -n ${NAMESPACE} >/dev/null 2>&1 && GITHUB_SECRET_EXISTS=true || GITHUB_SECRET_EXISTS=false

if [ "$GITHUB_SECRET_EXISTS" = true ]; then
    print_info "GitHub credentials secret already exists"
else
    echo -e "${YELLOW}⚠️  GitHub token not configured${NC}"
    echo -e "${YELLOW}   Creating placeholder secret...${NC}"
    echo -e "${YELLOW}   You MUST update it before testing Plan Mode:${NC}"
    echo -e "${YELLOW}   kubectl create secret generic github-credentials --from-literal=token=YOUR_TOKEN -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -${NC}"
    kubectl create secret generic github-credentials \
        --from-literal=token=ghp_PLACEHOLDER_REPLACE_ME \
        -n ${NAMESPACE}
fi
echo ""

# Step 9: Deploy Ollama
echo -e "${BLUE}Step 9: Deploying Ollama (LLM service)...${NC}"
kubectl get deployment ollama -n ${NAMESPACE} >/dev/null 2>&1 && OLLAMA_EXISTS=true || OLLAMA_EXISTS=false

if [ "$OLLAMA_EXISTS" = true ]; then
    print_info "Ollama already deployed, skipping..."
else
    print_info "Deploying Ollama..."
    kubectl apply -f k8s/base/ollama-deployment.yaml
    print_status "Ollama deployment created"
    print_info "Model download started (will take 5-10 minutes in background)"
    print_info "Check progress with: kubectl logs -f job/ollama-pull-model -n ${NAMESPACE}"
fi
echo ""

# Step 10: Apply configuration
echo -e "${BLUE}Step 10: Applying configuration...${NC}"
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/keda-auth.yaml
print_status "ConfigMap and KEDA auth applied"
echo ""

# Step 11: Deploy worker
echo -e "${BLUE}Step 11: Deploying AI Agent Worker...${NC}"
kubectl apply -f k8s/base/deployment.yaml
print_status "Worker deployment created"

# Force a rollout to ensure it uses the latest image
print_info "Triggering rollout to use latest image..."
kubectl rollout restart deployment/ai-agent-worker -n ${NAMESPACE} 2>/dev/null || true
sleep 2
echo ""

# Step 12: Deploy KEDA ScaledObject
echo -e "${BLUE}Step 12: Configuring KEDA auto-scaling...${NC}"
kubectl apply -f k8s/base/scaledobject.yaml
print_status "KEDA ScaledObject created"
echo ""

# Verification
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Verification${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

echo -e "${GREEN}Pods in namespace ${NAMESPACE}:${NC}"
kubectl get pods -n ${NAMESPACE}
echo ""

echo -e "${GREEN}Services:${NC}"
kubectl get svc -n ${NAMESPACE}
echo ""

echo -e "${GREEN}ScaledObject:${NC}"
kubectl get scaledobject -n ${NAMESPACE}
echo ""

echo -e "${GREEN}Secrets:${NC}"
kubectl get secrets -n ${NAMESPACE}
echo ""

# Final instructions
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Installation Complete!${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

echo -e "${GREEN}✓ Minikube cluster running${NC}"
echo -e "${GREEN}✓ RabbitMQ deployed${NC}"
echo -e "${GREEN}✓ KEDA installed${NC}"
echo -e "${GREEN}✓ Ollama deploying (model downloading in background)${NC}"
echo -e "${GREEN}✓ Worker deployed (scaled to 0)${NC}"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANT: Configure GitHub token before testing:${NC}"
echo -e "   1. Get token from: https://github.com/settings/tokens"
echo -e "   2. Scope needed: 'repo'"
echo -e "   3. Update secret:"
echo -e "      ${BLUE}kubectl create secret generic github-credentials --from-literal=token=ghp_YOUR_TOKEN -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -${NC}"
echo ""

echo -e "${YELLOW}📊 Monitor Ollama model download:${NC}"
echo -e "   ${BLUE}kubectl logs -f job/ollama-pull-model -n ${NAMESPACE}${NC}"
echo ""

echo -e "${YELLOW}🧪 Test the system:${NC}"
echo -e "   1. Port-forward RabbitMQ:"
echo -e "      ${BLUE}kubectl port-forward -n ${NAMESPACE} svc/rabbitmq 5672:5672 &${NC}"
echo -e "   2. Run test script:"
echo -e "      ${BLUE}cd scripts && pip install -r requirements.txt${NC}"
echo -e "      ${BLUE}python test-iteration3.py --repo-url https://github.com/user/repo --issue-id 1${NC}"
echo -e "   3. Monitor:"
echo -e "      ${BLUE}kubectl get pods -n ${NAMESPACE} -w${NC}"
echo -e "      ${BLUE}kubectl logs -f -n ${NAMESPACE} -l app=ai-agent-worker${NC}"
echo ""

echo -e "${GREEN}🎉 All done! Your AI Coding Agent is ready!${NC}"
echo ""

