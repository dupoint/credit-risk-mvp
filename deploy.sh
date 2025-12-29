#!/bin/bash
set -e

# Usage: ./deploy.sh [PROJECT_ID]
if [ -z "$1" ]; then
  echo "❌ Error: Project ID required."
  echo "Usage: ./deploy.sh [PROJECT_ID]"
  exit 1
fi

PROJECT_ID=$(echo "$1" | tr -d '[]')
REGION="us-central1"

echo "🚀 Starting Deployment for Project: $PROJECT_ID"

# ==============================================================================
# 0. BOOTSTRAP APIs (CRITICAL FOR FRESH PROJECTS)
# ==============================================================================
echo "🔌 Enabling required Google Cloud APIs..."
gcloud services enable \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  compute.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  --project $PROJECT_ID

echo "⏳ Waiting for Service Accounts to provision..."

# --- NEW BLOCK: SAFETY WAIT LOOP ---
# We calculate the Project Number early to check the specific email
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "   Checking availability of: $COMPUTE_SA"
MAX_RETRIES=20
COUNT=0
# Loop until the Service Account is found or we timeout
while ! gcloud iam service-accounts describe $COMPUTE_SA --project=$PROJECT_ID > /dev/null 2>&1; do
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "❌ Timeout waiting for Service Account creation. Try re-running the script."
    exit 1
  fi
  echo "   ... Google is still creating the account. Sleeping 5s..."
  sleep 5
  ((COUNT++))
done
echo "✅ Service Account is ready!"
# --- END NEW BLOCK ---

# ==============================================================================
# 1. INFRASTRUCTURE (Terraform)
# ==============================================================================
echo "🏗️ Setting up Infrastructure..."
cd infra

# Initialize Terraform
terraform init

# Apply configuration
terraform apply \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -auto-approve

cd ..

# ==============================================================================
# 2. DATA GENERATION
# ==============================================================================
echo "🎲 Checking Data..."
BUCKET_NAME="${PROJECT_ID}-data"

# Install dependencies if missing
pip3 install google-cloud-storage google-cloud-bigquery pandas faker flask gunicorn numpy --upgrade --quiet

echo "   ⚙️ Generating 5,000 records..."
python3 scripts/generate_training_data.py $BUCKET_NAME

echo "📥 Loading Data into BigQuery..."
python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='$PROJECT_ID', location='$REGION')
job_config = bigquery.LoadJobConfig(source_format='CSV', skip_leading_rows=1, autodetect=True, write_disposition='WRITE_TRUNCATE')
uri = 'gs://$BUCKET_NAME/credit_history.csv'
load_job = client.load_table_from_uri(uri, 'credit_risk_mvp.credit_history', job_config=job_config)
load_job.result()
print('   ✅ Data Loaded.')
"

# ==============================================================================
# 3. SQL MODEL TRAINING
# ==============================================================================
echo "🧠 Training/Updating Model..."
sed "s/PROJECT_ID/$PROJECT_ID/g" sql/schema.sql > sql/schema_processed.sql
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/schema_processed.sql

# ==============================================================================
# 4. APP DEPLOYMENT (Cloud Run)
# ==============================================================================
echo "🚀 Deploying to Cloud Run..."

# Redundant safety check for IAM (Silent)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:${COMPUTE_SA} \
    --role=roles/storage.admin --condition=None --quiet > /dev/null 2>&1

gcloud run deploy credit-risk-portal \
  --source frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --project $PROJECT_ID

echo "✅ DONE. System Live."