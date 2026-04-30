variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west2"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "europe-west2-a"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "survivor-dev"
}

variable "node_count" {
  description = "Number of nodes per zone"
  type        = number
  default     = 2
}

variable "machine_type" {
  description = "GCP machine type for cluster nodes"
  type        = string
  default     = "e2-standard-2"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_password" {
  description = "PostgreSQL password for survivor user"
  type        = string
  sensitive   = true
}
