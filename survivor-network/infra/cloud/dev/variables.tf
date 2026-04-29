variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "africa-south1"
}

variable "cluster_name" {
  description = "Kubernetes cluster name"
  type        = string
  default     = "survivor-dev"
}

variable "node_count" {
  description = "Number of nodes in the cluster"
  type        = number
  default     = 2
}

variable "machine_type" {
  description = "GCP machine type for cluster nodes"
  type        = string
  default     = "e2-standard-2"
}
