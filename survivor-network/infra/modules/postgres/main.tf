# =============================================================================
# PostgreSQL Module — Cloud SQL
# =============================================================================

variable "project_id" { type = string }
variable "region" { type = string }

variable "db_name" {
  type    = string
  default = "survivor"
}

variable "db_user" {
  type    = string
  default = "survivor"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "tier" {
  type    = string
  default = "db-f1-micro"
}

variable "instance_name" {
  type    = string
  default = "survivor-db-dev"
}

resource "google_sql_database_instance" "main" {
  name             = var.instance_name
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.tier
    availability_type = "ZONAL" # dev — no HA needed
    disk_size         = 10
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled = true # dev — allow public IP for simplicity
      # For production: use private IP + VPC peering
    }

    backup_configuration {
      enabled = false # dev — no backups needed
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = false # dev — allow easy teardown
}

resource "google_sql_database" "db" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "user" {
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

output "connection_string" {
  value     = "postgresql://${var.db_user}:${var.db_password}@${google_sql_database_instance.main.public_ip_address}:5432/${var.db_name}"
  sensitive = true
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}

output "public_ip" {
  value = google_sql_database_instance.main.public_ip_address
}
