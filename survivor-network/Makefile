# ============================================================
# Survivor Network — Makefile
# ============================================================
CLUSTER     := survivor-net
NAMESPACE   := survivor-apps
CONTEXT     := kind-$(CLUSTER)
KUBECTL_CLUSTER := kubectl --context $(CONTEXT)
KUBECTL     := $(KUBECTL_CLUSTER) -n $(NAMESPACE)
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
	@echo "  make restart-service SVC=x — restart one service"
	@echo "  make local-reset        — clear test cases"
	@echo "  make clear-local-cases  — alias for local-reset"
	@echo "  make e2e-local          — run E2E quality checks"
	@echo "  make e2e-admin          — run admin workflow E2E"
	@echo "  make e2e-admin-local    — alias for e2e-admin"
	@echo "  make init-chatbot-db    — create chatbot DB tables manually"
	@echo "  make clean-start-local  — full rebuild + init + test"

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
