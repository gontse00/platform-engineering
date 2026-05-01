# ============================================================
# Survivor Network — Makefile
# ============================================================
# --- Local Kind ---
CLUSTER     := survivor-net
NAMESPACE   := survivor-apps
CONTEXT     := kind-$(CLUSTER)
KUBECTL_CLUSTER := kubectl --context $(CONTEXT)
KUBECTL     := $(KUBECTL_CLUSTER) -n $(NAMESPACE)
TIMEOUT     := 120s
HELM_CHART  := platform/helm/survivor-network
HELM_VALUES := $(HELM_CHART)/values-local.yaml

# --- Cloud Dev (GCP) ---
GCP_PROJECT        ?= survivor-rescue-net-dev
GCP_REGION         ?= europe-west2
GCP_ZONE           ?= europe-west2-a
GKE_CLUSTER        ?= survivor-network-dev
AR_REPO            ?= survivor-network
IMAGE_TAG          ?= dev
REGISTRY           ?= $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(AR_REPO)
DOCKER_PLATFORM    ?= linux/amd64
BUILDX_BUILDER     ?= survivor-builder
CLOUD_SQL_INSTANCE ?= survivor-network-dev-db
CLOUD_SQL_DATABASE ?= survivor
CLOUD_SQL_USER     ?= survivor
DEV_NAMESPACE      ?= survivor-apps
TF_DEV_DIR         := infra/cloud/dev
TF_APPLY_PLAN      := tfplan
TF_DESTROY_PLAN    := destroy.tfplan
CLOUD_DEV_STRICT   ?= false
CLOUD_DEV_NAMESPACES := survivor-apps ingress-nginx cert-manager external-secrets observability
SMOKE_DEV_SERVICES ?= chatbot-service graph-core incident-service participant-service admin-service agent-service
SMOKE_CURL_IMAGE   ?= curlimages/curl
CLOUD_DEV_SHUTDOWN_TIMEOUT ?= 180s
APP_LABEL_SELECTOR ?= app.kubernetes.io/part-of=survivor-network
CLOUD_DEV_DOMAIN ?= dev.rescuenet.co.za
GCP_SECRET_DB_URL ?= survivor-db-url
CLOUD_SQL_CONNECTION_NAME ?= $(GCP_PROJECT):$(GCP_REGION):$(CLOUD_SQL_INSTANCE)
CONFIRM_PROD_TLS ?= false

# Bootstrap Helm configuration
INGRESS_NGINX_NAMESPACE ?= ingress-nginx
INGRESS_NGINX_RELEASE   ?= ingress-nginx
INGRESS_NGINX_CHART     ?= ingress-nginx/ingress-nginx
INGRESS_NGINX_TIMEOUT   ?= 10m
INGRESS_NGINX_LB_WAIT_SECONDS ?= 600
INGRESS_NGINX_CPU_REQUEST    ?= 100m
INGRESS_NGINX_MEMORY_REQUEST ?= 128Mi
INGRESS_NGINX_CPU_LIMIT      ?= 500m
INGRESS_NGINX_MEMORY_LIMIT   ?= 512Mi
INGRESS_NGINX_EXTRA_SET      ?=

CERT_MANAGER_NAMESPACE ?= cert-manager
CERT_MANAGER_RELEASE   ?= cert-manager
CERT_MANAGER_CHART     ?= jetstack/cert-manager
CERT_MANAGER_TIMEOUT   ?= 10m
CERT_MANAGER_EXTRA_SET ?=

EXTERNAL_SECRETS_NAMESPACE ?= external-secrets
EXTERNAL_SECRETS_RELEASE   ?= external-secrets
EXTERNAL_SECRETS_CHART     ?= external-secrets/external-secrets
EXTERNAL_SECRETS_TIMEOUT   ?= 10m
EXTERNAL_SECRETS_EXTRA_SET ?=

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
        cloud-dev-init cloud-dev-fmt cloud-dev-validate cloud-dev-plan cloud-dev-apply cloud-dev-plan-destroy cloud-dev-destroy \
        cloud-dev-pre-destroy cloud-dev-pre-destroy-check cloud-dev-shutdown-apps cloud-dev-uninstall-apps cloud-dev-drain-db cloud-dev-clean-db-owned cloud-dev-destroy-safe cloud-dev-destroy-safe-check \
        cloud-dev-bootstrap cloud-dev-platform-ready cloud-dev-kubeconfig cloud-dev-kubeconfig-if-present cloud-dev-create-namespaces cloud-dev-install-ingress \
        cloud-dev-install-cert-manager cloud-dev-install-external-secrets cloud-dev-create-db-secret cloud-dev-create-db-secret-from-tf \
        cloud-dev-bootstrap-verify cloud-dev-buildx-bootstrap cloud-dev-verify-images cloud-dev-restart-apps cloud-dev-full-recreate \
        cloud-dev-dns-info cloud-dev-tls-apply-staging-issuer cloud-dev-tls-apply-prod-issuer cloud-dev-tls-verify \
        cloud-dev-secret-create-db-url cloud-dev-secret-put-db-url cloud-dev-secret-describe-db-url \
        cloud-dev-external-secrets-apply cloud-dev-external-secrets-verify cloud-dev-sql-info \
        deploy-dev kubeconfig-dev cloud-dev-build-push cloud-dev-authorize-sql cloud-dev-create-secrets \
        helm-template-dev smoke-dev-internal smoke-dev-internal-verbose cloud-dev-recreate \
        terraform-state-bucket-create terraform-state-enable-versioning terraform-state-migrate \
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
	@echo "  make restart-service SVC=x — restart one service"
	@echo "  make local-reset        — clear test cases"
	@echo "  make clear-local-cases  — alias for local-reset"
	@echo "  make e2e-local          — run E2E quality checks"
	@echo "  make e2e-admin          — run admin workflow E2E"
	@echo "  make e2e-admin-local    — alias for e2e-admin"
	@echo "  make init-chatbot-db    — create chatbot DB tables manually"
	@echo "  make clean-start-local  — full rebuild + init + test"
	@echo ""
	@echo "=== Cloud Dev (GCP) ==="
	@echo "  make cloud-dev-init     — terraform init"
	@echo "  make cloud-dev-fmt      — terraform fmt"
	@echo "  make cloud-dev-validate — terraform validate"
	@echo "  make cloud-dev-plan     — plan + save to tfplan"
	@echo "  make cloud-dev-apply    — apply saved tfplan"
	@echo "  make cloud-dev-plan-destroy — plan destroy + save"
	@echo "  make cloud-dev-destroy  — apply saved destroy plan"
	@echo "  make cloud-dev-pre-destroy — gracefully stop apps before destroy"
	@echo "  make cloud-dev-pre-destroy-check — inspect pre-destroy state without mutating"
	@echo "  make cloud-dev-clean-db-owned — drop DB objects owned by the app role before destroy"
	@echo "  make cloud-dev-destroy-safe — pre-destroy + plan destroy + destroy"
	@echo "  make cloud-dev-destroy-safe-check — print safe destroy flow without mutating"
	@echo "  make cloud-dev-bootstrap — bootstrap GKE add-ons and app prerequisites"
	@echo "  make cloud-dev-platform-ready — canonical post-Terraform cluster bootstrap"
	@echo "  make cloud-dev-kubeconfig — get GKE credentials"
	@echo "  make kubeconfig-dev     — compatibility alias for cloud-dev-kubeconfig"
	@echo "  make cloud-dev-buildx-bootstrap — create/use Docker Buildx builder"
	@echo "  make cloud-dev-build-push — build + push all images"
	@echo "  make cloud-dev-verify-images — list and inspect Artifact Registry images"
	@echo "  make cloud-dev-restart-apps — restart app deployments and watch pods"
	@echo "  make cloud-dev-authorize-sql — authorize GKE→Cloud SQL"
	@echo "  make cloud-dev-create-db-secret — create DB secret from DATABASE_URL"
	@echo "  make cloud-dev-create-db-secret-from-tf — create DB secret from Terraform output"
	@echo "  make cloud-dev-create-secrets — legacy interactive DB secret fallback"
	@echo "  make cloud-dev-dns-info — print rescuenet.co.za DNS records and ingress IP"
	@echo "  make cloud-dev-tls-verify — inspect cert-manager issuers/certificates"
	@echo "  make cloud-dev-secret-create-db-url — create Secret Manager DB secret shell"
	@echo "  make cloud-dev-secret-put-db-url — add DATABASE_URL as Secret Manager version"
	@echo "  make cloud-dev-external-secrets-verify — inspect External Secrets status"
	@echo "  make cloud-dev-sql-info — print Cloud SQL public/Auth Proxy migration info"
	@echo "  make helm-template-dev  — render dev Helm templates"
	@echo "  make deploy-dev         — helm deploy to cloud dev"
	@echo "  make smoke-dev-internal — health check pods internally"
	@echo "  make smoke-dev-internal-verbose — verbose internal health checks"
	@echo "  make cloud-dev-full-recreate — plan/apply/bootstrap/build/deploy/smoke"
	@echo "  make cloud-dev-recreate — full teardown + recreate"

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
	@$(KUBECTL) run curl-test --image=curlimages/curl --rm -i --restart=Never --command -- \
		curl -sf http://agent-service:8080/health 2>/dev/null && echo " ✅ agent-service (internal)" || echo " ⚠️  agent-service (could not verify internally)"

