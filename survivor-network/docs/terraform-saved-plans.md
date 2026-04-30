# Terraform Saved Plan Files

## Why Saved Plans?

Without saved plans:
```bash
terraform plan    # shows what will change
terraform apply   # re-calculates and applies — may differ from what you reviewed!
```

With saved plans:
```bash
terraform plan -out=tfplan   # saves exact changes to a file
terraform apply tfplan       # applies EXACTLY what was planned — deterministic
```

Benefits:
- **Deterministic applies** — what you reviewed is exactly what gets applied
- **Safer destroys** — destroy is a two-step process (plan-destroy → apply)
- **CI/CD friendly** — plan in one step, apply in another (with approval gate)
- **Audit trail** — plan files can be inspected before apply

## Workflow

### Create/Update Infrastructure

```bash
# 1. Plan and save
make cloud-dev-plan

# 2. Review the plan
cd infra/cloud/dev && terraform show tfplan

# 3. Apply the saved plan
make cloud-dev-apply
```

### Destroy Infrastructure

```bash
# 1. Plan the destroy and save
make cloud-dev-plan-destroy

# 2. Review what will be destroyed
cd infra/cloud/dev && terraform show destroy.tfplan

# 3. Apply the destroy plan
make cloud-dev-destroy
```

## Inspecting Plan Files

```bash
cd infra/cloud/dev

# Human-readable summary
terraform show tfplan

# JSON output (for CI/CD or scripting)
terraform show -json tfplan | jq '.resource_changes[] | {action: .change.actions, address: .address}'
```

## Plan File Security

Plan files may contain sensitive values (passwords, connection strings). They are:
- Excluded from git via `.gitignore`
- Stored only locally
- Ephemeral — regenerate before each apply

## CI/CD Integration

Future GitHub Actions workflow:

```yaml
jobs:
  plan:
    steps:
      - run: terraform plan -out=tfplan
      - uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infra/cloud/dev/tfplan

  apply:
    needs: plan
    environment: dev  # requires manual approval
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: tfplan
      - run: terraform apply tfplan
```

## Makefile Targets

| Target | Command | Purpose |
|---|---|---|
| `cloud-dev-plan` | `terraform plan -out=tfplan` | Save apply plan |
| `cloud-dev-apply` | `terraform apply tfplan` | Apply saved plan |
| `cloud-dev-plan-destroy` | `terraform plan -destroy -out=destroy.tfplan` | Save destroy plan |
| `cloud-dev-destroy` | `terraform apply destroy.tfplan` | Apply destroy plan |
