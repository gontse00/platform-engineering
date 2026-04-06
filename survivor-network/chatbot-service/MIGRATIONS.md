# Database migrations

This service now uses Alembic to keep the PostgreSQL schema aligned with the application models.

## What changed

- JSONB state fields are now tracked with `MutableDict`, so in-place state updates persist reliably.
- `app.db.init_db` now upgrades the database to the latest Alembic revision.
- A baseline migration was added to create missing tables and backfill newer columns/indexes into older deployments.

## Local usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the migration/bootstrap step:

```bash
python -m app.db.init_db
```

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Kubernetes usage

The existing init job still works, but now runs Alembic-backed upgrades:

```bash
kubectl delete job -n survivor-apps chatbot-service-init-db --ignore-not-found
kubectl apply -f k8s/init-db-job.yaml
kubectl logs -n survivor-apps job/chatbot-service-init-db -f
```

Then restart the service:

```bash
kubectl rollout restart deployment chatbot-service -n survivor-apps
kubectl rollout status deployment chatbot-service -n survivor-apps
```

## Adding future revisions

Create a new revision:

```bash
alembic revision -m "describe change"
```

Apply revisions:

```bash
alembic upgrade head
```
