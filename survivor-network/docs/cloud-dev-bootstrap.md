# Cloud Dev Bootstrap

This document describes the hardened GKE bootstrap and deployment flow for the Survivor Network `cloud/gcp-dev` environment.

The current cloud-dev architecture is intentionally preserved: Terraform creates GCP infrastructure, Makefile bootstrap prepares the Kubernetes platform, Docker Buildx publishes images, Helm deploys the app chart, and in-cluster smoke tests verify service health.

## Recommended Flow

Use the saved Terraform plan workflow, then run the canonical platform bootstrap target:

```bash
make cloud-dev-plan
make cloud-dev-apply
make cloud-dev-platform-ready
make cloud-dev-build-push
make cloud-dev-verify-images
make deploy-dev
make smoke-dev-internal
```

For a repeatable reconcile without destroying infrastructure:

```bash
make cloud-dev-full-recreate
```

`cloud-dev-full-recreate` runs:

```text
cloud-dev-plan
cloud-dev-apply
cloud-dev-platform-ready
cloud-dev-build-push
cloud-dev-verify-images
deploy-dev
smoke-dev-internal
```

It does not run destroy.

## Platform Ready

`cloud-dev-platform-ready` is the canonical post-Terraform bootstrap target. It runs:

```text
cloud-dev-kubeconfig
cloud-dev-create-namespaces
cloud-dev-install-ingress
cloud-dev-install-cert-manager
cloud-dev-install-external-secrets
cloud-dev-authorize-sql
cloud-dev-create-db-secret
cloud-dev-bootstrap-verify
```

The first step always refreshes kubeconfig. This matters after GKE destroy/recreate because the old cluster endpoint certificate becomes stale and `kubectl` can fail with TLS errors until credentials are refreshed.

## Image Architecture

GKE dev nodes run Linux AMD64. Apple Silicon Macs build ARM64 images by default with plain `docker build`, which caused pods to fail with:

```text
no match for platform in manifest: not found
```

Cloud-dev builds now use Docker Buildx and default to:

```make
DOCKER_PLATFORM ?= linux/amd64
BUILDX_BUILDER ?= survivor-builder
```

Initialize or reuse the builder:

```bash
make cloud-dev-buildx-bootstrap
```

Build and push all images:

```bash
make cloud-dev-build-push
```

Verify Artifact Registry images and manifests:

```bash
make cloud-dev-verify-images
```

`cloud-dev-build-push` uses `docker buildx build --platform linux/amd64 --push` for each service and preserves the existing image names and `dev` tag.

## Cloud SQL Connectivity

The current dev path uses Cloud SQL public IP plus authorized networks. After a cluster recreate, GKE node external/NAT IPs can change. If they are not authorized, DB-backed services can time out on startup:

```text
psycopg2.OperationalError: connection to server ... port 5432 failed: Connection timed out
```

`cloud-dev-authorize-sql` detects the current running GKE node NAT IPs and patches the Cloud SQL authorized networks for the dev instance. It is part of `cloud-dev-platform-ready`, so it runs before app deployment.

This keeps the current public-IP dev workflow intact. A future production hardening step should move to Cloud SQL Auth Proxy or private IP.

## DB Secret

The Helm cloud values expect a Kubernetes Secret named `survivor-db-url` in namespace `survivor-apps`.

Create or update it with:

```bash
DATABASE_URL='postgresql+psycopg2://survivor:password@ip:5432/survivor' make cloud-dev-create-db-secret
```

The target uses strict shell behavior so Kubernetes failures stop the recipe and success is printed only after `kubectl apply` succeeds. If `DATABASE_URL` is missing, bootstrap warns and continues by default. To make that fatal:

```bash
CLOUD_DEV_STRICT=true make cloud-dev-platform-ready
```

Do not commit real database passwords or generated Secret manifests.

## Ingress

`cloud-dev-install-ingress` installs `ingress-nginx` with Helm and verifies:

- namespace exists through bootstrap namespace creation
- controller deployment rolls out
- controller pod becomes Ready
- controller service exists
- controller service is type `LoadBalancer`
- an external LoadBalancer address is assigned

