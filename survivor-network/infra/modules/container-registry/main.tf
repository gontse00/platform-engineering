# =============================================================================
# Container Registry Module — GCP Artifact Registry
# =============================================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" {
  type    = string
  default = "survivor-images"
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "Survivor Network container images"

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "repository_id" {
  value = google_artifact_registry_repository.images.repository_id
}
