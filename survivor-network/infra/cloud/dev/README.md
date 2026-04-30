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
# Edit terraform.tfvars — set db_password to a secure value

# Initialize and plan
terraform init
terraform plan

# Apply (creates all resources)
terraform apply
```

## Resources Created

| Resource | Type | Purpose |
|---|---|---|
| GKE cluster (`survivor-dev`) | `google_container_cluster` | Kubernetes for services |
| Node pool (2x e2-standard-2) | `google_container_node_pool` | Compute |
| Artifact Registry (`survivor-images`) | `google_artifact_registry_repository` | Container images |
| Cloud SQL (`survivor-db-dev`) | `google_sql_database_instance` | PostgreSQL 16 |
| Cloud Storage | `google_storage_bucket` | Attachments/evidence |

## Connect to cluster

```bash
gcloud container clusters get-credentials survivor-dev --zone europe-west2-a --project survivor-rescue-net-dev
kubectl get nodes
```

## Push images

```bash
# Configure docker for Artifact Registry
gcloud auth configure-docker europe-west2-docker.pkg.dev

# Tag and push
docker tag chatbot-service:latest europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-images/chatbot-service:latest
docker push europe-west2-docker.pkg.dev/survivor-rescue-net-dev/survivor-images/chatbot-service:latest
```

## Deploy with Helm

```bash
helm upgrade --install survivor-network \
  ../../platform/helm/survivor-network \
  -f ../../platform/helm/survivor-network/values-dev.yaml \
  --namespace survivor-apps \
  --create-namespace \
  --wait --timeout 5m
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

To enable team collaboration with remote state:

```bash
# Create state bucket
gsutil mb -l europe-west2 gs://survivor-rescue-net-dev-tfstate

# Uncomment backend.tf and re-init
terraform init -migrate-state
```
