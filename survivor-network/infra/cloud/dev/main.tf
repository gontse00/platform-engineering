# =============================================================================
# Survivor Network — Cloud Dev Environment
# =============================================================================
# This Terraform configuration provisions the cloud dev environment.
# Designed for GCP but module interfaces are generic.
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

# --- Container Registry ---
module "container_registry" {
  source     = "../../modules/container-registry"
  project_id = var.project_id
  region     = var.region
}

# --- Kubernetes Cluster ---
module "kubernetes_cluster" {
  source       = "../../modules/kubernetes-cluster"
  project_id   = var.project_id
  region       = var.region
  cluster_name = var.cluster_name
  node_count   = var.node_count
  machine_type = var.machine_type
}

# --- PostgreSQL ---
module "postgres" {
  source       = "../../modules/postgres"
  project_id   = var.project_id
  region       = var.region
  db_name      = "survivor"
  db_user      = "survivor"
}

# --- Object Storage ---
module "object_storage" {
  source      = "../../modules/object-storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = "${var.project_id}-survivor-storage"
}
