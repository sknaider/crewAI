# ============================================================================
# CrewAI Makefile - Development & Operations Utilities
# ============================================================================
# Enterprise-grade makefile with common commands for development, testing,
# deployment, and operations.
#
# Usage:
#   make help          # Show all available commands
#   make test          # Run tests
#   make docker-build  # Build Docker image
# ============================================================================

.PHONY: help
.DEFAULT_GOAL := help

# ============================================================================
# Configuration
# ============================================================================
PYTHON := python3
UV := uv
DOCKER := docker
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl
HELM := helm

IMAGE_NAME := crewai
IMAGE_TAG := 1.5.0
REGISTRY := # Set your registry here (e.g., ghcr.io/your-org)

NAMESPACE := crewai
HELM_RELEASE := crewai

# ============================================================================
# Help
# ============================================================================
help: ## Show this help message
	@echo "CrewAI Development & Operations Commands"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Development
# ============================================================================
install: ## Install dependencies with uv
	@echo "Installing dependencies..."
	$(UV) sync --all-groups --all-extras

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(UV) sync --all-groups --all-extras
	$(UV) run pre-commit install

clean: ## Clean build artifacts and cache
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	rm -rf dist/ build/

# ============================================================================
# Testing
# ============================================================================
test: ## Run all tests
	@echo "Running tests..."
	cd lib/crewai && $(UV) run pytest -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	cd lib/crewai && $(UV) run pytest \
		--cov=crewai \
		--cov-report=html \
		--cov-report=term \
		--cov-report=xml \
		-v

test-fast: ## Run tests in parallel (fast)
	@echo "Running tests in parallel..."
	cd lib/crewai && $(UV) run pytest -n auto -v

test-tools: ## Run tools tests
	@echo "Running tools tests..."
	cd lib/crewai-tools && $(UV) run pytest -v

test-all: test test-tools ## Run all test suites

# ============================================================================
# Code Quality
# ============================================================================
lint: ## Run linter (ruff)
	@echo "Running linter..."
	$(UV) run ruff check .

lint-fix: ## Auto-fix linting issues
	@echo "Auto-fixing linting issues..."
	$(UV) run ruff check --fix .

format: ## Format code with ruff
	@echo "Formatting code..."
	$(UV) run ruff format .

type-check: ## Run type checker (mypy)
	@echo "Running type checker..."
	$(UV) run mypy lib/crewai/src lib/crewai-tools/src

security-check: ## Run security scan (bandit)
	@echo "Running security scan..."
	$(UV) run bandit -r lib/crewai/src lib/crewai-tools/src -c pyproject.toml

quality: lint type-check security-check ## Run all quality checks

pre-commit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks..."
	$(UV) run pre-commit run --all-files

# ============================================================================
# Docker
# ============================================================================
docker-build: ## Build Docker image
	@echo "Building Docker image: $(IMAGE_NAME):$(IMAGE_TAG)..."
	$(DOCKER) build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	$(DOCKER) tag $(IMAGE_NAME):$(IMAGE_TAG) $(IMAGE_NAME):latest

docker-build-no-cache: ## Build Docker image without cache
	@echo "Building Docker image (no cache)..."
	$(DOCKER) build --no-cache -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-push: ## Push Docker image to registry
	@echo "Pushing Docker image to $(REGISTRY)..."
	@if [ -z "$(REGISTRY)" ]; then echo "Error: REGISTRY not set"; exit 1; fi
	$(DOCKER) tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(DOCKER) push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

docker-run: ## Run Docker container locally
	@echo "Running Docker container..."
	$(DOCKER) run -it --rm \
		-p 8000:8000 \
		-p 9090:9090 \
		-e OPENAI_API_KEY=${OPENAI_API_KEY} \
		$(IMAGE_NAME):$(IMAGE_TAG)

# ============================================================================
# Docker Compose
# ============================================================================
compose-up: ## Start all services with Docker Compose
	@echo "Starting services with Docker Compose..."
	$(DOCKER_COMPOSE) up -d

compose-down: ## Stop all services
	@echo "Stopping services..."
	$(DOCKER_COMPOSE) down

compose-logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

compose-ps: ## List running services
	$(DOCKER_COMPOSE) ps

compose-restart: ## Restart all services
	@echo "Restarting services..."
	$(DOCKER_COMPOSE) restart

compose-clean: ## Stop and remove all containers, volumes
	@echo "Cleaning up Docker Compose..."
	$(DOCKER_COMPOSE) down -v --remove-orphans

# ============================================================================
# Kubernetes
# ============================================================================
k8s-create-namespace: ## Create Kubernetes namespace
	@echo "Creating namespace: $(NAMESPACE)..."
	$(KUBECTL) create namespace $(NAMESPACE) --dry-run=client -o yaml | $(KUBECTL) apply -f -

k8s-deploy: ## Deploy to Kubernetes using kubectl
	@echo "Deploying to Kubernetes..."
	$(KUBECTL) apply -f k8s/namespace.yaml
	$(KUBECTL) apply -f k8s/configmap.yaml
	$(KUBECTL) apply -f k8s/rbac.yaml
	$(KUBECTL) apply -f k8s/pvc.yaml
	$(KUBECTL) apply -f k8s/deployment.yaml

