# Object Storage Module (Cloud Storage)

variable "project_id" { type = string }
variable "region" { type = string }
variable "bucket_name" { type = string }

# TODO: Implement Cloud Storage bucket
# resource "google_storage_bucket" "attachments" { ... }

output "bucket_name" {
  value = var.bucket_name
}

output "bucket_url" {
  value = "gs://${var.bucket_name}"
}
