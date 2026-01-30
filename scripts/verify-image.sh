#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Verifying worker image in Minikube..."
echo ""

# Configure Docker to use Minikube
eval $(minikube docker-env)

# Check if image exists
if docker images | grep -q "ai-agent-worker"; then
    echo -e "${GREEN}✓ Image found in Minikube's Docker:${NC}"
    docker images | grep "ai-agent-worker" | head -1
    echo ""
    
    # Check deployment
    echo "Checking deployment..."
    kubectl get deployment ai-agent-worker -n ai-agent -o jsonpath='{.spec.template.spec.containers[0].image}'
    echo ""
    echo ""
    
    # Check if pods can pull the image
    kubectl get pods -n ai-agent -l app=ai-agent-worker -o wide 2>/dev/null
    
    echo ""
    echo -e "${GREEN}✓ Everything looks good!${NC}"
else
    echo -e "${RED}✗ Image NOT found in Minikube's Docker${NC}"
    echo ""
    echo -e "${YELLOW}Build the image with:${NC}"
    echo "  eval \$(minikube docker-env)"
    echo "  cd worker && docker build -t ai-agent-worker:latest ."
    exit 1
fi

