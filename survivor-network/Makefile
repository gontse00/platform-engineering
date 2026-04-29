# ============================================================
# Survivor Network — Makefile
# ============================================================
CLUSTER     := survivor-net
NAMESPACE   := survivor-apps
CONTEXT     := kind-$(CLUSTER)
KUBECTL     := kubectl --context $(CONTEXT) -n $(NAMESPACE)
TIMEOUT     := 120s
HELM_CHART  := platform/helm/survivor-network
HELM_VALUES := $(HELM_CHART)/values-local.yaml

# All service images (must match Helm values)
SERVICES := chatbot-service graph-core chatbot-ui admin-ui agent-service incident-service participant-service admin-service

# Source directories
DIR_chatbot-service     := ./chatbot-service
DIR_graph-core          := ./graph-core/backend
DIR_chatbot-ui          := ./chatbot-ui-service
DIR_admin-ui            := ./admin-ui
DIR_agent-service       := ./agent-service
DIR_incident-service    := ./incident-service
DIR_participant-service := ./participant-service
DIR_admin-service       := ./admin-service

.PHONY: help all local-up local-down local-build local-load-kind deploy-local-helm \
        status health smoke-local local-test local-sim local-sim-full local-sim-100 \
        helm-lint-local helm-template-local logs restart clean \
        cloud-dev-plan cloud-dev-apply deploy-dev \
        chatbot graph chatbot-ui admin-ui agent incident participant admin-svc

# ============================================================
# Help
# ============================================================

help:
	@echo "=== Recommended Local Workflow ==="
	@echo "  make local-up           — create Kind cluster"
	@echo "  make local-build        — build all Docker images"
	@echo "  make local-load-kind    — load images into Kind"
	@echo "  make deploy-local-helm  — deploy all services via Helm"
	@echo "  make status             — show pod status"
	@echo "  make smoke-local        — health check all services"
	@echo "  make local-test         — run unit tests"
	@echo "  make local-sim          — 10-user disaster simulation"
	@echo "  make local-sim-full     — full flow simulation"
	@echo ""
	@echo "=== Helm ==="
	@echo "  make helm-lint-local    — lint Helm chart"
	@echo "  make helm-template-local— render templates"
	@echo ""
	@echo "=== Individual Services (legacy manifest deploy) ==="
	@echo "  make chatbot / graph / chatbot-ui / admin-ui"
	@echo "  make agent / incident / participant / admin-svc"
	@echo ""
	@echo "=== Operations ==="
	@echo "  make logs SVC=x         — tail logs"
	@echo "  make restart            — rolling restart all"
	@echo "  make clean              — remove local images"

# ============================================================
# Local Workflow (Helm-based)
# ============================================================

local-up:
	@echo "\n� Starting local Kind cluster..."
	cd survivor-infra && terraform init && terraform apply -auto-approve
	@echo "✅ Cluster ready."

local-down:
	@echo "\n� Destroying local Kind cluster..."
	kind delete cluster --name $(CLUSTER)
	@echo "✅ Cluster destroyed."

local-build:
	@echo "\n🔨 Building all service images..."
	@for svc in $(SERVICES); do \
		dir=$${DIR_$$svc:-./$$svc}; \
		echo "  Building $$svc..."; \
		docker build -t $$svc:latest $(DIR_$$(echo $$svc)) 2>/dev/null || true; \
	done
	docker build -t chatbot-service:latest $(DIR_chatbot-service)
	docker build -t graph-core:latest $(DIR_graph-core)
	docker build -t chatbot-ui:latest $(DIR_chatbot-ui)
	docker build -t admin-ui:latest $(DIR_admin-ui)
	docker build -t agent-service:latest $(DIR_agent-service)
	docker build -t incident-service:latest $(DIR_incident-service)
	docker build -t participant-service:latest $(DIR_participant-service)
	docker build -t admin-service:latest $(DIR_admin-service)
	@echo "✅ All images built."

local-load-kind:
	@echo "\n� Loading images into Kind..."
	@for svc in $(SERVICES); do \
		echo "  Loading $$svc:latest..."; \
		kind load docker-image $$svc:latest --name $(CLUSTER); \
	done
	@echo "✅ All images loaded."

deploy-local-helm:
	@echo "\n� Deploying with Helm (local)..."
	helm upgrade --install survivor-network \
		$(HELM_CHART) \
		-f $(HELM_VALUES) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait --timeout 5m
	@echo "✅ Helm deployment complete."

# Full local deploy shortcut
all: local-build local-load-kind deploy-local-helm
	@echo "\n✅ All services built and deployed via Helm."

# ============================================================
# Helm Validation
# ============================================================

helm-lint-local:
	helm lint $(HELM_CHART) -f $(HELM_VALUES)

helm-template-local:
	helm template survivor-network $(HELM_CHART) -f $(HELM_VALUES)

# ============================================================
# Status & Health
# ============================================================

status:
	@echo "\n📊 Pod status:"
	$(KUBECTL) get pods -o wide
	@echo "\n📊 Deployments:"
	$(KUBECTL) get deploy

smoke-local: health

