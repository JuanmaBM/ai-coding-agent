.PHONY: help install uninstall test logs status rebuild verify

help:
	@echo "AI Coding Agent - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install    - Install everything (Minikube + all components)"
	@echo "  uninstall  - Remove all components"
	@echo "  rebuild    - Rebuild and redeploy worker"
	@echo "  verify     - Verify worker image in Minikube"
	@echo "  test       - Setup for testing"
	@echo "  logs       - Stream worker logs"
	@echo "  status     - Show deployment status"

install:
	@chmod +x install.sh
	@./install.sh

uninstall:
	@chmod +x uninstall.sh
	@./uninstall.sh

rebuild:
	@echo "🏗️  Rebuilding worker image..."
	@eval $$(minikube docker-env) && cd worker && docker build -t ai-agent-worker:latest .
	@echo "🔍 Verifying image..."
	@eval $$(minikube docker-env) && docker images | grep ai-agent-worker
	@echo "🔄 Restarting deployment..."
	@kubectl rollout restart deployment/ai-agent-worker -n ai-agent
	@kubectl rollout status deployment/ai-agent-worker -n ai-agent --timeout=60s
	@echo "✅ Worker rebuilt and restarted"

test:
	@echo "Setting up port-forward..."
	@kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 >/dev/null 2>&1 &
	@sleep 2
	@echo "Run test with:"
	@echo "  cd scripts && python test-iteration3.py --repo-url https://github.com/user/repo --issue-id 1"

logs:
	@kubectl logs -f -n ai-agent -l app=ai-agent-worker

verify:
	@chmod +x scripts/verify-image.sh
	@./scripts/verify-image.sh

status:
	@echo "=== Pods ==="
	@kubectl get pods -n ai-agent
	@echo ""
	@echo "=== Services ==="
	@kubectl get svc -n ai-agent
	@echo ""
	@echo "=== ScaledObject ==="
	@kubectl get scaledobject -n ai-agent
	@echo ""
	@echo "=== Secrets ==="
	@kubectl get secrets -n ai-agent
