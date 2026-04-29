You are working in my repo on branch `rescue-net`.

Project path:
`survivor-network/`

The previous update fixed the primary+secondary needs combination, but several requested items are still missing.

Please finish the remaining local runtime polish.

Tasks:

1. Fix domestic violence rule priority in:
   `incident-service/app/routes/incidents.py`

The phrase:
`"My husband is beating me right now, I locked myself in the bathroom"`

must classify as:

- urgency: critical
- safety_risk: immediate
- incident_type: Domestic Violence
- needs includes Emergency Shelter
- needs includes Protection Order Support

The current generic active attack rule can still classify it as Assault. Move the Domestic Violence critical rule above the generic active attack rule, or implement a simple specificity/override rule.

2. Standardise incident_type labels.

Use these preferred labels:

- Sexual Assault
- Domestic Violence
- Assault
- Medical Emergency
- Mental Health Crisis
- Medication Access
- Disaster / Emergency
- Robbery
- Hijacking
- Break-in
- Child Endangerment
- Protection Order
- Transport Support

Update rules:
- building collapse / trapped / disaster / fire / flood -> Disaster / Emergency
- overdose / too many pills / suicidal / self-harm -> Mental Health Crisis or Medical Emergency, but be consistent
- counselling / trauma / panic attack / can't cope -> Mental Health Crisis
- protection order / restraining order -> Protection Order
- stranded / no transport / need a ride -> Transport Support
- ARVs / HIV medication / medication stolen -> Medication Access

3. Add incident-service unit tests.

Create:
`survivor-network/incident-service/tests/test_safety_normalization.py`

Test `_normalize_case_safety` directly.

Include tests for:
- sexual assault
- active domestic violence
- stabbing / bleeding
- overdose / self-harm
- building collapse / trapped
- HIV medication / ARVs
- vague help should not over-escalate
- primary + secondary needs are combined
- duplicate session id idempotency if feasible; if DB setup is too heavy, add a TODO and at least test normalization now

4. Update Makefile.

In `survivor-network/Makefile`:

- add `restart-service` target:
  `make restart-service SVC=incident-service`
- require SVC and print usage if missing
- run rollout restart and rollout status for `deploy/$(SVC)`
- add incident-service tests to `local-test`:
  `cd incident-service && python3 -m pytest tests/ -v`
- add participant-service tests only if `participant-service/tests` exists
- update help output with:
  - restart-service
  - local-reset
  - clear-local-cases
  - e2e-local

5. Update README.

Replace or expand `survivor-network/README.md` with sections:

- Survivor Network overview
- Service ownership
- Local development prerequisites
- Local build/deploy workflow:
  make local-up
  make helm-lint-local
  make helm-template-local
  make local-build
  make local-load-kind
  make deploy-local-helm
  make status
  make smoke-local
- Runtime quality checks:
  make local-reset
  make clear-local-cases
  make e2e-local
- Logs/restarts:
  make logs SVC=chatbot-service
  make restart-service SVC=incident-service
- Local URLs
- Deterministic safety rules:
  explain that they run even when LLM_ENABLED=false
- Known caveats:
  database URLs are ConfigMaps locally
  startup migration is temporary until Alembic
  reset endpoint requires ENVIRONMENT=local/dev/test
  cloud deployment is still a skeleton
- Roadmap:
  keep the existing service wiring roadmap

6. Do not change cloud infrastructure.
7. Do not rewrite the whole app.
8. Keep local Helm deployment working.

Acceptance criteria:
- DV active attack maps to Domestic Violence.
- Incident type labels are consistent.
- `pytest incident-service/tests -v` passes.
- `make local-test` includes incident-service tests.
- `make restart-service SVC=incident-service` works.
- README documents local runtime workflow.