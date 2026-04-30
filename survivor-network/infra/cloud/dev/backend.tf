terraform {
  backend "gcs" {
    bucket = "survivor-terraform-state-dev"
    prefix = "survivor-network/dev"
  }
}
