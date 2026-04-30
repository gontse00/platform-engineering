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

# --- Artifact Registry ---
variable "artifact_registry_repo" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "survivor-network"
}

# --- GKE ---
variable "gke_cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "survivor-network-dev"
}

variable "gke_node_count" {
  description = "Number of nodes per zone"
  type        = number
  default     = 2
}

variable "gke_machine_type" {
  description = "GCP machine type for cluster nodes"
  type        = string
  default     = "e2-standard-2"
}

# --- Cloud SQL ---
variable "cloud_sql_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "survivor-network-dev-db"
}

variable "cloud_sql_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = "survivor"
}

variable "cloud_sql_user" {
  description = "PostgreSQL user"
  type        = string
  default     = "survivor"
}

variable "cloud_sql_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "cloud_sql_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

# --- Cloud Storage ---
variable "gcs_bucket_name" {
  description = "Cloud Storage bucket name for attachments"
  type        = string
  default     = "survivor-rescue-net-dev-attachments"
}