# ============================================================
# Tests & Simulations
# ============================================================

local-test:
	@echo "\n🧪 Running tests..."
	cd chatbot-service && python3 -m pytest tests/ -v
	cd agent-service && python3 -m pytest tests/ -v
	cd admin-service && python3 -m pytest tests/ -v
	cd incident-service && python3 -m pytest tests/ -v

local-sim:
	python3 tests/load/disaster_sim.py --users 10 --ramp-up 5

local-sim-full:
	python3 tests/load/full_flow_sim.py --survivors 20 --helpers 10 --ramp-up 5

local-sim-100:
	python3 tests/load/disaster_sim.py --users 100 --ramp-up 60

local-reset:
	@echo "\n🗑️  Resetting test data..."
	@curl -sf -X DELETE http://incident-service.127.0.0.1.nip.io/dev/reset-cases && echo " ✅ Cases reset" || echo " ❌ Reset failed"

clear-local-cases: local-reset

e2e-local:
	@echo "\n🔬 Running local E2E verification..."
	@echo "  Resetting..."
	@curl -sf -X DELETE http://incident-service.127.0.0.1.nip.io/dev/reset-cases > /dev/null
	@echo "  Testing known high-risk case (sexual assault)..."
	@curl -sf -X POST http://incident-service.127.0.0.1.nip.io/cases/from-intake \
		-H 'Content-Type: application/json' \
		-d '{"session_id":"e2e-test-sexual-assault","message":"I was raped last night in Hillbrow","location_text":"Hillbrow","urgency":"medium","safety_risk":"low","immediate_danger":false}' | \
		python3 -c "\
	import sys, json; c = json.load(sys.stdin); \
	assert c['urgency'] in ('urgent','critical'), f'Expected urgent+, got {c[\"urgency\"]}'; \
	assert c['safety_risk'] in ('high','immediate'), f'Expected high+, got {c[\"safety_risk\"]}'; \
	assert c['incident_type'] is not None, 'incident_type is null'; \
	assert len(c['needs']) > 0, 'needs is empty'; \
	print(f'  ✅ Sexual assault: urgency={c[\"urgency\"]}, safety={c[\"safety_risk\"]}, type={c[\"incident_type\"]}, needs={c[\"needs\"]}')"
	@echo "  Testing known critical case (stabbing)..."
	@curl -sf -X POST http://incident-service.127.0.0.1.nip.io/cases/from-intake \
		-H 'Content-Type: application/json' \
		-d '{"session_id":"e2e-test-stabbing","message":"I was stabbed and I am bleeding heavily","urgency":"medium","safety_risk":"low","immediate_danger":true}' | \
		python3 -c "\
	import sys, json; c = json.load(sys.stdin); \
	assert c['urgency'] == 'critical', f'Expected critical, got {c[\"urgency\"]}'; \
	assert c['safety_risk'] == 'immediate', f'Expected immediate, got {c[\"safety_risk\"]}'; \
	assert 'Emergency Medical' in c['needs'], f'Missing Emergency Medical in {c[\"needs\"]}'; \
	print(f'  ✅ Stabbing: urgency={c[\"urgency\"]}, safety={c[\"safety_risk\"]}, needs={c[\"needs\"]}')"
	@echo "  Testing idempotency (duplicate session)..."
	@curl -sf -X POST http://incident-service.127.0.0.1.nip.io/cases/from-intake \
		-H 'Content-Type: application/json' \
		-d '{"session_id":"e2e-test-stabbing","message":"duplicate call","urgency":"standard","safety_risk":"low"}' | \
		python3 -c "\
	import sys, json; c = json.load(sys.stdin); \
	assert c['urgency'] == 'critical', 'Idempotency failed — got different case'; \
	print('  ✅ Idempotency: duplicate returned existing case')"
	@echo "  Running 10-user simulation..."
	@python3 tests/load/disaster_sim.py --users 10 --ramp-up 5 > /dev/null 2>&1
	@echo "  Checking aggregate case quality..."
	@curl -sf "http://incident-service.127.0.0.1.nip.io/cases?limit=50" | python3 -c "\
	import sys, json; \
	d = json.load(sys.stdin); \
	cases = d['cases']; \
	total = len(cases); \
	with_type = sum(1 for c in cases if c.get('incident_type')); \
	with_needs = sum(1 for c in cases if c.get('needs')); \
	critical = sum(1 for c in cases if c.get('urgency') in ('critical', 'urgent')); \
	triaging = sum(1 for c in cases if c.get('status') == 'triaging'); \
	print(f'  Cases: {total}'); \
	print(f'  With incident_type: {with_type}/{total}'); \
	print(f'  With needs: {with_needs}/{total}'); \
	print(f'  Urgent/critical: {critical}/{total}'); \
	print(f'  Auto-triaging: {triaging}/{total}'); \
	assert total > 0, 'No cases created'; \
	print('  ✅ E2E verification passed')"

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

restart-service:
ifndef SVC
	@echo "Usage: make restart-service SVC=incident-service"
	@exit 1
endif
	@echo "\n🔄 Restarting $(SVC)..."
	$(KUBECTL) rollout restart deploy/$(SVC)
	$(KUBECTL) rollout status deploy/$(SVC) --timeout=$(TIMEOUT)
	@echo "✅ $(SVC) restarted."

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
# Cloud Dev (GCP) — Full Automation
# ============================================================

cloud-dev-init:
	cd $(TF_DEV_DIR) && terraform init

cloud-dev-fmt:
	terraform fmt -recursive infra/

cloud-dev-validate:
	cd $(TF_DEV_DIR) && terraform validate

cloud-dev-plan:
	@echo "\n📋 Planning cloud-dev infrastructure..."
	cd $(TF_DEV_DIR) && terraform init && terraform plan -out=$(TF_APPLY_PLAN)
	@echo "✅ Plan saved to $(TF_DEV_DIR)/$(TF_APPLY_PLAN)"
	@echo "   Review with: cd $(TF_DEV_DIR) && terraform show $(TF_APPLY_PLAN)"
	@echo "   Apply with:  make cloud-dev-apply"

