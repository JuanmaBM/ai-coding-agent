#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE="ai-agent"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}AI Coding Agent - Uninstall${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}➜${NC} $1"
}

# Confirm
echo -e "${YELLOW}This will remove:${NC}"
echo "  - Namespace ${NAMESPACE} and all resources"
echo "  - KEDA installation"
echo "  - Minikube cluster (optional)"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Delete namespace
echo -e "${BLUE}Removing namespace ${NAMESPACE}...${NC}"
kubectl delete namespace ${NAMESPACE} --timeout=60s 2>/dev/null || true
print_status "Namespace ${NAMESPACE} deleted"

# Uninstall KEDA
echo -e "${BLUE}Uninstalling KEDA...${NC}"
helm uninstall keda -n keda 2>/dev/null || true
kubectl delete namespace keda --timeout=60s 2>/dev/null || true
print_status "KEDA uninstalled"

# Ask about Minikube
echo ""
read -p "Stop Minikube cluster? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    minikube stop
    print_status "Minikube stopped"
    
    echo ""
    read -p "Delete Minikube cluster completely? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        minikube delete
        print_status "Minikube cluster deleted"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Cleanup complete!${NC}"

