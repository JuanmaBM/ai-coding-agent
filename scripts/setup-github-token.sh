#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE="ai-agent"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}GitHub Token Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage:${NC}"
    echo "  ./setup-github-token.sh <github-token>"
    echo ""
    echo -e "${YELLOW}Example:${NC}"
    echo "  ./setup-github-token.sh ghp_xxxxxxxxxxxxx"
    echo ""
    echo -e "${YELLOW}To get a token:${NC}"
    echo "  1. Go to https://github.com/settings/tokens"
    echo "  2. Generate new token (classic)"
    echo "  3. Select scope: repo"
    echo "  4. Copy the token and run this script"
    exit 1
fi

GITHUB_TOKEN=$1

echo -e "${YELLOW}➜${NC} Creating GitHub credentials secret..."
kubectl create secret generic github-credentials \
    --from-literal=token=${GITHUB_TOKEN} \
    -n ${NAMESPACE} \
    --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo -e "${GREEN}✓ GitHub token configured!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Restart worker to pick up the token:"
echo "     ${BLUE}kubectl rollout restart deployment/ai-agent-worker -n ${NAMESPACE}${NC}"
echo ""
echo "  2. Test with an issue:"
echo "     ${BLUE}python scripts/test-iteration3.py --repo-url https://github.com/user/repo --issue-id 1${NC}"

