# =============================================================================
# Object Storage Module — Cloud Storage
# =============================================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "bucket_name" { type = string }

resource "google_storage_bucket" "attachments" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = true  # dev — allow easy teardown

  uniform_bucket_level_access = true

  versioning {
    enabled = false  # dev — no versioning needed
  }

  lifecycle_rule {
    condition {
      age = 90  # auto-delete after 90 days in dev
    }
    action {
      type = "Delete"
    }
  }
}

output "bucket_name" {
  value = google_storage_bucket.attachments.name
}

output "bucket_url" {
  value = "gs://${google_storage_bucket.attachments.name}"
}