If the external address is not assigned within the configured wait window, the target prints controller pods, service state, and service events to make the failure actionable.

Useful inspection commands:

```bash
kubectl -n ingress-nginx get pods -o wide
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
kubectl -n ingress-nginx describe svc ingress-nginx-controller
```

## Smoke Tests

Cloud smoke tests do not exec into app containers. Minimal app images may not include `wget` or `curl`, so that approach can report false failures.

`smoke-dev-internal` starts temporary `curlimages/curl` pods inside `survivor-apps` and checks Kubernetes service DNS:

```text
http://chatbot-service:8080/health
http://graph-core:8080/health
http://incident-service:8080/health
http://participant-service:8080/health
http://admin-service:8080/health
http://agent-service:8080/health
```

The target exits non-zero if any service fails and prints the failing service, URL, Service object, and matching pods.

For response bodies and HTTP status codes:

```bash
make smoke-dev-internal-verbose
```

## External Secrets Future Path

External Secrets Operator is installed during platform bootstrap, but the GCP Secret Manager integration is not applied automatically.

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

Replace `change-me@example.com` with a monitored team email before applying either issuer. Use staging before production:

```bash
kubectl apply -f platform/bootstrap/cert-manager/clusterissuer-letsencrypt-staging.yaml
```

Do not apply the production issuer until DNS points to the ingress LoadBalancer and HTTP-01 validation works with staging.

## Safe Destroy Workflow

Terraform destroy can hang or fail when application pods still hold active Cloud SQL connections or when Kubernetes resources are still reconciling. Before destroying GKE and Cloud SQL, gracefully stop the app layer and verify that DB-using pods are gone.

Recommended explicit sequence:

```bash
make cloud-dev-pre-destroy
make cloud-dev-plan-destroy
make cloud-dev-destroy
```

Single-command safe flow:

```bash
make cloud-dev-destroy-safe
```

`cloud-dev-pre-destroy` runs:

```text
cloud-dev-kubeconfig
cloud-dev-shutdown-apps
cloud-dev-drain-db
cloud-dev-uninstall-apps
```

`cloud-dev-shutdown-apps` scales all deployments in `survivor-apps` to zero and waits for pods to terminate. Scaling to zero lets app processes exit and release PostgreSQL connections before Cloud SQL destruction.

`cloud-dev-drain-db` is Kubernetes-focused for now. It verifies that no application pods remain and prints current services/endpoints for diagnostics. It does not run SQL queries.

`cloud-dev-uninstall-apps` removes the Helm release if it exists and verifies application deployments, services, and ingresses are gone. It tolerates repeated runs when the release is already absent.

The Helm chart also sets a default `terminationGracePeriodSeconds` so pods have time to shut down after SIGTERM. Future app hardening should add explicit FastAPI SIGTERM handling to close in-flight requests and DB sessions cleanly.

## Recovery

ImagePullBackOff with `no match for platform in manifest`:

```bash
make cloud-dev-build-push
make cloud-dev-verify-images
make cloud-dev-restart-apps
```

Stale kubeconfig or TLS certificate errors after recreate:

```bash
make cloud-dev-kubeconfig
kubectl get nodes
```

Cloud SQL timeout from pods:

```bash
make cloud-dev-authorize-sql
kubectl -n survivor-apps rollout restart deploy/incident-service deploy/participant-service
```

Missing ingress controller after cluster recreate:

```bash
make cloud-dev-install-ingress
kubectl -n ingress-nginx get pods
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
```

Smoke test failures:

```bash
make smoke-dev-internal-verbose
kubectl -n survivor-apps get svc
kubectl -n survivor-apps get pods -o wide
```

Stuck pre-destroy or destroy:

```bash
make cloud-dev-shutdown-apps
make cloud-dev-drain-db
kubectl -n survivor-apps get pods -o wide
kubectl -n survivor-apps get events --sort-by=.lastTimestamp
```

If pods remain after the shutdown timeout, inspect the remaining pod events and logs before running Terraform destroy. Avoid force-deleting pods unless you have confirmed there are no important in-flight writes.
