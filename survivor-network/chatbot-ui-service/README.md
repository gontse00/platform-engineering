# chatbot-ui

Separate frontend service for the Survivor Network chatbot experience.

## What it does

- Starts and resumes a support session
- Sends chat messages to `chatbot-service`
- Shows a survivor-facing conversation view
- Displays current stage, urgency, queue, and missing fields
- Supports quick actions and attachment upload
- Submits the case when enough detail has been collected

## Local run

```bash
npm install
npm run dev
```

Set a custom API base URL if needed:

```bash
VITE_CHATBOT_API_BASE_URL=http://chatbot-service.127.0.0.1.nip.io npm run dev
```

## Build container

```bash
docker build -t chatbot-ui:latest .
```

## Run on kind

```bash
kind load docker-image chatbot-ui:latest --name survivor-net
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl rollout status deployment/chatbot-ui -n survivor-apps
```

Open:

- `http://chatbot-ui.127.0.0.1.nip.io`

## UX notes

This service is intentionally separate from `chatbot-service` so the API and UI can evolve independently.
