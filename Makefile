.PHONY: help setup build deploy test clean

help:
	@echo "Available targets:"
	@echo "  setup      - Initialize Minikube and install dependencies"
	@echo "  build      - Build worker Docker image"
	@echo "  deploy     - Deploy all Kubernetes resources"
	@echo "  test       - Run end-to-end tests"
	@echo "  logs       - Stream worker logs"
	@echo "  clean      - Remove all deployed resources"

# Setup Minikube and install dependencies
setup:
	@echo "🚀 Starting Minikube..."
	minikube start --cpus 2 --memory 4096 --driver=docker
	minikube addons enable metrics-server
	minikube addons enable ingress
	@echo "📦 Installing Helm charts..."
	helm repo add bitnami https://charts.bitnami.com/bitnami
	helm repo add kedacore https://kedacore.github.io/charts
	helm repo update
	@echo "✅ Setup complete!"

# Build worker image
build:
	@echo "🏗️  Building worker Docker image..."
	eval $$(minikube docker-env) && \
	cd worker && \
	docker build -t ai-agent-worker:latest .
	@echo "✅ Build complete!"

# Deploy all resources
deploy:
	@echo "🚀 Deploying AI Coding Agent..."
	kubectl apply -f k8s/base/namespace.yaml
	@echo "Waiting for namespace..."
	kubectl wait --for=jsonpath='{.status.phase}'=Active namespace/ai-agent --timeout=30s || true
	@echo "Installing RabbitMQ..."
	helm install rabbitmq bitnami/rabbitmq \
		-f k8s/base/rabbitmq-values.yaml \
		-n ai-agent \
		--set auth.password=DevPassword123 \
		--wait --timeout=5m || helm upgrade rabbitmq bitnami/rabbitmq \
		-f k8s/base/rabbitmq-values.yaml \
		-n ai-agent \
		--wait --timeout=5m
	@echo "Creating secrets..."
	kubectl create secret generic rabbitmq-credentials \
		--from-literal=username=admin \
		--from-literal=password=DevPassword123 \
		-n ai-agent --dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic keda-rabbitmq-secret \
		--from-literal=host="amqp://admin:DevPassword123@rabbitmq.ai-agent.svc.cluster.local:5672/" \
		-n ai-agent --dry-run=client -o yaml | kubectl apply -f -
	@echo "Installing KEDA..."
	helm install keda kedacore/keda --namespace keda --create-namespace --wait || \
		helm upgrade keda kedacore/keda --namespace keda --wait
	@echo "Applying configurations..."
	kubectl apply -f k8s/base/keda-auth.yaml
	kubectl apply -f k8s/base/configmap.yaml
	kubectl apply -f k8s/base/deployment.yaml
	kubectl apply -f k8s/base/scaledobject.yaml
	@echo "✅ Deployment complete!"
	@echo "📊 Check status with: kubectl get pods -n ai-agent -w"

# Test the setup
test:
	@echo "🧪 Running tests..."
	@echo "Setting up port-forward in background..."
	kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672 & sleep 3
	cd scripts && pip install -q -r requirements.txt && \
		python test-queue.py --count 3 --delay 1
	@echo "📊 Monitor scaling with: kubectl get pods -n ai-agent -w"

# Stream logs
logs:
	kubectl logs -n ai-agent -l app=ai-agent-worker --tail=100 -f

# Clean up everything
clean:
	@echo "🧹 Cleaning up resources..."
	-helm uninstall rabbitmq -n ai-agent
	-helm uninstall keda -n keda
	-kubectl delete namespace ai-agent
	-kubectl delete namespace keda
	@echo "✅ Cleanup complete!"

# One-command full setup
all: setup build deploy
	@echo "🎉 Full setup complete!"
	@echo "Run 'make test' to validate the deployment"

