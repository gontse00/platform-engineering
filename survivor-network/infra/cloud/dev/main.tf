# =============================================================================
# Survivor Network — Cloud Dev Environment (GCP)
# Project: survivor-rescue-net-dev
# Region: europe-west2
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Container Registry (Artifact Registry) ---
module "container_registry" {
  source        = "../../modules/container-registry"
  project_id    = var.project_id
  region        = var.region
  repository_id = var.artifact_registry_repo
}

# --- GKE Kubernetes Cluster ---
module "kubernetes_cluster" {
  source       = "../../modules/kubernetes-cluster"
  project_id   = var.project_id
  region       = var.region
  zone         = var.zone
  cluster_name = var.gke_cluster_name
  node_count   = var.gke_node_count
  machine_type = var.gke_machine_type
}

# --- Cloud SQL PostgreSQL ---
module "postgres" {
  source        = "../../modules/postgres"
  project_id    = var.project_id
  region        = var.region
  instance_name = var.cloud_sql_instance_name
  db_name       = var.cloud_sql_database
  db_user       = var.cloud_sql_user
  db_password   = var.cloud_sql_password
  tier          = var.cloud_sql_tier
}

# --- Cloud Storage (attachments/evidence) ---
module "object_storage" {
  source      = "../../modules/object-storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = var.gcs_bucket_name
}