health:
	@echo "\n🏥 Health checks:"
	@curl -sf http://chatbot-service.127.0.0.1.nip.io/health && echo " ✅ chatbot-service" || echo " ❌ chatbot-service"
	@curl -sf http://graph-core.127.0.0.1.nip.io/health && echo " ✅ graph-core" || echo " ❌ graph-core"
	@curl -sf http://incident-service.127.0.0.1.nip.io/health && echo " ✅ incident-service" || echo " ❌ incident-service"
	@curl -sf http://participant-service.127.0.0.1.nip.io/health && echo " ✅ participant-service" || echo " ❌ participant-service"
	@curl -sf http://admin-service.127.0.0.1.nip.io/health && echo " ✅ admin-service" || echo " ❌ admin-service"
	@curl -sf http://admin-ui.127.0.0.1.nip.io/health && echo " ✅ admin-ui" || echo " ❌ admin-ui"
	@curl -sf http://chatbot-ui.127.0.0.1.nip.io/ >/dev/null && echo " ✅ chatbot-ui" || echo " ❌ chatbot-ui"
	@echo "  ⚠️  agent-service (internal only — no ingress)"

# ============================================================
# Tests & Simulations
# ============================================================

local-test:
	@echo "\n🧪 Running tests..."
	cd chatbot-service && python3 -m pytest tests/ -v
	cd agent-service && python3 -m pytest tests/ -v
	cd admin-service && python3 -m pytest tests/ -v

local-sim:
	python3 tests/load/disaster_sim.py --users 10 --ramp-up 5

local-sim-full:
	python3 tests/load/full_flow_sim.py --survivors 20 --helpers 10 --ramp-up 5

local-sim-100:
	python3 tests/load/disaster_sim.py --users 100 --ramp-up 60

# ============================================================
# Logs
# ============================================================

logs:
ifndef SVC
	@echo "Usage: make logs SVC=chatbot-service"
	@exit 1
endif
	$(KUBECTL) logs -l app=$(SVC) --tail=100 -f

# ============================================================
# Operations
# ============================================================

restart:
	@echo "\n🔄 Rolling restart all services..."
	$(KUBECTL) rollout restart deploy/chatbot-service deploy/graph-core deploy/chatbot-ui deploy/admin-ui deploy/agent-service deploy/incident-service deploy/participant-service deploy/admin-service
	@echo "✅ Restart initiated."

clean:
	@echo "\n🧹 Removing local images..."
	@for svc in $(SERVICES); do docker rmi $$svc:latest 2>/dev/null || true; done
	@echo "✅ Clean."

# ============================================================
# Legacy per-service targets (direct manifest deploy)
# ============================================================

chatbot:
	docker build -t chatbot-service:latest $(DIR_chatbot-service)
	kind load docker-image chatbot-service:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_chatbot-service)/k8s/
	$(KUBECTL) rollout restart deploy/chatbot-service
	$(KUBECTL) rollout status deploy/chatbot-service --timeout=$(TIMEOUT)

graph:
	docker build -t graph-core:latest $(DIR_graph-core)
	kind load docker-image graph-core:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_graph-core)/deploy/graph-core.yaml
	$(KUBECTL) rollout restart deploy/graph-core
	$(KUBECTL) rollout status deploy/graph-core --timeout=$(TIMEOUT)

chatbot-ui:
	docker build -t chatbot-ui:latest $(DIR_chatbot-ui)
	kind load docker-image chatbot-ui:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_chatbot-ui)/k8s/
	$(KUBECTL) rollout restart deploy/chatbot-ui
	$(KUBECTL) rollout status deploy/chatbot-ui --timeout=$(TIMEOUT)

admin-ui:
	docker build -t admin-ui:latest $(DIR_admin-ui)
	kind load docker-image admin-ui:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_admin-ui)/k8s/
	$(KUBECTL) rollout restart deploy/admin-ui
	$(KUBECTL) rollout status deploy/admin-ui --timeout=$(TIMEOUT)

agent:
	docker build -t agent-service:latest $(DIR_agent-service)
	kind load docker-image agent-service:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_agent-service)/k8s/
	$(KUBECTL) rollout restart deploy/agent-service
	$(KUBECTL) rollout status deploy/agent-service --timeout=$(TIMEOUT)

incident:
	docker build -t incident-service:latest $(DIR_incident-service)
	kind load docker-image incident-service:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_incident-service)/k8s/
	$(KUBECTL) rollout restart deploy/incident-service
	$(KUBECTL) rollout status deploy/incident-service --timeout=$(TIMEOUT)

participant:
	docker build -t participant-service:latest $(DIR_participant-service)
	kind load docker-image participant-service:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_participant-service)/k8s/
	$(KUBECTL) rollout restart deploy/participant-service
	$(KUBECTL) rollout status deploy/participant-service --timeout=$(TIMEOUT)

admin-svc:
	docker build -t admin-service:latest $(DIR_admin-service)
	kind load docker-image admin-service:latest --name $(CLUSTER)
	$(KUBECTL) apply -f $(DIR_admin-service)/k8s/
	$(KUBECTL) rollout restart deploy/admin-service
	$(KUBECTL) rollout status deploy/admin-service --timeout=$(TIMEOUT)

# ============================================================
# Cloud Deployment
# ============================================================

cloud-dev-plan:
	cd infra/cloud/dev && terraform init && terraform plan

cloud-dev-apply:
	cd infra/cloud/dev && terraform init && terraform apply

deploy-dev:
	helm upgrade --install survivor-network \
		$(HELM_CHART) \
		-f $(HELM_CHART)/values-dev.yaml \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait --timeout 5m
