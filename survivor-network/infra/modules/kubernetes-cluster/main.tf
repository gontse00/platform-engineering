# =============================================================================
# Kubernetes Cluster Module — GKE Autopilot (cost-efficient for dev)
# =============================================================================

variable "project_id" { type = string }
variable "region" { type = string }

variable "zone" {
  type    = string
  default = ""
}

variable "cluster_name" { type = string }

variable "node_count" {
  type    = number
  default = 2
}

variable "machine_type" {
  type    = string
  default = "e2-standard-2"
}

# Use standard GKE (not Autopilot) for more control in dev
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone != "" ? var.zone : var.region

  # Remove default node pool — we manage our own
  remove_default_node_pool = true
  initial_node_count       = 1

  # Network config
  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {}

  # Workload identity for secure pod-to-GCP auth
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Dev-friendly: no deletion protection
  deletion_protection = false
}

resource "google_container_node_pool" "default" {
  name       = "default-pool"
  location   = google_container_cluster.primary.location
  cluster    = google_container_cluster.primary.name
  node_count = var.node_count

  node_config {
    machine_type = var.machine_type
    disk_size_gb = 50
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    # Workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    labels = {
      env     = "dev"
      project = "survivor-network"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

output "endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_ca_certificate" {
  value     = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive = true
}
