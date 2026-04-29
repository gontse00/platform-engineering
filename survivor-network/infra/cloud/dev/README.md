# Cloud Dev Environment

Terraform configuration for the Survivor Network cloud dev environment on GCP.

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated
- Terraform >= 1.5

## Setup

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project details
terraform init
terraform plan
terraform apply
```

## Resources Created

- GKE Kubernetes cluster
- Artifact Registry (container images)
- Cloud SQL PostgreSQL instance
- Cloud Storage bucket (attachments/evidence)
