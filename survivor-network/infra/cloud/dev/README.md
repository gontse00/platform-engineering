# Cloud Dev Environment — GCP

Terraform configuration for the Survivor Network cloud dev environment.

**Project:** `survivor-rescue-net-dev`
**Region:** `europe-west2` (London)
**Zone:** `europe-west2-a`

## Prerequisites

- GCP project `survivor-rescue-net-dev` with billing enabled
- `gcloud` CLI authenticated: `gcloud auth application-default login`
- Terraform >= 1.5
- Required APIs enabled:
  - container.googleapis.com
  - artifactregistry.googleapis.com
  - sqladmin.googleapis.com
  - compute.googleapis.com
  - iam.googleapis.com
  - storage.googleapis.com
  - cloudresourcemanager.googleapis.com

## Setup

```bash
cd survivor-network/infra/cloud/dev

# Create tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set cloud_sql_password to a secure value

# Initialize, validate, plan, apply
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

## Resources Created

| Resource | Name | Purpose |
|---|---|---|
| GKE cluster | `survivor-network-dev` | Kubernetes for services |
| Node pool | 2x e2-standard-2 | Compute |
| Artifact Registry | `survivor-network` | Container images |
| Cloud SQL | `survivor-network-dev-db` | PostgreSQL 16 |
| Cloud Storage | `survivor-rescue-net-dev-attachments` | Attachments/evidence |

## Connect to cluster

```bash
gcloud container clusters get-credentials survivor-network-dev \
  --zone europe-west2-a \
  --project survivor-rescue-net-dev
kubectl get nodes
```

## Push images

Images must be pushed before `make deploy-dev`.

```bash
# Configure docker for Artifact Registry
gcloud auth configure-docker europe-west2-docker.pkg.dev

# Tag and push each service
docker tag chatbot-service:latest europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-network/chatbot-service:dev
docker push europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-network/chatbot-service:dev

docker tag incident-service:latest europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-network/incident-service:dev
docker push europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-network/incident-service:dev

# Repeat for: admin-service, participant-service, agent-service, graph-core, chatbot-ui, admin-ui
```

## Deploy with Helm

```bash
make kubeconfig-dev
make deploy-dev
```

## Cloud SQL App Connectivity

**Important:** After `terraform apply`, the services will NOT automatically connect to Cloud SQL.

The `DATABASE_URL` values in `values-dev.yaml` are placeholders. You must replace them with the actual Cloud SQL connection details.

Preferred connectivity options:
1. **Cloud SQL Auth Proxy sidecar** (recommended) — add a sidecar container to each pod that needs DB access
2. **Private IP** — configure VPC peering between GKE and Cloud SQL (requires additional Terraform)
3. **Public IP + authorized networks** (dev only) — add GKE node IPs to Cloud SQL authorized networks

Get the Cloud SQL public IP after apply:
```bash
terraform output database_connection_string
```

## Teardown

```bash
terraform destroy
```

## Cost estimate (dev)

- GKE: ~$70/month (2x e2-standard-2)
- Cloud SQL: ~$10/month (db-f1-micro)
- Storage: ~$1/month
- Artifact Registry: ~$1/month
- **Total: ~$82/month**

## Remote state (optional)

```bash
# Create state bucket
gsutil mb -l europe-west2 gs://survivor-rescue-net-dev-tfstate

# Uncomment backend.tf and re-init
terraform init -migrate-state
```
