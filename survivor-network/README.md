# Survivor Network

Survivor Network is a local-first, Kubernetes-deployed emergency and community safety platform. It supports survivor chatbot intake, graph-based triage and context, incident case management, admin workflows, participant/helper services, and future mobile/cloud deployment.

The platform is designed for South African communities and supports crime reporting, urgent help requests, community safety reports, evidence uploads, participant/helper matching, and admin mission control.

## Service Ownership

| Service | Owns |
|---|---|
| `chatbot-service` | Survivor conversation, session state, deterministic safety checks, orchestration |
| `incident-service` | Operational cases, timelines, status, assignments, idempotent case creation, safety normalization |
| `graph-core` | Graph context, triage/resource intelligence, semantic search, relationship/resource matching |
| `agent-service` | AI reasoning support, intake/triage agents, fallback decision support |
| `admin-service` | Admin backend-for-frontend, workflow orchestration, safety-checked assignments |
| `participant-service` | Helper/participant profiles, skills, availability, verification, trust levels |
| `chatbot-ui` | Survivor-facing web UI (React) |
| `admin-ui` | Admin/operator dashboard UI (React + Leaflet maps) |
| `attachment-service` | Planned — media/evidence uploads via MinIO |
| `notification-service` | Planned — SMS, WhatsApp, email, push notifications |

## Local Development

### Prerequisites

- Docker Desktop or OrbStack
- Kind
- kubectl
- Helm 3
- Terraform >= 1.5
- Python 3.11+
- Node.js 20+
- jq (optional, for JSON formatting)

### Start the local cluster

```bash
make local-up
```

This runs Terraform to create a 4-node Kind cluster with PostgreSQL, MinIO, NGINX Ingress, and the observability stack (Prometheus, Grafana, Loki, Tempo).

### Build and deploy all services

```bash
make local-build
make local-load-kind
make deploy-local-helm
```

Or use the legacy per-service targets:

```bash
make chatbot        # chatbot-service only
make graph          # graph-core only
make incident       # incident-service only
make participant    # participant-service only
make admin-svc      # admin-service only
make agent          # agent-service only
make admin-ui       # admin UI only
make chatbot-ui     # chatbot UI only
```

### Verify deployment

```bash
make status
make smoke-local
```

### Helm validation

```bash
make helm-lint-local
make helm-template-local
```

## Runtime Quality Checks

### Reset test data

```bash
make local-reset
make clear-local-cases   # alias
```

Requires `ENVIRONMENT=local` (set in Helm values). Will not run in production.

### End-to-end verification

```bash
make e2e-local
```

Tests:
- Sexual assault case → urgency=urgent, safety_risk=high, incident_type=Sexual Assault
- Stabbing case → urgency=critical, safety_risk=immediate, needs includes Emergency Medical
- Idempotency → duplicate session returns existing case
- Aggregate simulation → cases have incident_type and needs populated

### Load simulations

```bash
make local-sim          # 10 users
make local-sim-full     # 20 incidents + 10 helpers + assignments
make local-sim-100      # 100 concurrent users
```

## Logs and Restarts

```bash
make logs SVC=chatbot-service
make logs SVC=incident-service
make restart                          # restart all
make restart-service SVC=incident-service  # restart one
```

## Local URLs

| Service | URL |
|---|---|
| Chatbot UI | http://chatbot-ui.127.0.0.1.nip.io |
| Admin UI | http://admin-ui.127.0.0.1.nip.io |
| Chatbot API | http://chatbot-service.127.0.0.1.nip.io |
| Graph Core | http://graph-core.127.0.0.1.nip.io |
| Incident Service | http://incident-service.127.0.0.1.nip.io |
| Participant Service | http://participant-service.127.0.0.1.nip.io |
| Admin Service | http://admin-service.127.0.0.1.nip.io |
| Grafana | http://grafana.127.0.0.1.nip.io |
| MinIO Console | http://minio.127.0.0.1.nip.io |

## Deterministic Safety Rules

Safety normalization runs **even when `LLM_ENABLED=false`**. This ensures cases are never under-classified regardless of LLM availability.

Rules are defined in `incident-service/app/safety_rules.py` and enforce:

- Active domestic violence → `urgency=critical`, `safety_risk=immediate`, `incident_type=Domestic Violence`
- Stabbing/bleeding → `urgency=critical`, `safety_risk=immediate`, needs includes `Emergency Medical`
- Overdose/self-harm → `urgency=critical`, `safety_risk=immediate`, `incident_type=Mental Health Crisis`
- Sexual assault → `urgency=urgent`, `safety_risk=high`, `incident_type=Sexual Assault`
- Building collapse → `urgency=critical`, `safety_risk=immediate`, `incident_type=Disaster / Emergency`
- HIV/ARV medication → `urgency=urgent`, `safety_risk=medium`, `incident_type=Medication Access`
- Vague messages → not over-escalated (stays at `medium`/`low`)

The `immediate_danger` flag from chatbot-service always forces `urgency=critical` and `safety_risk=immediate`.

## Known Caveats

- Database URLs are passed via ConfigMaps (not Secrets) in local dev
- Startup migration for `source_session_id` is temporary until Alembic is configured
- Reset endpoint (`DELETE /dev/reset-cases`) requires `ENVIRONMENT=local/dev/test`
- Cloud deployment (GCP/GKE) is a skeleton — not yet functional
- `admin-ui` currently talks to `graph-core` directly for case display; migration to `admin-service` is in progress
- `attachment-service` and `notification-service` are not yet deployed

## Roadmap

- [ ] Wire `admin-ui` to use `admin-service` instead of `graph-core` directly
- [ ] Implement `attachment-service` (MinIO integration)
- [ ] Implement `notification-service` (SMS/WhatsApp/email)
- [ ] Add Alembic migrations for all services
- [ ] Enable LLM with `gpt-4o-mini` for production-quality triage
- [ ] Deploy to GCP/GKE using Terraform + Helm
- [ ] Add GitHub Actions CI/CD pipeline
- [ ] Implement proper auth (JWT/OAuth) for admin-service
- [ ] Add MCP tool servers for resource directory and case management
- [ ] Mobile app integration