cloud-dev-apply:
	@echo "\n🏗️  Applying saved plan..."
	cd $(TF_DEV_DIR) && terraform apply $(TF_APPLY_PLAN)
	@echo "✅ Infrastructure applied."

cloud-dev-plan-destroy:
	@echo "\n⚠️  Planning infrastructure DESTROY..."
	cd $(TF_DEV_DIR) && terraform plan -destroy -out=$(TF_DESTROY_PLAN)
	@echo "✅ Destroy plan saved to $(TF_DEV_DIR)/$(TF_DESTROY_PLAN)"
	@echo "   Review with: cd $(TF_DEV_DIR) && terraform show $(TF_DESTROY_PLAN)"
	@echo "   Destroy with: make cloud-dev-destroy"

cloud-dev-destroy:
	@echo "\n🛑 Applying saved destroy plan..."
	cd $(TF_DEV_DIR) && terraform apply $(TF_DESTROY_PLAN)
	@echo "✅ Infrastructure destroyed."

cloud-dev-pre-destroy: cloud-dev-kubeconfig-if-present cloud-dev-shutdown-apps cloud-dev-drain-db cloud-dev-clean-db-owned cloud-dev-uninstall-apps
	@echo "\nSUCCESS: Cloud dev pre-destroy shutdown complete."

cloud-dev-pre-destroy-check:
	@echo "\nINFO: Pre-destroy dry-run checklist for cloud-dev."
	@echo "INFO: Real pre-destroy command sequence:"
	@echo "      make cloud-dev-kubeconfig-if-present"
	@echo "      make cloud-dev-shutdown-apps"
	@echo "      make cloud-dev-drain-db"
	@echo "      make cloud-dev-clean-db-owned"
	@echo "      make cloud-dev-uninstall-apps"
	@echo "\nINFO: Current Kubernetes context:"
	@kubectl config current-context || true
	@echo "\nINFO: Helm release status:"
	@helm status survivor-network -n $(DEV_NAMESPACE) || true
	@echo "\nINFO: App-managed resources using selector $(APP_LABEL_SELECTOR):"
	@kubectl -n $(DEV_NAMESPACE) get deploy,svc,ingress,configmap,secret -l $(APP_LABEL_SELECTOR) -o wide || true
	@echo "\nINFO: Current pods in $(DEV_NAMESPACE):"
	@kubectl -n $(DEV_NAMESPACE) get pods -o wide || true
	@echo "\nINFO: Terraform destroy plan command:"
	@echo "      make cloud-dev-plan-destroy"
	@echo "WARN: This check target does not scale, delete, uninstall, or destroy anything."

cloud-dev-shutdown-apps:
	@echo "\nINFO: Scaling application deployments in $(DEV_NAMESPACE) to zero..."
	@set -e; \
	if ! kubectl get namespace $(DEV_NAMESPACE) >/dev/null 2>&1; then \
		echo "WARN: Namespace $(DEV_NAMESPACE) does not exist; no app deployments to shut down."; \
		exit 0; \
	fi; \
	if ! kubectl -n $(DEV_NAMESPACE) get deploy >/dev/null 2>&1; then \
		echo "WARN: Could not list deployments in $(DEV_NAMESPACE)."; \
		exit 1; \
	fi; \
	if [ -z "$$(kubectl -n $(DEV_NAMESPACE) get deploy -o name)" ]; then \
		echo "INFO: No deployments found in $(DEV_NAMESPACE)."; \
	else \
		kubectl -n $(DEV_NAMESPACE) scale deploy --all --replicas=0; \
	fi; \
	echo "INFO: Waiting for application pods to terminate..."; \
	if [ -z "$$(kubectl -n $(DEV_NAMESPACE) get pods -o name)" ]; then \
		echo "SUCCESS: No application pods remain in $(DEV_NAMESPACE)."; \
	elif kubectl -n $(DEV_NAMESPACE) wait --for=delete pod --all --timeout=$(CLOUD_DEV_SHUTDOWN_TIMEOUT); then \
		echo "SUCCESS: Application pods terminated."; \
	else \
		echo "ERROR: Timed out waiting for application pods to terminate."; \
		echo "INFO: Remaining pods:"; \
		kubectl -n $(DEV_NAMESPACE) get pods -o wide || true; \
		echo "INFO: Recent namespace events:"; \
		kubectl -n $(DEV_NAMESPACE) get events --sort-by=.lastTimestamp | tail -n 30 || true; \
		exit 1; \
	fi

cloud-dev-uninstall-apps:
	@echo "\nINFO: Uninstalling Helm release survivor-network from $(DEV_NAMESPACE)..."
	@set -e; \
	if helm status survivor-network -n $(DEV_NAMESPACE) >/dev/null 2>&1; then \
		helm uninstall survivor-network -n $(DEV_NAMESPACE); \
		echo "SUCCESS: Helm release survivor-network uninstalled."; \
	else \
		echo "WARN: Helm release survivor-network is not installed in $(DEV_NAMESPACE); skipping uninstall."; \
	fi; \
	echo "INFO: Verifying application Kubernetes resources are removed..."; \
	if kubectl get namespace $(DEV_NAMESPACE) >/dev/null 2>&1; then \
		kubectl -n $(DEV_NAMESPACE) get deploy,svc,ingress,configmap,secret -l $(APP_LABEL_SELECTOR) || true; \
		if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get deploy -l $(APP_LABEL_SELECTOR) -o name 2>/dev/null)" ]; then \
			echo "ERROR: App-managed deployments still exist after Helm uninstall."; \
			kubectl -n $(DEV_NAMESPACE) get deploy -l $(APP_LABEL_SELECTOR) -o wide || true; \
			exit 1; \
		fi; \
		if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get svc -l $(APP_LABEL_SELECTOR) -o name 2>/dev/null)" ]; then \
			echo "ERROR: App-managed services still exist after Helm uninstall."; \
			kubectl -n $(DEV_NAMESPACE) get svc -l $(APP_LABEL_SELECTOR) -o wide || true; \
			exit 1; \
		fi; \
		if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get ingress -l $(APP_LABEL_SELECTOR) -o name 2>/dev/null)" ]; then \
			echo "ERROR: App-managed ingress resources still exist after Helm uninstall."; \
			kubectl -n $(DEV_NAMESPACE) get ingress -l $(APP_LABEL_SELECTOR) -o wide || true; \
			exit 1; \
		fi; \
		if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get configmap -l $(APP_LABEL_SELECTOR) -o name 2>/dev/null)" ]; then \
			echo "ERROR: App-managed configmaps still exist after Helm uninstall."; \
			kubectl -n $(DEV_NAMESPACE) get configmap -l $(APP_LABEL_SELECTOR) || true; \
			exit 1; \
		fi; \
		if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get secret -l $(APP_LABEL_SELECTOR) -o name 2>/dev/null)" ]; then \
			echo "ERROR: App-managed secrets still exist after Helm uninstall."; \
			kubectl -n $(DEV_NAMESPACE) get secret -l $(APP_LABEL_SELECTOR) || true; \
			exit 1; \
		fi; \
		echo "SUCCESS: App-managed deployments, services, ingresses, configmaps, and secrets are removed."; \
	else \
		echo "SUCCESS: Namespace $(DEV_NAMESPACE) is already absent."; \
	fi

