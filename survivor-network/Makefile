# ============================================================
# Survivor Network — Local Dev Makefile
# ============================================================
CLUSTER     := survivor-net
NAMESPACE   := survivor-apps
CONTEXT     := kind-$(CLUSTER)
KUBECTL     := kubectl --context $(CONTEXT) -n $(NAMESPACE)
TIMEOUT     := 120s

# Image names (must match k8s deployment manifests)
CHATBOT_IMG     := chatbot-service:latest
GRAPH_IMG       := graph-core:latest
CHATUI_IMG      := chatbot-ui:latest
ADMINUI_IMG     := survivor-net/admin-ui:latest
AGENT_IMG       := agent-service:latest
INCIDENT_IMG    := incident-service:latest
PARTICIPANT_IMG := participant-service:latest
ADMINSVC_IMG    := admin-service:latest

# Source paths
CHATBOT_DIR     := ./chatbot-service
GRAPH_DIR       := ./graph-core/backend
CHATUI_DIR      := ./chatbot-ui-service
ADMINUI_DIR     := ./admin-ui
AGENT_DIR       := ./agent-service
INCIDENT_DIR    := ./incident-service
PARTICIPANT_DIR := ./participant-service
ADMINSVC_DIR    := ./admin-service

# K8s manifest paths
CHATBOT_K8S     := $(CHATBOT_DIR)/k8s
GRAPH_K8S       := $(GRAPH_DIR)/deploy
CHATUI_K8S      := $(CHATUI_DIR)/k8s
ADMINUI_K8S     := $(ADMINUI_DIR)/k8s

.PHONY: all help chatbot graph chatbot-ui admin-ui agent incident participant admin-svc \
        local-up local-down local-build local-test local-sim local-sim-full \
        deploy deploy-local-helm status logs restart clean \
        cloud-dev-plan cloud-dev-apply deploy-dev

# ============================================================
# Top-level targets
# ============================================================

all: chatbot graph chatbot-ui admin-ui agent incident participant admin-svc
	@echo "\n✅ All services built and deployed."

help:
	@echo "=== Local Development ==="
	@echo "  make local-up         — create Kind cluster with Terraform"
	@echo "  make local-down       — destroy Kind cluster"
	@echo "  make local-build      — build + deploy all services"
	@echo "  make local-test       — run unit tests for all services"
	@echo "  make local-sim        — run 10-user disaster simulation"
	@echo "  make local-sim-full   — run full flow simulation (incidents + participants)"
	@echo ""
	@echo "=== Individual Services ==="
	@echo "  make chatbot          — chatbot-service"
	@echo "  make graph            — graph-core"
	@echo "  make chatbot-ui       — chatbot UI"
	@echo "  make admin-ui         — admin UI (React)"
	@echo "  make agent            — agent-service"
	@echo "  make incident         — incident-service"
	@echo "  make participant      — participant-service"
	@echo "  make admin-svc        — admin-service (BFF)"
	@echo ""
	@echo "=== Operations ==="
	@echo "  make status           — pod + deployment status"
	@echo "  make logs SVC=x       — tail logs for a service"
	@echo "  make restart          — rolling restart all"
	@echo "  make deploy           — apply all k8s manifests (no rebuild)"
	@echo "  make clean            — remove local docker images"
	@echo ""
	@echo "=== Cloud ==="
	@echo "  make cloud-dev-plan   — terraform plan for cloud dev"
	@echo "  make cloud-dev-apply  — terraform apply for cloud dev"
	@echo "  make deploy-dev       — helm deploy to cloud dev"

# ============================================================
# Per-service: build → load → apply → restart → wait
# ============================================================

