# Kubernetes Cluster Module (GKE)

variable "project_id" { type = string }
variable "region" { type = string }
variable "cluster_name" { type = string }
variable "node_count" { type = number; default = 2 }
variable "machine_type" { type = string; default = "e2-standard-2" }

# TODO: Implement GKE cluster resource
# resource "google_container_cluster" "primary" { ... }
# resource "google_container_node_pool" "default" { ... }

output "endpoint" {
  value = "https://placeholder-cluster-endpoint"
}

output "cluster_name" {
  value = var.cluster_name
}
