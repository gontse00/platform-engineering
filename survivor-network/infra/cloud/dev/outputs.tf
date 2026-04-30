output "registry_url" {
  description = "Artifact Registry URL for docker push"
  value       = module.container_registry.registry_url
}

output "cluster_name" {
  description = "GKE cluster name"
  value       = module.kubernetes_cluster.cluster_name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = module.kubernetes_cluster.endpoint
}

output "cluster_location" {
  description = "GKE cluster location (zone)"
  value       = var.zone
}

output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.postgres.instance_name
}

output "database_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.postgres.connection_string
  sensitive   = true
}

output "storage_bucket" {
  description = "Cloud Storage bucket name"
  value       = module.object_storage.bucket_name
}

output "storage_bucket_url" {
  description = "Cloud Storage bucket URL"
  value       = module.object_storage.bucket_url
}