cloud-dev-drain-db:
	@echo "\nINFO: Verifying Kubernetes app workloads have drained DB connections..."
	@set -e; \
	if ! kubectl get namespace $(DEV_NAMESPACE) >/dev/null 2>&1; then \
		echo "SUCCESS: Namespace $(DEV_NAMESPACE) does not exist; no app pods remain."; \
		exit 0; \
	fi; \
	echo "INFO: Current pod status:"; \
	kubectl -n $(DEV_NAMESPACE) get pods -o wide || true; \
	if [ -n "$$(kubectl -n $(DEV_NAMESPACE) get pods -o name 2>/dev/null)" ]; then \
		echo "ERROR: Application pods still exist in $(DEV_NAMESPACE); DB connections may still be active."; \
		echo "INFO: Run make cloud-dev-shutdown-apps again, then inspect remaining pods."; \
		exit 1; \
	fi; \
	echo "INFO: Remaining services/endpoints:"; \
	kubectl -n $(DEV_NAMESPACE) get svc,endpoints || true; \
	echo "SUCCESS: No application pods remain in $(DEV_NAMESPACE)."

cloud-dev-clean-db-owned:
	@echo "\nINFO: Cleaning PostgreSQL objects owned by role $(CLOUD_SQL_USER) before Cloud SQL user deletion..."
	@set -e; \
	DB_URL="$${DATABASE_URL:-}"; \
	if [ -z "$$DB_URL" ]; then \
		DB_URL="$$(kubectl -n $(DEV_NAMESPACE) get secret survivor-db-url -o jsonpath='{.data.DATABASE_URL}' 2>/dev/null | base64 --decode || true)"; \
	fi; \
	if [ -z "$$DB_URL" ]; then \
		DB_URL="$$(cd $(TF_DEV_DIR) && terraform output -raw database_connection_string 2>/dev/null || true)"; \
	fi; \
	if [ -z "$$DB_URL" ]; then \
		echo "ERROR: Could not determine DATABASE_URL from environment, Kubernetes secret, or Terraform output."; \
		echo "INFO: Pass it explicitly:"; \
		echo "      DATABASE_URL='postgresql+psycopg2://survivor:password@ip:5432/survivor' make cloud-dev-clean-db-owned"; \
		exit 1; \
	fi; \
	if kubectl get namespace $(DEV_NAMESPACE) >/dev/null 2>&1; then \
		echo "INFO: Running DB cleanup from a temporary Kubernetes pod."; \
		kubectl -n $(DEV_NAMESPACE) delete pod db-destroy-cleanup --ignore-not-found --wait=false >/dev/null 2>&1 || true; \
		kubectl -n $(DEV_NAMESPACE) run db-destroy-cleanup \
			--image=postgres:16-alpine \
			--rm -i \
			--restart=Never \
			--env="DATABASE_URL=$$DB_URL" \
			--env="DB_OWNER=$(CLOUD_SQL_USER)" \
			--command -- sh -c 'PSQL_URL=$$(printf "%s" "$$DATABASE_URL" | sed "s#^postgresql+[^:]*://#postgresql://#"); echo "INFO: Dropping objects owned by role $$DB_OWNER in database $(CLOUD_SQL_DATABASE)..."; psql "$$PSQL_URL" -v ON_ERROR_STOP=1 -c "DROP OWNED BY \"$$DB_OWNER\" CASCADE;"'; \
	elif command -v docker >/dev/null 2>&1; then \
		echo "WARN: Kubernetes is unavailable; running DB cleanup with local Docker."; \
		docker run --rm \
			-e "DATABASE_URL=$$DB_URL" \
			-e "DB_OWNER=$(CLOUD_SQL_USER)" \
			postgres:16-alpine \
			sh -c 'PSQL_URL=$$(printf "%s" "$$DATABASE_URL" | sed "s#^postgresql+[^:]*://#postgresql://#"); echo "INFO: Dropping objects owned by role $$DB_OWNER in database $(CLOUD_SQL_DATABASE)..."; psql "$$PSQL_URL" -v ON_ERROR_STOP=1 -c "DROP OWNED BY \"$$DB_OWNER\" CASCADE;"'; \
	elif command -v psql >/dev/null 2>&1; then \
		echo "WARN: Kubernetes is unavailable; running DB cleanup with local psql."; \
		PSQL_URL="$$(printf "%s" "$$DB_URL" | sed "s#^postgresql+[^:]*://#postgresql://#")"; \
		psql "$$PSQL_URL" -v ON_ERROR_STOP=1 -c "DROP OWNED BY \"$(CLOUD_SQL_USER)\" CASCADE;"; \
	else \
		echo "ERROR: Kubernetes is unavailable and neither docker nor psql is installed locally."; \
		echo "INFO: Install Docker or psql, or run from an environment that can reach Cloud SQL."; \
		exit 1; \
	fi; \
	echo "SUCCESS: PostgreSQL objects owned by role $(CLOUD_SQL_USER) were dropped."

cloud-dev-destroy-safe:
	@echo "\nINFO: Running safe cloud-dev destroy workflow..."
	$(MAKE) cloud-dev-pre-destroy
	$(MAKE) cloud-dev-plan-destroy
	$(MAKE) cloud-dev-destroy
	@echo "\nSUCCESS: Safe cloud-dev destroy complete."

cloud-dev-destroy-safe-check:
	@echo "\nINFO: Safe destroy dry-run checklist for cloud-dev."
	@echo "INFO: Real safe destroy command sequence:"
	@echo "      make cloud-dev-pre-destroy"
	@echo "      make cloud-dev-plan-destroy"
	@echo "      cd $(TF_DEV_DIR) && terraform show $(TF_DESTROY_PLAN)"
	@echo "      make cloud-dev-destroy"
	@echo "\nINFO: Inspecting current pre-destroy state:"
	@$(MAKE) cloud-dev-pre-destroy-check
	@echo "\nWARN: Review the saved destroy plan before applying it."
	@echo "WARN: This check target does not scale, delete, uninstall, plan, or destroy anything."

cloud-dev-bootstrap: cloud-dev-platform-ready
	@echo "\nSUCCESS: Cloud dev bootstrap complete."

cloud-dev-platform-ready: cloud-dev-kubeconfig cloud-dev-create-namespaces cloud-dev-install-ingress cloud-dev-install-cert-manager cloud-dev-install-external-secrets cloud-dev-authorize-sql cloud-dev-create-db-secret cloud-dev-bootstrap-verify
	@echo "\nSUCCESS: Cloud dev platform is ready."

cloud-dev-kubeconfig:
	@echo "\nINFO: Refreshing kubeconfig for $(GKE_CLUSTER) in $(GCP_ZONE)..."
	gcloud container clusters get-credentials $(GKE_CLUSTER) --zone $(GCP_ZONE) --project $(GCP_PROJECT)
	@echo "SUCCESS: kubeconfig refreshed."

cloud-dev-kubeconfig-if-present:
	@echo "\nINFO: Refreshing kubeconfig for $(GKE_CLUSTER) in $(GCP_ZONE) if the cluster exists..."
	@set -e; \
	if gcloud container clusters describe $(GKE_CLUSTER) --zone $(GCP_ZONE) --project $(GCP_PROJECT) >/dev/null 2>&1; then \
		gcloud container clusters get-credentials $(GKE_CLUSTER) --zone $(GCP_ZONE) --project $(GCP_PROJECT); \
		echo "SUCCESS: kubeconfig refreshed."; \
	else \
		echo "WARN: GKE cluster $(GKE_CLUSTER) was not found; skipping Kubernetes cleanup steps that require a live cluster."; \
	fi

kubeconfig-dev: cloud-dev-kubeconfig

cloud-dev-create-namespaces:
	@echo "\nINFO: Creating cloud-dev namespaces..."
	@for ns in $(CLOUD_DEV_NAMESPACES); do \
		echo "INFO: Ensuring namespace $$ns..."; \
		kubectl create namespace $$ns --dry-run=client -o yaml | kubectl apply -f -; \
	done
	@echo "SUCCESS: Namespaces ready."

