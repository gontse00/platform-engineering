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
  source     = "../../modules/container-registry"
  project_id = var.project_id
  region     = var.region
}

# --- GKE Kubernetes Cluster ---
module "kubernetes_cluster" {
  source       = "../../modules/kubernetes-cluster"
  project_id   = var.project_id
  region       = var.region
  zone         = var.zone
  cluster_name = var.cluster_name
  node_count   = var.node_count
  machine_type = var.machine_type
}

# --- Cloud SQL PostgreSQL ---
module "postgres" {
  source      = "../../modules/postgres"
  project_id  = var.project_id
  region      = var.region
  db_name     = "survivor"
  db_user     = "survivor"
  db_password = var.db_password
  tier        = var.db_tier
}

# --- Cloud Storage (attachments/evidence) ---
module "object_storage" {
  source      = "../../modules/object-storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = "${var.project_id}-survivor-storage"
}
