# RescueNet Landing Page

This is a minimal static landing page for:

```text
rescuenet.co.za
www.rescuenet.co.za
```

It has no backend, no build step, no secrets, and can be deployed to Cloudflare Pages, Vercel, Netlify, or GitHub Pages.

## File Tree

```text
landing/
├── index.html
├── styles.css
└── README.md
```

## Run Locally

From the repository root:

```bash
cd landing
python3 -m http.server 8080
```

Open:

```text
http://localhost:8080
```

## Option 1: Deploy With Cloudflare Pages

Best fit if you want Cloudflare to manage DNS, HTTPS, Pages hosting, and future Cloudflare Tunnel records in one place.

1. Commit and push this repository to GitHub.
2. In Cloudflare, add `rescuenet.co.za` as a site/zone.
3. At your domain registrar, change the domain nameservers to the two Cloudflare nameservers shown in the Cloudflare dashboard.
4. In Cloudflare, go to `Workers & Pages`.
5. Select `Create application`.
6. Select `Pages`.
7. Connect the GitHub repository.
8. Configure the Pages project:

```text
Framework preset: None
Build command: exit 0
Build output directory: landing
Root directory: /
```

9. Deploy.
10. Add custom domains in the Pages project:

```text
rescuenet.co.za
www.rescuenet.co.za
```

Cloudflare Pages will guide the needed DNS records. If Cloudflare manages your nameservers, it can create the records for you.

## Option 2: Deploy With Vercel

1. Import the GitHub repository into Vercel.
2. Configure the project:

```text
Framework preset: Other
Root directory: landing
Build command: none
Output directory: .
```

3. Add domains in Vercel:

```text
rescuenet.co.za
www.rescuenet.co.za
```

4. Vercel will show the required DNS records. Common records are:

```text
rescuenet.co.za      A      76.76.21.21
www.rescuenet.co.za  CNAME  cname.vercel-dns.com
```

Use the exact records Vercel shows in your project dashboard.

## Option 3: Deploy With Netlify

1. Import the GitHub repository into Netlify.
2. Configure the site:

```text
Base directory: landing
Build command: leave empty
Publish directory: landing
```

If Netlify asks for a publish directory relative to the base directory, use:

```text
.
```

3. Add custom domains:

```text
rescuenet.co.za
www.rescuenet.co.za
```

4. Netlify will show the required DNS records. Usually `www` can be a CNAME to your Netlify site. For the apex/root domain, use Netlify DNS or the A/ALIAS/ANAME records Netlify gives you.

## DNS Setup

DNS depends on the hosting provider you choose.

### If Using Cloudflare Pages

Recommended approach:

1. Move nameservers for `rescuenet.co.za` to Cloudflare.
2. Add both custom domains in Cloudflare Pages.
3. Let Cloudflare create or validate the DNS records.

Typical records:

| Host | Type | Target | Notes |
|---|---|---|---|
| `rescuenet.co.za` | CNAME flattening / provider-managed | Cloudflare Pages target | Cloudflare handles apex flattening |
| `www.rescuenet.co.za` | CNAME | Cloudflare Pages target | Use the target shown by Pages |

### If Using Vercel

Use the exact records Vercel shows. Common pattern:

| Host | Type | Target |
|---|---|---|
| `rescuenet.co.za` | A | `76.76.21.21` |
| `www.rescuenet.co.za` | CNAME | `cname.vercel-dns.com` |

### If Using Netlify

Use the exact records Netlify shows. Common pattern:

| Host | Type | Target |
|---|---|---|
| `rescuenet.co.za` | A / ALIAS / ANAME | Netlify-provided apex target |
| `www.rescuenet.co.za` | CNAME | Your Netlify site domain |

## Future Production DNS Plan

Use the root domain for the public marketing site. Use subdomains for applications and APIs.