chatbot:
	@echo "\n🔨 Building chatbot-service..."
	docker build -t $(CHATBOT_IMG) $(CHATBOT_DIR)
	kind load docker-image $(CHATBOT_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(CHATBOT_K8S)/
	$(KUBECTL) rollout restart deploy/chatbot-service
	$(KUBECTL) rollout status deploy/chatbot-service --timeout=$(TIMEOUT)
	@echo "✅ chatbot-service deployed."

graph:
	@echo "\n🔨 Building graph-core..."
	docker build -t $(GRAPH_IMG) $(GRAPH_DIR)
	kind load docker-image $(GRAPH_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(GRAPH_K8S)/graph-core.yaml
	$(KUBECTL) rollout restart deploy/graph-core
	$(KUBECTL) rollout status deploy/graph-core --timeout=$(TIMEOUT)
	@echo "✅ graph-core deployed."

chatbot-ui:
	@echo "\n🔨 Building chatbot-ui..."
	docker build -t $(CHATUI_IMG) $(CHATUI_DIR)
	kind load docker-image $(CHATUI_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(CHATUI_K8S)/
	$(KUBECTL) rollout restart deploy/chatbot-ui
	$(KUBECTL) rollout status deploy/chatbot-ui --timeout=$(TIMEOUT)
	@echo "✅ chatbot-ui deployed."

admin-ui:
	@echo "\n🔨 Building admin-ui..."
	docker build -t $(ADMINUI_IMG) $(ADMINUI_DIR)
	kind load docker-image $(ADMINUI_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(ADMINUI_K8S)/
	$(KUBECTL) rollout restart deploy/admin-ui
	$(KUBECTL) rollout status deploy/admin-ui --timeout=$(TIMEOUT)
	@echo "✅ admin-ui deployed."

agent:
	@echo "\n🔨 Building agent-service..."
	docker build -t $(AGENT_IMG) $(AGENT_DIR)
	kind load docker-image $(AGENT_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(AGENT_DIR)/k8s/
	$(KUBECTL) rollout restart deploy/agent-service
	$(KUBECTL) rollout status deploy/agent-service --timeout=$(TIMEOUT)
	@echo "✅ agent-service deployed."

incident:
	@echo "\n🔨 Building incident-service..."
	docker build -t $(INCIDENT_IMG) $(INCIDENT_DIR)
	kind load docker-image $(INCIDENT_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(INCIDENT_DIR)/k8s/
	$(KUBECTL) rollout restart deploy/incident-service
	$(KUBECTL) rollout status deploy/incident-service --timeout=$(TIMEOUT)
	@echo "✅ incident-service deployed."

participant:
	@echo "\n🔨 Building participant-service..."
	docker build -t $(PARTICIPANT_IMG) $(PARTICIPANT_DIR)
	kind load docker-image $(PARTICIPANT_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(PARTICIPANT_DIR)/k8s/
	$(KUBECTL) rollout restart deploy/participant-service
	$(KUBECTL) rollout status deploy/participant-service --timeout=$(TIMEOUT)
	@echo "✅ participant-service deployed."

admin-svc:
	@echo "\n🔨 Building admin-service..."
	docker build -t $(ADMINSVC_IMG) $(ADMINSVC_DIR)
	kind load docker-image $(ADMINSVC_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(ADMINSVC_DIR)/k8s/
	$(KUBECTL) rollout restart deploy/admin-service
	$(KUBECTL) rollout status deploy/admin-service --timeout=$(TIMEOUT)
	@echo "✅ admin-service deployed."

# ============================================================
# Operations
# ============================================================

deploy:
	@echo "\n📦 Applying all manifests..."
	$(KUBECTL) apply -f $(CHATBOT_K8S)/
	$(KUBECTL) apply -f $(GRAPH_K8S)/graph-core.yaml
	$(KUBECTL) apply -f $(CHATUI_K8S)/
	$(KUBECTL) apply -f $(ADMINUI_K8S)/
	$(KUBECTL) apply -f $(AGENT_DIR)/k8s/
	$(KUBECTL) apply -f $(INCIDENT_DIR)/k8s/
	$(KUBECTL) apply -f $(PARTICIPANT_DIR)/k8s/
	$(KUBECTL) apply -f $(ADMINSVC_DIR)/k8s/
	@echo "✅ All manifests applied."

status:
	@echo "\n📊 Pod status:"
	$(KUBECTL) get pods -o wide
	@echo "\n📊 Deployments:"
	$(KUBECTL) get deploy

logs:
ifndef SVC
	@echo "Usage: make logs SVC=chatbot-service"
	@exit 1
endif
	$(KUBECTL) logs -l app=$(SVC) --tail=100 -f

restart:
	@echo "\n🔄 Rolling restart all services..."
	$(KUBECTL) rollout restart deploy/chatbot-service deploy/graph-core deploy/chatbot-ui deploy/admin-ui deploy/agent-service deploy/incident-service deploy/participant-service deploy/admin-service
	$(KUBECTL) rollout status deploy/chatbot-service deploy/graph-core deploy/chatbot-ui deploy/admin-ui deploy/agent-service deploy/incident-service deploy/participant-service deploy/admin-service --timeout=$(TIMEOUT)
	@echo "✅ All services restarted."

clean:
	@echo "\n🧹 Removing local images..."
	-docker rmi $(CHATBOT_IMG) $(GRAPH_IMG) $(CHATUI_IMG) $(ADMINUI_IMG) $(AGENT_IMG) $(INCIDENT_IMG) $(PARTICIPANT_IMG) $(ADMINSVC_IMG) 2>/dev/null
	@echo "✅ Clean."

# ============================================================
# Local Development Workflow
# ============================================================

local-up:
	@echo "\n🚀 Starting local Kind cluster..."
	cd survivor-infra && terraform init && terraform apply -auto-approve
	@echo "✅ Cluster ready. Run 'make all' to deploy services."

local-down:
	@echo "\n🛑 Destroying local Kind cluster..."
	kind delete cluster --name $(CLUSTER)
	@echo "✅ Cluster destroyed."

local-build: all

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
# Health Checks
# ============================================================

health:
	@echo "\n🏥 Health checks:"
	@curl -sf http://chatbot-service.127.0.0.1.nip.io/health && echo " ✅ chatbot-service" || echo " ❌ chatbot-service"
	@curl -sf http://graph-core.127.0.0.1.nip.io/health && echo " ✅ graph-core" || echo " ❌ graph-core"
	@curl -sf http://agent-service.127.0.0.1.nip.io/health 2>/dev/null && echo " ✅ agent-service" || echo " ⚠️  agent-service (internal only, no ingress)"
	@curl -sf http://incident-service.127.0.0.1.nip.io/health && echo " ✅ incident-service" || echo " ❌ incident-service"
	@curl -sf http://participant-service.127.0.0.1.nip.io/health && echo " ✅ participant-service" || echo " ❌ participant-service"
	@curl -sf http://admin-service.127.0.0.1.nip.io/health && echo " ✅ admin-service" || echo " ❌ admin-service"
	@curl -sf http://admin-ui.127.0.0.1.nip.io/health && echo " ✅ admin-ui" || echo " ❌ admin-ui"
	@curl -sf http://chatbot-ui.127.0.0.1.nip.io/ >/dev/null && echo " ✅ chatbot-ui" || echo " ❌ chatbot-ui"

# ============================================================
# Cloud Deployment
# ============================================================

cloud-dev-plan:
	@echo "\n📋 Planning cloud dev infrastructure..."
	cd infra/cloud/dev && terraform init && terraform plan

cloud-dev-apply:
	@echo "\n🏗️ Applying cloud dev infrastructure..."
	cd infra/cloud/dev && terraform init && terraform apply

deploy-dev:
	@echo "\n🚀 Deploying to cloud dev with Helm..."
	helm upgrade --install survivor-network \
		platform/helm/survivor-network \
		-f platform/helm/survivor-network/values-dev.yaml \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait --timeout 5m

deploy-local-helm:
	@echo "\n🚀 Deploying locally with Helm..."
	helm upgrade --install survivor-network \
		platform/helm/survivor-network \
		-f platform/helm/survivor-network/values-local.yaml \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait --timeout 5m