cloud-dev-install-ingress:
	@echo "\nINFO: Installing ingress-nginx..."
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx || true
	helm repo update
	helm upgrade --install $(INGRESS_NGINX_RELEASE) $(INGRESS_NGINX_CHART) \
		--namespace $(INGRESS_NGINX_NAMESPACE) \
		--create-namespace \
		--set controller.service.type=LoadBalancer \
		--set controller.metrics.enabled=true \
		--set controller.resources.requests.cpu=$(INGRESS_NGINX_CPU_REQUEST) \
		--set controller.resources.requests.memory=$(INGRESS_NGINX_MEMORY_REQUEST) \
		--set controller.resources.limits.cpu=$(INGRESS_NGINX_CPU_LIMIT) \
		--set controller.resources.limits.memory=$(INGRESS_NGINX_MEMORY_LIMIT) \
		$(INGRESS_NGINX_EXTRA_SET) \
		--wait \
		--timeout $(INGRESS_NGINX_TIMEOUT)
	@echo "INFO: Verifying ingress-nginx controller rollout..."
	kubectl -n $(INGRESS_NGINX_NAMESPACE) rollout status deploy/$(INGRESS_NGINX_RELEASE)-controller --timeout=$(INGRESS_NGINX_TIMEOUT)
	kubectl -n $(INGRESS_NGINX_NAMESPACE) wait pod \
		-l app.kubernetes.io/name=ingress-nginx,app.kubernetes.io/component=controller \
		--for=condition=Ready \
		--timeout=$(INGRESS_NGINX_TIMEOUT)
	@echo "INFO: Verifying ingress-nginx LoadBalancer service..."
	@set -e; \
	if ! kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller >/dev/null 2>&1; then \
		echo "ERROR: ingress-nginx controller service is missing."; \
		kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc -o wide || true; \
		exit 1; \
	fi; \
	if [ "$$(kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller -o jsonpath='{.spec.type}')" != "LoadBalancer" ]; then \
		echo "ERROR: ingress-nginx controller service is not type LoadBalancer."; \
		kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller -o wide; \
		exit 1; \
	fi; \
	deadline=$$(($$(date +%s) + $(INGRESS_NGINX_LB_WAIT_SECONDS))); \
	while true; do \
		lb="$$(kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)"; \
		if [ -n "$$lb" ]; then \
			echo "SUCCESS: ingress-nginx LoadBalancer is ready: $$lb"; \
			break; \
		fi; \
		if [ "$$(date +%s)" -ge "$$deadline" ]; then \
			echo "ERROR: ingress-nginx LoadBalancer external address was not assigned within $(INGRESS_NGINX_LB_WAIT_SECONDS)s."; \
			echo "INFO: Controller pods:"; \
			kubectl -n $(INGRESS_NGINX_NAMESPACE) get pods -o wide || true; \
			echo "INFO: Controller service:"; \
			kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller -o wide || true; \
			echo "INFO: Describe service for cloud provider events:"; \
			kubectl -n $(INGRESS_NGINX_NAMESPACE) describe svc $(INGRESS_NGINX_RELEASE)-controller || true; \
			exit 1; \
		fi; \
		echo "INFO: Waiting for ingress-nginx external LoadBalancer address..."; \
		sleep 10; \
	done
	@echo "SUCCESS: ingress-nginx ready."

cloud-dev-install-cert-manager:
	@echo "\nINFO: Installing cert-manager..."
	helm repo add jetstack https://charts.jetstack.io || true
	helm repo update
	helm upgrade --install $(CERT_MANAGER_RELEASE) $(CERT_MANAGER_CHART) \
		--namespace $(CERT_MANAGER_NAMESPACE) \
		--create-namespace \
		--set crds.enabled=true \
		$(CERT_MANAGER_EXTRA_SET) \
		--wait \
		--timeout $(CERT_MANAGER_TIMEOUT)
	@echo "SUCCESS: cert-manager ready."
	@echo "INFO: ClusterIssuer placeholders are in platform/bootstrap/cert-manager/ and are not applied automatically."

cloud-dev-install-external-secrets:
	@echo "\nINFO: Installing External Secrets Operator..."
	helm repo add external-secrets https://charts.external-secrets.io || true
	helm repo update
	helm upgrade --install $(EXTERNAL_SECRETS_RELEASE) $(EXTERNAL_SECRETS_CHART) \
		--namespace $(EXTERNAL_SECRETS_NAMESPACE) \
		--create-namespace \
		$(EXTERNAL_SECRETS_EXTRA_SET) \
		--wait \
		--timeout $(EXTERNAL_SECRETS_TIMEOUT)
	@echo "SUCCESS: External Secrets Operator ready."
	@echo "INFO: Placeholder GCP Secret Manager manifests are in platform/bootstrap/external-secrets/ and are not applied automatically."

cloud-dev-buildx-bootstrap:
	@echo "\nINFO: Ensuring Docker Buildx builder $(BUILDX_BUILDER) exists..."
	@docker buildx inspect $(BUILDX_BUILDER) >/dev/null 2>&1 || docker buildx create --name $(BUILDX_BUILDER) --use
	@docker buildx use $(BUILDX_BUILDER)
	@docker buildx inspect --bootstrap
	@echo "SUCCESS: Buildx builder $(BUILDX_BUILDER) ready."

cloud-dev-build-push: cloud-dev-buildx-bootstrap
	@echo "\nINFO: Building and pushing $(DOCKER_PLATFORM) images to $(REGISTRY)..."
	@gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev --quiet
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/chatbot-service:$(IMAGE_TAG) $(DIR_chatbot-service) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/graph-core:$(IMAGE_TAG) $(DIR_graph-core) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/chatbot-ui:$(IMAGE_TAG) $(DIR_chatbot-ui) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/admin-ui:$(IMAGE_TAG) $(DIR_admin-ui) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/agent-service:$(IMAGE_TAG) $(DIR_agent-service) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/incident-service:$(IMAGE_TAG) $(DIR_incident-service) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/participant-service:$(IMAGE_TAG) $(DIR_participant-service) --push
	docker buildx build --platform $(DOCKER_PLATFORM) -t $(REGISTRY)/admin-service:$(IMAGE_TAG) $(DIR_admin-service) --push
	@echo "SUCCESS: All $(DOCKER_PLATFORM) images pushed."

cloud-dev-verify-images:
	@echo "\n🔎 Listing Artifact Registry images in $(REGISTRY)..."
	gcloud artifacts docker images list $(REGISTRY) --project $(GCP_PROJECT)
	@echo "\n🔎 Inspecting pushed image manifests..."
	@for svc in $(SERVICES); do \
		echo "\n--- $(REGISTRY)/$$svc:$(IMAGE_TAG) ---"; \
		docker buildx imagetools inspect $(REGISTRY)/$$svc:$(IMAGE_TAG); \
	done

cloud-dev-authorize-sql:
	@echo "\nINFO: Authorizing current GKE node NAT IPs for Cloud SQL $(CLOUD_SQL_INSTANCE)..."
	@set -e; \
	NODE_IPS="$$(gcloud compute instances list \
		--project $(GCP_PROJECT) \
		--filter='name~^gke-$(GKE_CLUSTER)- AND status=RUNNING' \
		--format='value(networkInterfaces[0].accessConfigs[0].natIP)' | awk 'NF { print $$1 "/32" }' | paste -sd, -)"; \
	if [ -z "$$NODE_IPS" ]; then \
		echo "ERROR: No external NAT IPs found for running GKE nodes in cluster $(GKE_CLUSTER)."; \
		echo "INFO: Check GKE node instances with:"; \
		echo "      gcloud compute instances list --project $(GCP_PROJECT) --filter='name~^gke-$(GKE_CLUSTER)-'"; \
		exit 1; \
	fi; \
	echo "INFO: Authorizing networks: $$NODE_IPS"; \
	gcloud sql instances patch $(CLOUD_SQL_INSTANCE) \
		--project $(GCP_PROJECT) \
		--authorized-networks="$$NODE_IPS" \
		--quiet; \
	echo "SUCCESS: Cloud SQL authorized for current GKE node NAT IPs."

