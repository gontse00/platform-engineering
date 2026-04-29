output "cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = module.kubernetes_cluster.endpoint
}

output "registry_url" {
  description = "Container registry URL"
  value       = module.container_registry.registry_url
}

output "database_connection" {
  description = "PostgreSQL connection string"
  value       = module.postgres.connection_string
  sensitive   = true
}

output "storage_bucket" {
  description = "Object storage bucket name"
  value       = module.object_storage.bucket_name
}
