#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# ==================================================================================
#  🏦 CREDIT RISK MVP - INFRASTRUCTURE SETUP
#  "One-Click" Deployment Script (Idempotent & Path-Agnostic)
# ==================================================================================

# 1. DYNAMIC PATH RESOLUTION
# This ensures the script works regardless of where you call it from (root or infra/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 2. ARGUMENT PARSING
PROJECT_ID=$1
REGION=$2

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "❌ Usage: ./setup.sh [PROJECT_ID] [REGION]"
  echo "   Example: ./setup.sh my-project-id us-central1"
  exit 1
fi

echo "🚀 Starting Deployment for Project: $PROJECT_ID ($REGION)"
echo "📂 Project Root detected at: $ROOT_DIR"

# ==================================================================================
#  PHASE 1: ENABLE APIs & IAM
# ==================================================================================
echo "🔌 Enabling Google Cloud APIs (This may take 30s)..."
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  --project=$PROJECT_ID --quiet

# PAUSE: Give Google's backend time to propagate the API changes
echo "⏳ Waiting 15s for APIs to warm up..."
sleep 15

# ==================================================================================
#  PHASE 2: STORAGE & DATA
# ==================================================================================
BUCKET_NAME="${PROJECT_ID}-data"

echo "📦 Setting up Cloud Storage: gs://$BUCKET_NAME"
if ! gsutil ls -b gs://$BUCKET_NAME > /dev/null 2>&1; then
  gsutil mb -l $REGION gs://$BUCKET_NAME
  echo "   ✅ Bucket created."
else
  echo "   ⚠️ Bucket already exists. Skipping."
fi

# ==================================================================================
#  PHASE 3: BIGQUERY (Robust Creation)
# ==================================================================================
DATASET_NAME="credit_risk_mvp"
echo "🗄️  Setting up BigQuery Dataset: $DATASET_NAME"

# We use 'bq mk' with '|| true' to suppress errors if it exists. 
# This avoids the 'bq ls' hang issue entirely.
bq --location=$REGION mk -d --project_id=$PROJECT_ID $DATASET_NAME > /dev/null 2>&1 || echo "   ⚠️ Dataset likely exists or API busy (continuing)..."

# ==================================================================================
#  PHASE 4: DATA GENERATION
# ==================================================================================
# We assume 'y' for automation (Or you can keep the prompt if you prefer)
echo "🎲 Generating Synthetic Training Data..."

# Install dependencies strictly for the script (quietly)
pip3 install google-cloud-storage pandas faker > /dev/null 2>&1

# EXECUTE THE SCRIPT USING THE DYNAMIC ROOT PATH
# This fixes the "File not found" error you saw earlier
python3 "$ROOT_DIR/scripts/generate_training_data.py" $BUCKET_NAME

echo "📥 Loading History CSV into BigQuery..."
bq load \
  --autodetect \
  --source_format=CSV \
  --skip_leading_rows=1 \
  --replace \
  $PROJECT_ID:$DATASET_NAME.credit_history \
  gs://$BUCKET_NAME/credit_history.csv > /dev/null 2>&1

echo "   ✅ Data loaded successfully."

# ==================================================================================
#  PHASE 5: SQL DEPLOYMENT (Tables & Models)
# ==================================================================================
echo "🏗️  Deploying SQL Schema & Models..."

# We replace the placeholders in the SQL file dynamically and run it
sed "s/PROJECT_ID/$PROJECT_ID/g; s/BUCKET_NAME/$BUCKET_NAME/g" "$ROOT_DIR/sql/schema.sql" > "$ROOT_DIR/sql/processed_schema.sql"

# Run the query (This creates External Tables and Trains the Model)
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < "$ROOT_DIR/sql/processed_schema.sql"
rm "$ROOT_DIR/sql/processed_schema.sql"

echo "   ✅ Model training initiated (Logistic Regression)."

# ==================================================================================
#  PHASE 6: CLOUD RUN DEPLOYMENT
# ==================================================================================
echo "🚀 Deploying Frontend to Cloud Run..."

gcloud run deploy credit-risk-portal \
  --source "$ROOT_DIR/frontend" \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --quiet

echo "========================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================================"