cloud-dev-create-db-secret:
	@echo "\nINFO: Creating Kubernetes DB secret for cloud-dev..."
	@set -e; \
	DB_URL="$$DATABASE_URL"; \
	if [ -z "$$DB_URL" ]; then \
		echo "INFO: DATABASE_URL is not set; trying Terraform output database_connection_string."; \
		DB_URL="$$(cd $(TF_DEV_DIR) && terraform output -raw database_connection_string 2>/dev/null || true)"; \
	fi; \
	if [ -n "$$DB_URL" ]; then \
		kubectl create namespace $(DEV_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -; \
		kubectl --namespace $(DEV_NAMESPACE) create secret generic survivor-db-url \
			--from-literal=DATABASE_URL="$$DB_URL" \
			--dry-run=client -o yaml | kubectl apply -f -; \
		echo "SUCCESS: Secret survivor-db-url created/updated in namespace $(DEV_NAMESPACE)."; \
	else \
		echo "WARN: DATABASE_URL is not set and Terraform output database_connection_string is unavailable; skipping survivor-db-url secret creation."; \
		echo "INFO: Example: DATABASE_URL='postgresql+psycopg2://survivor:password@ip:5432/survivor' make cloud-dev-create-db-secret"; \
		echo "INFO: Or run after Terraform apply: make cloud-dev-create-db-secret-from-tf"; \
		if [ "$(CLOUD_DEV_STRICT)" = "true" ]; then \
			echo "ERROR: CLOUD_DEV_STRICT=true, failing because no database URL source is available."; \
			exit 1; \
		fi; \
	fi

cloud-dev-create-db-secret-from-tf:
	@echo "\nINFO: Creating Kubernetes DB secret from Terraform output database_connection_string..."
	@set -e; \
	DB_URL="$$(cd $(TF_DEV_DIR) && terraform output -raw database_connection_string)"; \
	if [ -z "$$DB_URL" ]; then \
		echo "ERROR: Terraform output database_connection_string is empty."; \
		exit 1; \
	fi; \
	kubectl create namespace $(DEV_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -; \
	kubectl --namespace $(DEV_NAMESPACE) create secret generic survivor-db-url \
		--from-literal=DATABASE_URL="$$DB_URL" \
		--dry-run=client -o yaml | kubectl apply -f -; \
	echo "SUCCESS: Secret survivor-db-url created/updated from Terraform output in namespace $(DEV_NAMESPACE)."

cloud-dev-create-secrets:
	@echo "\nINFO: Creating Kubernetes DB secret for cloud-dev..."
	@set -e; \
	if [ -n "$$DATABASE_URL" ]; then \
		kubectl create namespace $(DEV_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -; \
		kubectl --namespace $(DEV_NAMESPACE) create secret generic survivor-db-url \
			--from-literal=DATABASE_URL="$$DATABASE_URL" \
			--dry-run=client -o yaml | kubectl apply -f -; \
		echo "SUCCESS: Secret survivor-db-url created/updated in namespace $(DEV_NAMESPACE)."; \
	else \
		echo "Enter Cloud SQL DATABASE_URL (e.g., postgresql+psycopg2://survivor:PASSWORD@IP:5432/survivor):"; \
		read -p "DATABASE_URL: " DB_URL; \
		if [ -z "$$DB_URL" ]; then \
			echo "ERROR: DATABASE_URL cannot be empty for interactive secret creation."; \
			exit 1; \
		fi; \
		kubectl create namespace $(DEV_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -; \
		kubectl --namespace $(DEV_NAMESPACE) create secret generic survivor-db-url \
			--from-literal=DATABASE_URL="$$DB_URL" \
			--dry-run=client -o yaml | kubectl apply -f -; \
		echo "SUCCESS: Secret survivor-db-url created/updated in namespace $(DEV_NAMESPACE)."; \
	fi

cloud-dev-dns-info:
	@echo "\nINFO: Cloud-dev DNS plan for $(CLOUD_DEV_DOMAIN)"
	@echo "INFO: Ingress LoadBalancer service:"
	@kubectl -n $(INGRESS_NGINX_NAMESPACE) get svc $(INGRESS_NGINX_RELEASE)-controller -o wide || true
	@echo "\nINFO: Create A records in rescuenet.co.za DNS pointing to the ingress external IP:"
	@echo "  chat.$(CLOUD_DEV_DOMAIN)         -> chatbot-ui"
	@echo "  api.$(CLOUD_DEV_DOMAIN)          -> chatbot-service"
	@echo "  admin.$(CLOUD_DEV_DOMAIN)        -> admin-ui"
	@echo "  admin-api.$(CLOUD_DEV_DOMAIN)    -> admin-service"
	@echo "  graph.$(CLOUD_DEV_DOMAIN)        -> graph-core"
	@echo "  incidents.$(CLOUD_DEV_DOMAIN)    -> incident-service"
	@echo "  participants.$(CLOUD_DEV_DOMAIN) -> participant-service"
	@echo "\nINFO: Test before DNS propagation with: curl -H 'Host: api.$(CLOUD_DEV_DOMAIN)' http://<INGRESS_IP>/health"

cloud-dev-tls-apply-staging-issuer:
	@echo "\nINFO: Applying Let's Encrypt staging ClusterIssuer..."
	@echo "WARN: Confirm platform/bootstrap/cert-manager/clusterissuer-letsencrypt-staging.yaml has the right monitored email first."
	kubectl apply -f platform/bootstrap/cert-manager/clusterissuer-letsencrypt-staging.yaml
	@echo "SUCCESS: Staging ClusterIssuer applied."

cloud-dev-tls-apply-prod-issuer:
	@echo "\nWARN: Production Let's Encrypt issuer is not applied automatically."
	@if [ "$(CONFIRM_PROD_TLS)" != "true" ]; then \
		echo "ERROR: Set CONFIRM_PROD_TLS=true only after DNS and staging certificates are verified."; \
		exit 1; \
	fi
	kubectl apply -f platform/bootstrap/cert-manager/clusterissuer-letsencrypt-prod.yaml
	@echo "SUCCESS: Production ClusterIssuer applied."

cloud-dev-tls-verify:
	@echo "\nINFO: Inspecting cert-manager TLS state..."
	kubectl get clusterissuer || true
	kubectl describe clusterissuer letsencrypt-staging || true
	kubectl get certificate -A || true
	kubectl describe certificate -A || true
	kubectl describe challenge -A || true

cloud-dev-secret-create-db-url:
	@echo "\nINFO: Ensuring Secret Manager secret $(GCP_SECRET_DB_URL) exists..."
	@set -e; \
	if gcloud secrets describe $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT) >/dev/null 2>&1; then \
		echo "SUCCESS: Secret Manager secret $(GCP_SECRET_DB_URL) already exists."; \
	else \
		gcloud secrets create $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT) --replication-policy=automatic; \
		echo "SUCCESS: Secret Manager secret $(GCP_SECRET_DB_URL) created."; \
	fi

cloud-dev-secret-put-db-url:
	@echo "\nINFO: Adding a new Secret Manager version for $(GCP_SECRET_DB_URL)..."
	@set -e; \
	if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL is required but will not be printed."; \
		echo "INFO: Example: DATABASE_URL='postgresql+psycopg2://...' make cloud-dev-secret-put-db-url"; \
		exit 1; \
	fi; \
	gcloud secrets describe $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT) >/dev/null 2>&1 || \
		gcloud secrets create $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT) --replication-policy=automatic; \
	printf "%s" "$$DATABASE_URL" | gcloud secrets versions add $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT) --data-file=- >/dev/null; \
	echo "SUCCESS: Added new Secret Manager version for $(GCP_SECRET_DB_URL)."

cloud-dev-secret-describe-db-url:
	@echo "\nINFO: Describing Secret Manager secret $(GCP_SECRET_DB_URL) without reading secret data..."
	gcloud secrets describe $(GCP_SECRET_DB_URL) --project $(GCP_PROJECT)

cloud-dev-external-secrets-apply:
	@echo "\nINFO: Applying External Secrets manifests for GCP Secret Manager..."
	@echo "WARN: Workload Identity and roles/secretmanager.secretAccessor must be configured first."
	kubectl apply -f platform/bootstrap/external-secrets/clustersecretstore-gcp-secret-manager.yaml
	kubectl apply -f platform/bootstrap/external-secrets/externalsecret-survivor-db-url.yaml
	@echo "SUCCESS: External Secrets manifests applied."

cloud-dev-external-secrets-verify:
	@echo "\nINFO: Inspecting External Secrets status..."
	kubectl -n $(EXTERNAL_SECRETS_NAMESPACE) get pods || true
	kubectl get clustersecretstore gcp-secret-manager || true
	kubectl -n $(DEV_NAMESPACE) get externalsecret survivor-db-url || true
	kubectl -n $(DEV_NAMESPACE) describe externalsecret survivor-db-url || true
	kubectl -n $(DEV_NAMESPACE) get secret survivor-db-url || true

cloud-dev-sql-info:
	@echo "\nINFO: Cloud SQL dev connectivity state"
	@echo "INFO: Instance: $(CLOUD_SQL_INSTANCE)"
	@echo "INFO: Connection name: $(CLOUD_SQL_CONNECTION_NAME)"
	@echo "INFO: Current working fallback uses public IP plus authorized GKE node networks."
	@echo "INFO: Near-term hardening path is Cloud SQL Auth Proxy sidecars with Workload Identity."
	@echo "INFO: Required IAM for Auth Proxy: roles/cloudsql.client"
	@gcloud sql instances describe $(CLOUD_SQL_INSTANCE) --project $(GCP_PROJECT) --format='table(name,connectionName,ipAddresses.ipAddress,ipAddresses.type)' || true
	@echo "\nINFO: When Auth Proxy is enabled, DATABASE_URL should point at 127.0.0.1:5432 and still come from Kubernetes Secret or External Secret."

helm-template-dev:
	helm template survivor-network $(HELM_CHART) -f $(HELM_CHART)/values-dev.yaml --namespace $(DEV_NAMESPACE)

deploy-dev:
	helm upgrade --install survivor-network \
		$(HELM_CHART) \
		-f $(HELM_CHART)/values-dev.yaml \
		--namespace $(DEV_NAMESPACE) \
		--create-namespace \
		--wait --timeout 5m

smoke-dev-internal:
	@echo "\nINFO: Running cloud dev health checks from inside the cluster..."
	@failed=0; \
	for svc in $(SMOKE_DEV_SERVICES); do \
		url="http://$$svc:8080/health"; \
		pod="curl-test-$$svc"; \
		echo "  Checking $$url..."; \
		kubectl -n $(DEV_NAMESPACE) delete pod $$pod --ignore-not-found --wait=false >/dev/null 2>&1 || true; \
		if kubectl -n $(DEV_NAMESPACE) run $$pod \
			--image=$(SMOKE_CURL_IMAGE) \
			--rm -i \
			--restart=Never \
			--pod-running-timeout=90s \
			--command -- sh -c 'curl -fsS --connect-timeout 5 --max-time 20 "$$1" >/dev/null' -- "$$url"; then \
			echo "SUCCESS: $$svc"; \
		else \
			echo "ERROR: $$svc health check failed."; \
			echo "INFO: URL: $$url"; \
			echo "INFO: Service:"; \
			kubectl -n $(DEV_NAMESPACE) get svc $$svc -o wide || true; \
			echo "INFO: Pods:"; \
			kubectl -n $(DEV_NAMESPACE) get pods -l app=$$svc -o wide || true; \
			failed=1; \
		fi; \
	done; \
	exit $$failed

smoke-dev-internal-verbose:
	@echo "\nINFO: Running verbose cloud dev health checks from inside the cluster..."
	@failed=0; \
	for svc in $(SMOKE_DEV_SERVICES); do \
		url="http://$$svc:8080/health"; \
		pod="curl-test-$$svc-verbose"; \
		echo "\n--- $$svc ---"; \
		echo "URL: $$url"; \
		kubectl -n $(DEV_NAMESPACE) delete pod $$pod --ignore-not-found --wait=false >/dev/null 2>&1 || true; \
		if kubectl -n $(DEV_NAMESPACE) run $$pod \
			--image=$(SMOKE_CURL_IMAGE) \
			--rm -i \
			--restart=Never \
			--pod-running-timeout=90s \
			--command -- sh -c 'status=$$(curl -sS --connect-timeout 5 --max-time 20 -o /tmp/body -w "%{http_code}" "$$1"); cat /tmp/body; echo; echo "HTTP_STATUS=$$status"; [ "$$status" -ge 200 ] && [ "$$status" -lt 400 ]' -- "$$url"; then \
			echo "SUCCESS: $$svc"; \
		else \
			echo "ERROR: $$svc health check failed."; \
			echo "INFO: Service:"; \
			kubectl -n $(DEV_NAMESPACE) get svc $$svc -o wide || true; \
			echo "INFO: Pods:"; \
			kubectl -n $(DEV_NAMESPACE) get pods -l app=$$svc -o wide || true; \
			failed=1; \
		fi; \
	done; \
	exit $$failed

cloud-dev-restart-apps:
	kubectl -n $(DEV_NAMESPACE) rollout restart deploy
	kubectl -n $(DEV_NAMESPACE) get pods -w

cloud-dev-bootstrap-verify:
	@echo "\nINFO: Verifying cloud-dev bootstrap..."
	kubectl get nodes
	kubectl get ns
	kubectl -n ingress-nginx get pods
	kubectl -n ingress-nginx get svc $(INGRESS_NGINX_RELEASE)-controller -o wide
	kubectl -n cert-manager get pods
	kubectl -n external-secrets get pods
	@if kubectl -n $(DEV_NAMESPACE) get secret survivor-db-url >/dev/null 2>&1; then \
		echo "SUCCESS: survivor-db-url secret exists in namespace $(DEV_NAMESPACE)."; \
	else \
		echo "WARN: survivor-db-url secret is missing in namespace $(DEV_NAMESPACE)."; \
		echo "INFO: Set DATABASE_URL and run: make cloud-dev-create-db-secret"; \
		if [ "$(CLOUD_DEV_STRICT)" = "true" ]; then \
			echo "ERROR: CLOUD_DEV_STRICT=true, failing because survivor-db-url is missing."; \
			exit 1; \
		fi; \
	fi
	@echo "SUCCESS: Bootstrap verification complete."

cloud-dev-full-recreate:
	@echo "\nINFO: Full cloud-dev recreate without destroy..."
	$(MAKE) cloud-dev-plan
	$(MAKE) cloud-dev-apply
	$(MAKE) cloud-dev-platform-ready
	$(MAKE) cloud-dev-build-push
	$(MAKE) cloud-dev-verify-images
	$(MAKE) deploy-dev
	$(MAKE) smoke-dev-internal
	@echo "\nSUCCESS: Cloud dev full recreate complete."

cloud-dev-recreate:
	@echo "\nINFO: Legacy cloud-dev recreate without destroy..."
	@echo "  1. Terraform apply..."
	$(MAKE) cloud-dev-plan
	$(MAKE) cloud-dev-apply
	@echo "  2. Platform bootstrap..."
	$(MAKE) cloud-dev-platform-ready
	@echo "  5. Build and push images..."
	$(MAKE) cloud-dev-build-push
	$(MAKE) cloud-dev-verify-images
	@echo "  6. Deploy with Helm..."
	$(MAKE) deploy-dev
	@echo "  7. Smoke test..."
	$(MAKE) smoke-dev-internal
	@echo "\nSUCCESS: Cloud dev environment recreated."

# ============================================================
# Database Init (manual fallback if initContainer didn't run)
# ============================================================

init-chatbot-db:
	@echo "Initializing chatbot-service database tables via psql..."
	$(KUBECTL_CLUSTER) -n data exec survivor-db-postgresql-0 -- env PGPASSWORD=survivor-pw psql -U survivor -d survivor -c "\
		CREATE TABLE IF NOT EXISTS chat_sessions (id UUID PRIMARY KEY, status VARCHAR(50) DEFAULT 'active', stage VARCHAR(100) DEFAULT 'initial', provisional_case_id VARCHAR(100), escalated BOOLEAN DEFAULT FALSE, latest_urgency VARCHAR(50), latest_queue VARCHAR(100), state_json JSONB DEFAULT '{}', submitted_at TIMESTAMPTZ, closed_at TIMESTAMPTZ, last_user_message_at TIMESTAMPTZ, last_assessed_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()); \
		CREATE TABLE IF NOT EXISTS chat_messages (id UUID PRIMARY KEY, session_id UUID REFERENCES chat_sessions(id), role VARCHAR(20), content TEXT, client_message_id VARCHAR(100), extracted_json JSONB DEFAULT '{}', agent_reasoning_json JSONB, safety_flags_json JSONB, created_at TIMESTAMPTZ DEFAULT NOW()); \
		CREATE TABLE IF NOT EXISTS chat_attachments (id UUID PRIMARY KEY, session_id UUID REFERENCES chat_sessions(id), attachment_type VARCHAR(50), storage_path TEXT, original_filename VARCHAR(255), metadata_json JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW()); \
		CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages(session_id); \
		CREATE INDEX IF NOT EXISTS ix_chat_messages_client_message_id ON chat_messages(client_message_id); \
		CREATE INDEX IF NOT EXISTS ix_chat_attachments_session_id ON chat_attachments(session_id); \
		ALTER TABLE cases ADD COLUMN IF NOT EXISTS source_session_id VARCHAR(100); \
		CREATE UNIQUE INDEX IF NOT EXISTS ix_cases_source_session_id ON cases(source_session_id) WHERE source_session_id IS NOT NULL;"
	@echo "Done."

clean-start-local: local-build local-load-kind deploy-local-helm
	@echo "\nInitializing database..."
	@$(MAKE) init-chatbot-db
	@echo "Restarting chatbot-service..."
	@$(MAKE) restart-service SVC=chatbot-service
	@echo "Running smoke tests..."
	@$(MAKE) smoke-local
	@echo "Running E2E verification..."
	@$(MAKE) e2e-local
	@echo "\n✅ Clean start complete."

# ============================================================
# Admin Workflow E2E
# ============================================================

e2e-admin:
	@echo "\n🔬 Running admin workflow E2E..."
	@echo "  1. Creating test case via incident-service..."
	@CASE_ID=$$(curl -sf -X POST http://incident-service.127.0.0.1.nip.io/cases/from-intake \
		-H 'Content-Type: application/json' \
		-d '{"session_id":"admin-e2e-test-'$$RANDOM'","message":"I was mugged in Randburg and need transport home","location_text":"Randburg","urgency":"medium","safety_risk":"medium"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") && \
	echo "  Case created: $$CASE_ID" && \
	echo "  2. Listing cases via admin-service..." && \
	curl -sf "http://admin-service.127.0.0.1.nip.io/admin/cases?limit=5" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['total']>0; print(f'  Cases listed: {d[\"total\"]} total')" && \
	echo "  3. Fetching case detail via admin-service..." && \
	curl -sf "http://admin-service.127.0.0.1.nip.io/admin/cases/$$CASE_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['case'] is not None; print(f'  Case detail: urgency={d[\"case\"][\"urgency\"]}, status={d[\"case\"][\"status\"]}')" && \
	echo "  4. Updating case status via admin-service..." && \
	curl -sf -X PATCH "http://admin-service.127.0.0.1.nip.io/admin/cases/$$CASE_ID/status" \
		-H 'Content-Type: application/json' \
		-d '{"status":"in_progress","note":"Admin reviewing case"}' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['new_status']=='in_progress'; print('  Status updated to in_progress')" && \
	echo "  5. Creating participant for assignment..." && \
	PART_ID=$$(curl -sf -X POST http://participant-service.127.0.0.1.nip.io/participants \
		-H 'Content-Type: application/json' \
		-d '{"display_name":"E2E Helper","roles":["volunteer"],"availability_status":"available","verification_status":"admin_verified","trust_level":"high","can_transport_people":true}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") && \
	echo "  Participant created: $$PART_ID" && \
	echo "  6. Assigning participant via admin-service..." && \
	curl -sf -X POST "http://admin-service.127.0.0.1.nip.io/admin/cases/$$CASE_ID/assign" \
		-H 'Content-Type: application/json' \
		-d "{\"participant_id\":\"$$PART_ID\",\"assignment_type\":\"driver\",\"notify_participant\":false}" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['assigned']==True; print(f'  Assigned: {d[\"participant_id\"]}')" && \
	echo "  7. Reading case timeline..." && \
	curl -sf "http://admin-service.127.0.0.1.nip.io/admin/cases/$$CASE_ID/timeline" | python3 -c "\
	import sys,json; d=json.load(sys.stdin); \
	tl=d.get('timeline',[]); \
	assert len(tl)>0, 'Timeline is empty'; \
	events=[e['event_type'] for e in tl]; \
	assert any(e in ('status_change','assignment','created') for e in events), f'No expected events in {events}'; \
	print(f'  Timeline: {len(tl)} entries, events={events}')" && \
	echo "  8. Checking dashboard summary..." && \
	curl -sf "http://admin-service.127.0.0.1.nip.io/dashboard/summary" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Dashboard: {d[\"active_cases\"]} active, {d[\"available_participants\"]} available helpers')" && \
	echo "  ✅ Admin workflow E2E passed"

e2e-admin-local: e2e-admin

# ============================================================
# Terraform Remote State
# ============================================================

terraform-state-bucket-create:
	@echo "Creating GCS bucket for Terraform state..."
	gsutil mb -p $(GCP_PROJECT) -l $(GCP_REGION) gs://survivor-terraform-state-dev
	@echo "✅ Bucket created: gs://survivor-terraform-state-dev"

terraform-state-enable-versioning:
	@echo "Enabling versioning on state bucket..."
	gsutil versioning set on gs://survivor-terraform-state-dev
	@echo "✅ Versioning enabled."

terraform-state-migrate:
	@echo "Migrating Terraform state to GCS backend..."
	cd infra/cloud/dev && terraform init -migrate-state
	@echo "✅ State migration complete. Verify with: terraform state list"
