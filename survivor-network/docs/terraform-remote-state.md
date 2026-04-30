# Terraform Remote State — GCS Backend

## Why Remote State?

Local Terraform state (`terraform.tfstate`) is:
- Not shareable between team members
- At risk of accidental deletion
- Not locked for concurrent operations
- Not versioned

Remote state in GCS provides:
- Team collaboration (shared state)
- State locking (prevents concurrent modifications)
- Versioning (rollback if state is corrupted)
- Secure storage (IAM-controlled access)

## How It Works

Terraform stores its state file in a GCS bucket instead of locally. The backend is configured in `backend.tf`:

```hcl
terraform {
  backend "gcs" {
    bucket = "survivor-terraform-state-dev"
    prefix = "survivor-network/dev"
  }
}
```

State is stored at: `gs://survivor-terraform-state-dev/survivor-network/dev/default.tfstate`

## Setup

### 1. Create the GCS bucket

```bash
make terraform-state-bucket-create
```

Or manually:

```bash
gsutil mb -p survivor-rescue-net-dev -l europe-west2 gs://survivor-terraform-state-dev
```

### 2. Enable versioning

```bash
make terraform-state-enable-versioning
```

Or manually:

```bash
gsutil versioning set on gs://survivor-terraform-state-dev
```

### 3. Migrate local state to remote

```bash
make terraform-state-migrate
```

Or manually:

```bash
cd infra/cloud/dev
terraform init -migrate-state
```

Terraform will ask:
```
Do you want to copy existing state to the new backend?
```

Answer **yes** to copy your existing local state to GCS.

### 4. Verify migration

```bash
# Check state is accessible
terraform state list

# Verify local state file is no longer used
ls -la terraform.tfstate
# Should show an empty file or be absent

# Confirm remote state
gsutil cat gs://survivor-terraform-state-dev/survivor-network/dev/default.tfstate | head -5
```

## After Migration

- `terraform plan` and `terraform apply` now read/write state from GCS
- The local `terraform.tfstate` file can be deleted (Terraform leaves a backup)
- State locking is automatic via GCS object locking
- Multiple team members can now safely run Terraform

## Troubleshooting

### "Error acquiring the state lock"

Someone else (or a previous interrupted run) holds the lock:

```bash
# Find the lock ID from the error message
terraform force-unlock LOCK_ID
```

### "Backend configuration changed"

If you modify `backend.tf`, re-initialize:

```bash
terraform init -reconfigure
```

### "Error loading state"

If the bucket doesn't exist or you lack permissions:

```bash
# Verify bucket exists
gsutil ls gs://survivor-terraform-state-dev

# Verify your auth
gcloud auth application-default print-access-token
```

### Reverting to local state

If you need to go back to local state temporarily:

```bash
# Comment out backend.tf content
terraform init -migrate-state
# Answer yes to copy state back locally
```

## Security

- The state bucket is project-scoped (only project members can access)
- State may contain sensitive values (Cloud SQL passwords) — treat the bucket as sensitive
- Consider adding a bucket policy to restrict access to specific service accounts
- Do NOT make the bucket public

## Makefile Targets

```bash
make terraform-state-bucket-create      # Create the GCS bucket
make terraform-state-enable-versioning  # Enable bucket versioning
make terraform-state-migrate            # Migrate local → remote
```
