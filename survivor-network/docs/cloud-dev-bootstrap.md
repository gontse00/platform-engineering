# Cloud Dev Bootstrap

This document describes the GKE bootstrap layer for the Survivor Network `cloud/gcp-dev` environment.

Bootstrap runs after Terraform has created cloud infrastructure and before Helm deploys application workloads. It prepares the Kubernetes cluster with shared namespaces, ingress, certificate automation, secret automation scaffolding, and the database secret fallback used by the current Helm values.

## Architecture Flow

```text
Terraform plan/apply
  -> GCP infrastructure
     - GKE cluster
     - Artifact Registry
     - Cloud SQL
     - Cloud Storage
  -> GKE bootstrap
     - kubeconfig
     - namespaces
     - ingress-nginx
     - cert-manager
     - External Secrets Operator
     - survivor-db-url fallback secret
  -> image build/push
  -> Helm deploy
  -> smoke checks
```

The app deployment still uses the existing Helm chart at `platform/helm/survivor-network` and the cloud values file at `platform/helm/survivor-network/values-dev.yaml`.

## Prerequisites

- GCP project: `survivor-rescue-net-dev`
- Region: `europe-west2`
- Zone: `europe-west2-a`
- GKE cluster: `survivor-network-dev`
- Terraform state bucket already configured through `infra/cloud/dev/backend.tf`
- Authenticated `gcloud`
- `kubectl`, `helm`, `docker`, and `terraform` installed
- Required GCP APIs enabled for GKE, Artifact Registry, Cloud SQL, IAM, Compute, Storage, and Secret Manager if using External Secrets

## Normal Flow

Run the saved Terraform plan/apply workflow first:

```bash
make cloud-dev-plan
make cloud-dev-apply
```

Then bootstrap the cluster:

```bash
make cloud-dev-bootstrap
```

Then publish images and deploy:

```bash
make cloud-dev-build-push
make deploy-dev
make smoke-dev-internal
```

## Bootstrap Targets

`cloud-dev-bootstrap` runs these targets in order:

```text
cloud-dev-kubeconfig
cloud-dev-create-namespaces
cloud-dev-install-ingress
cloud-dev-install-cert-manager
cloud-dev-install-external-secrets
cloud-dev-create-db-secret
cloud-dev-bootstrap-verify
```

The target is idempotent. Re-running it should upgrade existing Helm releases and apply existing namespaces/secrets without replacing unrelated resources.

## Full Recreate Flow

Use this when infrastructure already exists or should be reconciled from Terraform, then bootstrapped and redeployed:

```bash
make cloud-dev-full-recreate
```

This runs:

```text
cloud-dev-plan
cloud-dev-apply
cloud-dev-bootstrap
cloud-dev-build-push
deploy-dev
smoke-dev-internal
```

It does not destroy infrastructure.

## DB Secret Fallback

The current `values-dev.yaml` expects a Kubernetes Secret named `survivor-db-url` in namespace `survivor-apps`.

Create or update it manually with:

```bash
DATABASE_URL='postgresql+psycopg2://survivor:password@ip:5432/survivor' make cloud-dev-create-db-secret
```

If `DATABASE_URL` is not set, `cloud-dev-create-db-secret` prints a warning and continues. To make a missing database URL fail bootstrap:

```bash
CLOUD_DEV_STRICT=true make cloud-dev-bootstrap
```

Do not commit real database passwords or generated Secret manifests.

## External Secrets Future Path

External Secrets Operator is installed by bootstrap, but the GCP Secret Manager integration is not applied automatically.

Placeholder manifests live in:

```text
platform/bootstrap/external-secrets/
```

Before using them:

- Create a GCP Secret Manager secret for `survivor-db-url`.
- Create or choose a Google service account with `roles/secretmanager.secretAccessor`.
- Bind Kubernetes service account `external-secrets/external-secrets` to that Google service account with Workload Identity.
- Review and apply `clustersecretstore-gcp-secret-manager.yaml`.
- Review and apply `externalsecret-survivor-db-url.yaml`.

Until that path is complete, keep using the `DATABASE_URL=... make cloud-dev-create-db-secret` fallback.

## cert-manager and TLS

Bootstrap installs cert-manager with CRDs enabled.

Placeholder ClusterIssuer manifests live in:

```text
platform/bootstrap/cert-manager/
```

Use staging first:

```bash
kubectl apply -f platform/bootstrap/cert-manager/clusterissuer-letsencrypt-staging.yaml
```

Before applying either issuer, replace `change-me@example.com` with a monitored team email.

Do not apply the production issuer until:

- DNS points to the ingress load balancer.
- HTTP-01 validation works with the staging issuer.
- Application ingress hosts are final.

Production issuer:

```bash
kubectl apply -f platform/bootstrap/cert-manager/clusterissuer-letsencrypt-prod.yaml
```

## Ingress and Load Balancer Notes

Bootstrap installs `ingress-nginx` as a Helm release in namespace `ingress-nginx`.

The default bootstrap configuration:

- exposes the controller as a GKE `LoadBalancer`
- enables controller metrics
- sets conservative resource requests and limits
- avoids provider-specific experimental settings

You can override resource sizing without editing the Makefile:

```bash
make cloud-dev-install-ingress \
  INGRESS_NGINX_CPU_REQUEST=200m \
  INGRESS_NGINX_MEMORY_REQUEST=256Mi \
  INGRESS_NGINX_CPU_LIMIT=1000m \
  INGRESS_NGINX_MEMORY_LIMIT=1Gi
```

Additional chart settings can be passed through `INGRESS_NGINX_EXTRA_SET`.

## Verification

Run:

```bash
make cloud-dev-bootstrap-verify
```

It checks:

```text
kubectl get nodes
kubectl get ns
kubectl -n ingress-nginx get pods
kubectl -n cert-manager get pods
kubectl -n external-secrets get pods
kubectl -n survivor-apps get secret survivor-db-url
```

The DB secret check warns by default and fails only with `CLOUD_DEV_STRICT=true`.

## Troubleshooting

If Helm cannot install charts, refresh repos manually:

```bash
helm repo update
```

If `kubectl` points at the wrong cluster:

```bash
make cloud-dev-kubeconfig
kubectl config current-context
```

If ingress has no external IP yet:

```bash
kubectl -n ingress-nginx get svc
```

GKE load balancer provisioning can take several minutes.

If cert-manager certificates do not become ready:

```bash
kubectl -n cert-manager get pods
kubectl describe certificate -A
kubectl describe challenge -A
```

If External Secrets cannot read from GCP Secret Manager, check Workload Identity bindings and Secret Manager IAM before changing app manifests.
