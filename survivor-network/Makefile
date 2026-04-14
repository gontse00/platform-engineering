CLUSTER     := survivor-net
NAMESPACE   := survivor-apps
CONTEXT     := kind-$(CLUSTER)
KUBECTL     := kubectl --context $(CONTEXT) -n $(NAMESPACE)
TIMEOUT     := 120s

CHATBOT_IMG   := chatbot-service:latest
GRAPH_IMG     := graph-core:latest
CHATUI_IMG    := chatbot-ui:latest
ADMIN_IMG     := survivor-net/admin-ui:latest

CHATBOT_DIR   := ./chatbot-service
GRAPH_DIR     := ./graph-core/backend
CHATUI_DIR    := ./chatbot-ui-service
ADMIN_DIR     := ./admin-ui

CHATBOT_K8S   := $(CHATBOT_DIR)/k8s
GRAPH_K8S     := $(GRAPH_DIR)/deploy
CHATUI_K8S    := $(CHATUI_DIR)/k8s
ADMIN_K8S     := $(ADMIN_DIR)/k8s

.PHONY: all chatbot graph chatbot-ui admin deploy status logs restart clean help

all: chatbot graph chatbot-ui admin
	@echo "\n✅ All services built and deployed."

help:
	@echo "make all          — build + deploy everything"
	@echo "make chatbot      — chatbot-service"
	@echo "make graph        — graph-core"
	@echo "make chatbot-ui   — chatbot UI"
	@echo "make admin        — admin UI"
	@echo "make deploy       — apply manifests only (no build)"
	@echo "make status       — pod status"
	@echo "make logs SVC=x   — tail logs"
	@echo "make restart      — rolling restart all"
	@echo "make clean        — remove docker images"

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

admin:
	@echo "\n🔨 Building admin-ui..."
	cd $(ADMIN_DIR) && npm install && cd ..
	docker build -t $(ADMIN_IMG) $(ADMIN_DIR)
	kind load docker-image $(ADMIN_IMG) --name $(CLUSTER)
	$(KUBECTL) apply -f $(ADMIN_K8S)/
	$(KUBECTL) rollout restart deploy/admin-ui
	$(KUBECTL) rollout status deploy/admin-ui --timeout=$(TIMEOUT)
	@echo "✅ admin-ui deployed."

deploy:
	@echo "\n📦 Applying all manifests..."
	$(KUBECTL) apply -f $(CHATBOT_K8S)/
	$(KUBECTL) apply -f $(GRAPH_K8S)/graph-core.yaml
	$(KUBECTL) apply -f $(CHATUI_K8S)/
	$(KUBECTL) apply -f $(ADMIN_K8S)/
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
	$(KUBECTL) rollout restart deploy/chatbot-service deploy/graph-core deploy/chatbot-ui deploy/admin-ui
	$(KUBECTL) rollout status deploy/chatbot-service deploy/graph-core deploy/chatbot-ui deploy/admin-ui --timeout=$(TIMEOUT)
	@echo "✅ All services restarted."

clean:
	@echo "\n🧹 Removing local images..."
	-docker rmi $(CHATBOT_IMG) $(GRAPH_IMG) $(CHATUI_IMG) $(ADMIN_IMG) 2>/dev/null
	@echo "✅ Clean."