| Host | Purpose | Future target |
|---|---|---|
| `rescuenet.co.za` | Public landing/marketing site | Static host |
| `www.rescuenet.co.za` | Public landing/marketing site alias | Static host |
| `app.rescuenet.co.za` | User-facing RescueNet app | Kubernetes ingress |
| `api.rescuenet.co.za` | Backend API gateway or chatbot API | Kubernetes ingress |
| `admin.rescuenet.co.za` | Admin/operator portal | Kubernetes ingress |
| `graph.rescuenet.co.za` | Graph-core API | Kubernetes ingress or private API |
| `dev-app.rescuenet.co.za` | Local/dev chatbot UI demo | Cloudflare Tunnel |
| `dev-api.rescuenet.co.za` | Local/dev chatbot API demo | Cloudflare Tunnel |
| `dev-admin.rescuenet.co.za` | Local/dev admin UI demo | Cloudflare Tunnel |
| `dev-graph.rescuenet.co.za` | Local/dev graph-core demo | Cloudflare Tunnel |

Production recommendation:

- Keep `rescuenet.co.za` and `www.rescuenet.co.za` on static hosting.
- Put production Kubernetes apps behind HTTPS ingress on `app`, `api`, `admin`, and `graph`.
- Use `dev-*` only for demos and local development tunnels.
- Do not expose local Kind directly to the internet without a tunnel, authentication, and careful routing.

## Optional Cloudflare Tunnel For Local Kind Demos

This is for dev/demo only, not production.

Example target mapping:

| Public hostname | Local service |
|---|---|
| `dev-app.rescuenet.co.za` | `chatbot-ui` |
| `dev-api.rescuenet.co.za` | `chatbot-service` |
| `dev-admin.rescuenet.co.za` | `admin-ui` |
| `dev-graph.rescuenet.co.za` | `graph-core` |

One simple approach is to port-forward local Kind services and point Cloudflare Tunnel at localhost ports.

Example terminal 1:

```bash
kubectl -n survivor-apps port-forward svc/chatbot-ui 18080:8080
```

Example terminal 2:

```bash
kubectl -n survivor-apps port-forward svc/chatbot-service 18081:8080
```

Example terminal 3:

```bash
kubectl -n survivor-apps port-forward svc/admin-ui 18082:8080
```

Example terminal 4:

```bash
kubectl -n survivor-apps port-forward svc/graph-core 18083:8080
```

Example `cloudflared` config:

```yaml
tunnel: rescuenet-dev
credentials-file: /Users/YOUR_USER/.cloudflared/rescuenet-dev.json

ingress:
  - hostname: dev-app.rescuenet.co.za
    service: http://localhost:18080
  - hostname: dev-api.rescuenet.co.za
    service: http://localhost:18081
  - hostname: dev-admin.rescuenet.co.za
    service: http://localhost:18082
  - hostname: dev-graph.rescuenet.co.za
    service: http://localhost:18083
  - service: http_status:404
```

Typical setup:

```bash
cloudflared tunnel login
cloudflared tunnel create rescuenet-dev
cloudflared tunnel route dns rescuenet-dev dev-app.rescuenet.co.za
cloudflared tunnel route dns rescuenet-dev dev-api.rescuenet.co.za
cloudflared tunnel route dns rescuenet-dev dev-admin.rescuenet.co.za
cloudflared tunnel route dns rescuenet-dev dev-graph.rescuenet.co.za
cloudflared tunnel run rescuenet-dev
```

For safer demos, put Cloudflare Access in front of `dev-*` hostnames so only approved users can open them.

## Quick Copy-Paste DNS Tables

For the static landing page:

| Host | Type | Value |
|---|---|---|
| `rescuenet.co.za` | Provider-specific apex record | Use your static host instructions |
| `www.rescuenet.co.za` | CNAME | Use your static host instructions |

For future Kubernetes:

| Host | Type | Value |
|---|---|---|
| `app.rescuenet.co.za` | CNAME or A | Kubernetes ingress/load balancer |
| `api.rescuenet.co.za` | CNAME or A | Kubernetes ingress/load balancer |
| `admin.rescuenet.co.za` | CNAME or A | Kubernetes ingress/load balancer |
| `graph.rescuenet.co.za` | CNAME or A | Kubernetes ingress/load balancer |

For future local demos:

| Host | Type | Value |
|---|---|---|
| `dev-app.rescuenet.co.za` | CNAME | Cloudflare Tunnel-generated target |
| `dev-api.rescuenet.co.za` | CNAME | Cloudflare Tunnel-generated target |
| `dev-admin.rescuenet.co.za` | CNAME | Cloudflare Tunnel-generated target |
| `dev-graph.rescuenet.co.za` | CNAME | Cloudflare Tunnel-generated target |
