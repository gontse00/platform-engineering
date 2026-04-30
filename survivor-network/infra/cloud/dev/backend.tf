# Remote state backend — uncomment after creating the bucket manually:
#   gsutil mb -l europe-west2 gs://survivor-rescue-net-dev-tfstate
#
# terraform {
#   backend "gcs" {
#     bucket = "survivor-rescue-net-dev-tfstate"
#     prefix = "cloud/dev"
#   }
# }
