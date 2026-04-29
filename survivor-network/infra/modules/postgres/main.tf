# PostgreSQL Module (Cloud SQL)

variable "project_id" { type = string }
variable "region" { type = string }
variable "db_name" { type = string; default = "survivor" }
variable "db_user" { type = string; default = "survivor" }
variable "tier" { type = string; default = "db-f1-micro" }

# TODO: Implement Cloud SQL instance
# resource "google_sql_database_instance" "main" { ... }
# resource "google_sql_database" "db" { ... }
# resource "google_sql_user" "user" { ... }

output "connection_string" {
  value = "postgresql://${var.db_user}:PASSWORD@placeholder:5432/${var.db_name}"
}

output "instance_name" {
  value = "survivor-db-dev"
}
