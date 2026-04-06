# Graph-core upgrade notes

## What changed

### 1. Scored routing
`/triage/assess` and `/intake/assess` now include:
- `ranked_destinations`
- `routing_summary`

Ranking uses:
- primary need match
- barrier-related support
- hierarchical location matching through `LOCATED_IN`
- availability status (`HAS_STATUS -> Available/Unavailable`)
- urgency fit (`accepted_urgencies` metadata or `HAS_URGENCY` edges)

### 2. Hierarchical location support
Location routing now works better when you model a hierarchy like:
- Fairland `LOCATED_IN` Randburg
- Randburg `LOCATED_IN` Johannesburg
- Johannesburg `LOCATED_IN` Gauteng

Resources and helpers linked to parent or child locations can still be scored.

### 3. Case timeline
Case context updates now create `Assessment` nodes linked by `UPDATED_TO`.

New endpoint:
- `GET /cases/{case_id}/timeline`

### 4. Schema cleanup
Duplicate schema and import issues were removed so the package is easier to maintain.

## Recommended data additions for testing

For resources/helpers, add metadata like:

```json
{
  "accepted_urgencies": ["urgent", "high"],
  "barrier_support": ["No Transport", "Unsafe To Travel"]
}
```

For status, create status nodes such as `Available` or `Unavailable` and connect with `HAS_STATUS`.

## Quick test flow

1. Start graph-core as usual.
2. Call `/triage/assess` with a message and optional location.
3. Check `intake.ranked_destinations`.
4. Call `/cases/intake` to persist a case.
5. Patch `/cases/{case_id}/context`.
6. Read `/cases/{case_id}/timeline`.

## Example triage request

```bash
curl -s -X POST "http://localhost:8000/triage/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need medical help in Johannesburg and I have no transport",
    "top_k": 5
  }' | jq
```

Look for:
- `triage`
- `intake.summary`
- `intake.ranked_destinations`
- `intake.routing_summary`
