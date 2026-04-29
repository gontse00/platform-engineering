# Local Infrastructure (Kind)

The local Kind cluster infrastructure lives in `../../survivor-infra/`.
This directory is a pointer — the actual Terraform files remain in their original location
to avoid breaking the existing local development workflow.

## Usage

```bash
cd ../../survivor-infra
terraform init
terraform apply -auto-approve
```

See `../../survivor-infra/README.md` for full documentation.
