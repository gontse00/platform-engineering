# Cloud Dev DNS, TLS, Secrets, and SQL Hardening

This document prepares the `cloud/gcp-dev` platform for the real RescueNet domain while preserving the current working dev path.

Current state:

- GKE, ingress-nginx, Helm deploys, internal smoke tests, and Cloud SQL public-IP access are working.
- App database configuration still supports `DATABASE_URL` to Kubernetes Secret `survivor-db-url`.
- External Secrets Operator and cert-manager are installed during bootstrap, but production use is staged.
- TLS and Cloud SQL Auth Proxy are disabled by default until DNS, IAM, and certificates are verified.

## DNS Setup

Cloud-dev uses:

```text
dev.rescuenet.co.za
```

The Helm dev values generate these hosts:

```text
chat.dev.rescuenet.co.za          -> chatbot-ui
api.dev.rescuenet.co.za           -> chatbot-service
admin.dev.rescuenet.co.za         -> admin-ui
admin-api.dev.rescuenet.co.za     -> admin-service
graph.dev.rescuenet.co.za         -> graph-core
incidents.dev.rescuenet.co.za     -> incident-service
participants.dev.rescuenet.co.za  -> participant-service
```

Get the ingress-nginx external IP:

```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
make cloud-dev-dns-info
```

Create DNS A records in the `rescuenet.co.za` zone pointing each hostname above to the ingress-nginx LoadBalancer external IP. A wildcard record for `*.dev.rescuenet.co.za` can work for dev if your DNS policy allows it, but explicit A records are easier to audit.

Before DNS propagates, test ingress routing with a Host header:

```bash
curl -H 'Host: api.dev.rescuenet.co.za' http://<INGRESS_IP>/health
curl -H 'Host: chat.dev.rescuenet.co.za' http://<INGRESS_IP>/
```

ExternalDNS is a future option. The Makefile intentionally does not mutate DNS records.

## TLS With Cert-Manager

TLS is exposed through Helm values but remains disabled by default:

```yaml
global:
  ingress:
    tls:
      enabled: false
      clusterIssuer: letsencrypt-staging
      secretNameSuffix: tls
```

Safe rollout sequence:

1. Configure DNS A records for `*.dev.rescuenet.co.za` or each required hostname.
2. Verify HTTP works first through ingress-nginx.
3. Confirm the ClusterIssuer email in `platform/bootstrap/cert-manager/clusterissuer-letsencrypt-staging.yaml`.
4. Apply the staging issuer:

```bash
make cloud-dev-tls-apply-staging-issuer
```

5. Enable TLS with `letsencrypt-staging` in Helm values or with `--set`.
6. Deploy and verify certificates:

```bash
kubectl get clusterissuer
kubectl describe clusterissuer letsencrypt-staging
kubectl get certificate -A
kubectl describe certificate -A
kubectl describe challenge -A
make cloud-dev-tls-verify
```

7. Switch to `letsencrypt-prod` only after staging certificates succeed. Production issuer application is guarded:

```bash
CONFIRM_PROD_TLS=true make cloud-dev-tls-apply-prod-issuer
```

Common HTTP-01 failure causes:

- DNS does not point at the ingress-nginx LoadBalancer IP.
- The ingress class is wrong or ingress-nginx is not ready.
- The LoadBalancer or firewall path is not ready.
- The requested hostnames do not match Helm ingress hosts.
- Let’s Encrypt production rate limits were hit.

## Secret Manager And External Secrets

The current manual fallback remains supported:

```bash
DATABASE_URL='postgresql+psycopg2://...' make cloud-dev-create-db-secret
```

After Terraform apply, the Kubernetes fallback can also be created from Terraform's sensitive `database_connection_string` output without manually assembling the URL:

```bash
make cloud-dev-create-db-secret-from-tf
```

The staged production-oriented path is:

```text
GCP Secret Manager -> External Secrets Operator -> Kubernetes Secret survivor-db-url -> Pods consume DATABASE_URL
```

Create or inspect the Secret Manager secret without storing plaintext in Terraform state:

