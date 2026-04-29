# Container Registry Module (GCP Artifact Registry)

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
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}
