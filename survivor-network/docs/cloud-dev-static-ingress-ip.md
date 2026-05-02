# Cloud Dev Static Ingress IP

This document describes the static external IP workflow for the Survivor Network `cloud/gcp-dev` ingress-nginx LoadBalancer.

## Why This Exists

GKE `LoadBalancer` services receive an external IP from Google Cloud. If that IP is ephemeral, it can change when the service or cluster is recreated. That breaks DNS records for:

```text
*.dev.rescuenet.co.za
```

It also makes production TLS risky because Let’s Encrypt validation depends on DNS pointing to the correct ingress endpoint. Before switching from Let’s Encrypt staging to production, the ingress IP should be stable.

## Target Flow

```text
Terraform reserves regional static IP
-> ingress-nginx LoadBalancer uses that IP
-> DNS A records point to that IP
-> HTTP and staging TLS are retested
-> production TLS can be enabled later
```

## Terraform Resource

Cloud-dev Terraform reserves a regional external IP:

```text
name: rescuenet-dev-ingress-ip
region: europe-west2
project: survivor-rescue-net-dev
```

Terraform output:

```bash
terraform -chdir=infra/cloud/dev output -raw ingress_static_ip
```

## Ingress-NGINX Binding

`make cloud-dev-install-ingress` reads:

```bash
cd infra/cloud/dev && terraform output -raw ingress_static_ip
```

When present, the value is passed into the ingress-nginx Helm chart:

```bash
--set controller.service.loadBalancerIP=<STATIC_IP>
```

If the Terraform output is missing, the target warns and falls back to an ephemeral IP unless `CLOUD_DEV_STRICT=true`.

## Deployment Sequence

Run:

```bash
make cloud-dev-plan
make cloud-dev-apply
make cloud-dev-platform-ready
make cloud-dev-ingress-ip
make cloud-dev-ingress-static-ip-verify
make cloud-dev-dns-info
```

`cloud-dev-platform-ready` now installs ingress-nginx and verifies that the LoadBalancer IP matches Terraform output.

## DNS Records

After the static IP is reserved and ingress-nginx is using it, update DNS A records in the `rescuenet.co.za` zone:

```text
chat.dev          A   <STATIC_IP>
api.dev           A   <STATIC_IP>
admin.dev         A   <STATIC_IP>
admin-api.dev     A   <STATIC_IP>
graph.dev         A   <STATIC_IP>
incidents.dev     A   <STATIC_IP>
participants.dev  A   <STATIC_IP>
```

Use:

```bash
make cloud-dev-dns-info
```

to print the current static IP and record list.

## HTTP Verification

After DNS updates propagate:

```bash
dig chat.dev.rescuenet.co.za
dig api.dev.rescuenet.co.za
curl http://chat.dev.rescuenet.co.za/
curl http://api.dev.rescuenet.co.za/health
```

Before DNS propagation, test with Host headers:

```bash
STATIC_IP="$(terraform -chdir=infra/cloud/dev output -raw ingress_static_ip)"
curl -H 'Host: chat.dev.rescuenet.co.za' "http://${STATIC_IP}/"
curl -H 'Host: api.dev.rescuenet.co.za' "http://${STATIC_IP}/health"
```

## Staging TLS Retest

After DNS points to the static IP:

```bash
make cloud-dev-tls-verify
kubectl get certificate -A
curl -k https://api.dev.rescuenet.co.za/health
curl -k https://chat.dev.rescuenet.co.za/
```

Use `-k` for staging certificates because Let’s Encrypt staging is not browser-trusted.

## Production TLS Readiness

Move to production TLS only when:

- `make cloud-dev-ingress-static-ip-verify` passes.
- DNS records resolve to the Terraform static IP.
- HTTP works through real hostnames.
- Let’s Encrypt staging certificates are Ready.
- `curl -k https://...` succeeds against staging certs.

Do not apply the production issuer automatically in bootstrap.

## Troubleshooting

Check Terraform output:

```bash
terraform -chdir=infra/cloud/dev output -raw ingress_static_ip
```

Check ingress-nginx service:

```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
make cloud-dev-ingress-ip
```

Require a match:

```bash
make cloud-dev-ingress-static-ip-verify
```

If the LoadBalancer keeps using an old ephemeral IP:

```bash
make cloud-dev-install-ingress
kubectl -n ingress-nginx describe svc ingress-nginx-controller
```

If DNS resolves to the wrong IP, update the A records and wait for TTL expiry.

If cert-manager challenges fail after the IP change:

```bash
kubectl get challenge -A
kubectl describe challenge -A
kubectl get order -A
```