```bash
make cloud-dev-secret-create-db-url
make cloud-dev-secret-describe-db-url
```

Add or rotate the secret value without printing it:

```bash
DATABASE_URL='postgresql+psycopg2://survivor:<password>@<host>:5432/survivor' make cloud-dev-secret-put-db-url
```

External Secrets manifests live in:

```text
platform/bootstrap/external-secrets/
```

They create Kubernetes Secret `survivor-db-url` in namespace `survivor-apps` with key `DATABASE_URL`.

Before applying them, configure Workload Identity:

- Create or choose a Google service account for External Secrets.
- Grant it `roles/secretmanager.secretAccessor` on the project or secret.
- Bind Kubernetes service account `external-secrets/external-secrets` to that Google service account.
- Confirm the `ClusterSecretStore` project, cluster, and service account values.

Apply and verify:

```bash
make cloud-dev-external-secrets-apply
make cloud-dev-external-secrets-verify
```

Do not remove the manual Kubernetes Secret fallback until External Secrets is proven in cloud-dev.

## Cloud SQL Access

Current dev connectivity uses Cloud SQL public IP plus authorized GKE node NAT IPs:

```bash
make cloud-dev-authorize-sql
```

This is acceptable for cloud-dev but not the long-term production target because node NAT IPs can change and database access depends on public networking.

Two safer options:

- Cloud SQL Auth Proxy: least disruptive near-term hardening. It uses Workload Identity and `roles/cloudsql.client`, keeps the database private from app code, and lets apps connect to `127.0.0.1:5432`.
- Private IP: preferred production networking model, but it can require VPC/private service access changes and may be disruptive depending on existing Cloud SQL configuration.

The Helm chart includes optional Auth Proxy sidecar support for DB-using services, disabled by default:

```yaml
global:
  cloudSql:
    authProxy:
      enabled: false
      instanceConnectionName: survivor-rescue-net-dev:europe-west2:survivor-network-dev-db
```

When enabling Auth Proxy, keep the database password or full URL in Kubernetes Secret or External Secret. Point `DATABASE_URL` at localhost:

```text
postgresql+psycopg2://survivor:<password>@127.0.0.1:5432/survivor
```

Required IAM:

- Google service account used by app pods
- `roles/cloudsql.client`
- Workload Identity binding from Kubernetes service account `survivor-apps/survivor-network`

Inspect the current Cloud SQL state:

```bash
make cloud-dev-sql-info
```

## Recommended Staged Rollout

1. Keep current public-IP DB and manual `survivor-db-url` secret working.
2. Add DNS A records for `dev.rescuenet.co.za` hosts.
3. Verify HTTP ingress with real hostnames.
4. Apply and validate the staging ClusterIssuer.
5. Enable TLS with staging, then switch to production only after success.
6. Create the Secret Manager `survivor-db-url` secret and configure Workload Identity for External Secrets.
7. Apply External Secrets and verify it creates the same Kubernetes Secret shape.
8. Configure Workload Identity for app pods and test Cloud SQL Auth Proxy with one DB-using service.
9. Roll Auth Proxy to the remaining DB-using services.
10. Plan private-IP Cloud SQL as a later networking change.

## Rollback

- DNS: point A records back to the previous ingress IP or remove dev records.
- TLS: set `global.ingress.tls.enabled=false` and redeploy; HTTP ingress remains available.
- External Secrets: keep or recreate the manual Kubernetes Secret with `make cloud-dev-create-db-secret`.
- Auth Proxy: set `global.cloudSql.authProxy.enabled=false`, restore the public-IP `DATABASE_URL`, and rerun `make cloud-dev-authorize-sql`.

## Troubleshooting

For ingress:

```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
kubectl -n survivor-apps get ingress
kubectl -n ingress-nginx get pods
```

For TLS:

```bash
make cloud-dev-tls-verify
kubectl describe challenge -A
```

For External Secrets:

```bash
make cloud-dev-external-secrets-verify
kubectl -n survivor-apps get secret survivor-db-url
```

For Cloud SQL:

```bash
make cloud-dev-sql-info
make cloud-dev-authorize-sql
```
