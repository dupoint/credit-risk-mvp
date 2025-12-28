# infra/main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VARIABLES (So we can pass them in via command line)
variable "project_id" {}
variable "region" { default = "us-central1" }

# 1. ENABLE APIS
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# 2. STORAGE BUCKET
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.project_id}-data"
  location      = var.region
  
  # 1. ALLOW DELETION EVEN IF FULL
  force_destroy = true 
  
  # 2. FIX THE 412 ERROR (Security Policy)
  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis]
}

# 3. BIGQUERY DATASET
resource "google_bigquery_dataset" "dataset" {
  dataset_id  = "credit_risk_mvp"
  location    = var.region
  
  # 3. ALLOW DELETION EVEN IF IT HAS TABLES
  delete_contents_on_destroy = true 

  depends_on = [google_project_service.apis]
}

# OUTPUTS (To pass to the shell script later)
output "bucket_name" {
  value = google_storage_bucket.data_bucket.name
}

# 1. Get Project Metadata (to find the Project Number dynamically)
data "google_project" "project" {
}

# 2. Grant Permissions to the Default Compute Service Account
# This fixes the "Source Upload" error during gcloud run deploy
resource "google_project_iam_member" "compute_sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# 3. Grant Permissions to Cloud Build (Future Proofing)
# If we move to Cloud Build later, it also needs this
resource "google_project_iam_member" "cloudbuild_sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# 1. ALLOW LOGGING (Fixes "Permission to write logs")
resource "google_project_iam_member" "compute_sa_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# 2. ALLOW ARTIFACT REGISTRY (Prevents the next error you are likely to hit)
resource "google_project_iam_member" "compute_sa_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# 3. ALLOW STORAGE OBJECT ADMIN (Re-confirming this exists)
resource "google_project_iam_member" "compute_sa_storage_admin_confirm" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# 4. ALLOW BIGQUERY (Fixes "Access Denied" on Analyze)
resource "google_project_iam_member" "compute_sa_bq_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}