k8s-delete: ## Delete Kubernetes resources
	@echo "Deleting Kubernetes resources..."
	$(KUBECTL) delete -f k8s/deployment.yaml --ignore-not-found
	$(KUBECTL) delete -f k8s/pvc.yaml --ignore-not-found
	$(KUBECTL) delete -f k8s/rbac.yaml --ignore-not-found
	$(KUBECTL) delete -f k8s/configmap.yaml --ignore-not-found

k8s-status: ## Show deployment status
	@echo "Deployment status:"
	$(KUBECTL) get all -n $(NAMESPACE)

k8s-logs: ## Show pod logs
	$(KUBECTL) logs -f -l app=crewai -n $(NAMESPACE)

k8s-describe: ## Describe deployment
	$(KUBECTL) describe deployment crewai-service -n $(NAMESPACE)

k8s-port-forward: ## Port forward to local machine
	@echo "Port forwarding 8000:8000..."
	$(KUBECTL) port-forward -n $(NAMESPACE) svc/crewai-service 8000:80

# ============================================================================
# Helm
# ============================================================================
helm-lint: ## Lint Helm chart
	@echo "Linting Helm chart..."
	$(HELM) lint helm/crewai

helm-template: ## Generate Kubernetes manifests from Helm chart
	@echo "Generating manifests..."
	$(HELM) template $(HELM_RELEASE) helm/crewai

helm-install: ## Install Helm chart
	@echo "Installing Helm chart..."
	$(HELM) install $(HELM_RELEASE) helm/crewai --namespace $(NAMESPACE) --create-namespace

helm-upgrade: ## Upgrade Helm release
	@echo "Upgrading Helm release..."
	$(HELM) upgrade $(HELM_RELEASE) helm/crewai --namespace $(NAMESPACE)

helm-uninstall: ## Uninstall Helm release
	@echo "Uninstalling Helm release..."
	$(HELM) uninstall $(HELM_RELEASE) --namespace $(NAMESPACE)

helm-status: ## Show Helm release status
	$(HELM) status $(HELM_RELEASE) --namespace $(NAMESPACE)

# ============================================================================
# Build & Release
# ============================================================================
build: ## Build Python packages
	@echo "Building packages..."
	$(UV) build --all-packages

publish: build ## Publish to PyPI (requires credentials)
	@echo "Publishing to PyPI..."
	$(UV) publish dist/*

version: ## Show current version
	@echo "Current version: $(IMAGE_TAG)"
	@grep "^version" pyproject.toml

# ============================================================================
# Monitoring & Operations
# ============================================================================
metrics: ## Open Prometheus metrics endpoint
	@echo "Opening metrics endpoint..."
	@command -v open >/dev/null 2>&1 && open http://localhost:9090/metrics || echo "Visit: http://localhost:9090/metrics"

grafana: ## Open Grafana dashboard
	@echo "Opening Grafana..."
	@command -v open >/dev/null 2>&1 && open http://localhost:3000 || echo "Visit: http://localhost:3000 (admin/admin)"

health: ## Check application health
	@echo "Checking health..."
	@curl -s http://localhost:8000/health | $(PYTHON) -m json.tool || echo "Application not running"

# ============================================================================
# Database Operations
# ============================================================================
db-backup: ## Backup database (Docker Compose)
	@echo "Backing up database..."
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U crewai crewai > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore database from backup (requires BACKUP_FILE)
	@echo "Restoring database..."
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Error: BACKUP_FILE not set"; exit 1; fi
	$(DOCKER_COMPOSE) exec -T postgres psql -U crewai crewai < $(BACKUP_FILE)

# ============================================================================
# Documentation
# ============================================================================
docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	@echo "Documentation not configured yet"

# ============================================================================
# Cleanup
# ============================================================================
clean-all: clean compose-clean ## Clean everything (build artifacts and Docker)
	@echo "Full cleanup complete"

# ============================================================================
# CI/CD Simulation
# ============================================================================
ci: lint type-check test-coverage ## Run CI pipeline locally
	@echo "CI pipeline completed successfully!"

cd: docker-build ## Build artifacts for deployment
	@echo "CD pipeline completed!"

# ============================================================================
# Quick Start
# ============================================================================
quickstart: install compose-up ## Quick start: install deps and start services
	@echo ""
	@echo "✅ CrewAI is running!"
	@echo ""
	@echo "Services:"
	@echo "  - CrewAI API:       http://localhost:8000"
	@echo "  - Prometheus:       http://localhost:9091"
	@echo "  - Grafana:          http://localhost:3000 (admin/admin)"
	@echo "  - Redis Commander:  http://localhost:8081"
	@echo "  - pgAdmin:          http://localhost:5050 (admin@crewai.local/admin)"
	@echo ""
	@echo "View logs: make compose-logs"
	@echo "Stop services: make compose-down"
	@echo ""
