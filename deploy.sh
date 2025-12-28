#!/bin/bash
set -e

PROJECT_ID=$1
REGION="us-central1"

# START NEW BLOCK: Sanitizer
# This strips unexpected brackets '[' or ']' if you copy-pasted them by mistake
PROJECT_ID=$(echo "$PROJECT_ID" | tr -d '[]')
# END NEW BLOCK

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Usage: ./deploy.sh [PROJECT_ID]"
  exit 1
fi

echo "🚀 Starting Principal-Grade Deployment..."

# --- NEW: BOOTSTRAP STEP ---
# This fixes the "Chicken and Egg" error by enabling the Manager APIs manually first
echo "🔌 Bootstrapping Critical APIs..."
gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com \
  --project $PROJECT_ID --quiet
# ---------------------------

# ---------------------------------------------------------
# STEP 1: INFRASTRUCTURE (Terraform)
# ---------------------------------------------------------
echo "🏗️  Applying Terraform Infrastructure..."
cd infra
terraform init
terraform apply -auto-approve \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION"
cd ..

# ---------------------------------------------------------
# STEP 2: DATA & MODELS (Python)
# ---------------------------------------------------------
echo "🎲 Checking Data..."
BUCKET_NAME="${PROJECT_ID}-data"

# Install deps silently (Fast if already installed)
pip3 install google-cloud-storage google-cloud-bigquery pandas faker --upgrade --quiet

# CHECK: If file exists, skip generation
if gsutil ls gs://$BUCKET_NAME/credit_history.csv > /dev/null 2>&1; then
  echo "   ⚠️ Data already exists in gs://$BUCKET_NAME. Skipping generation."
else
  echo "   ⚙️ Generating new data..."
  python3 scripts/generate_training_data.py $BUCKET_NAME
fi

# Load Data (This is fast, so we can re-run it safely to ensure BQ is fresh)
echo "📥 Ensuring BigQuery Data is loaded..."
python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='$PROJECT_ID', location='$REGION')
job_config = bigquery.LoadJobConfig(source_format='CSV', skip_leading_rows=1, autodetect=True, write_disposition='WRITE_TRUNCATE')
uri = 'gs://$BUCKET_NAME/credit_history.csv'
client.load_table_from_uri(uri, 'credit_risk_mvp.credit_history', job_config=job_config).result()
"

# Train Model
echo "🧠 Training Model..."
sed "s/PROJECT_ID/$PROJECT_ID/g; s/BUCKET_NAME/$BUCKET_NAME/g" sql/schema.sql > sql/processed_schema.sql
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/processed_schema.sql
rm sql/processed_schema.sql

# ---------------------------------------------------------
# STEP 3: DEPLOY APP
# ---------------------------------------------------------
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy credit-risk-portal \
  --source frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --quiet

echo "✅ DONE. System Live."
