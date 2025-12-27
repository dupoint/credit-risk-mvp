#!/bin/bash

# ==================================================================================
# SETUP SCRIPT FOR CREDIT RISK AI PLATFORM
# Usage: ./setup.sh [PROJECT_ID] [REGION]
# Example: ./setup.sh my-new-project-123 us-central1
# ==================================================================================

# 1. CONFIGURATION
# ----------------------------------------------------------------------------------
if [ -z "$1" ]; then
    echo "❌ Error: No Project ID provided."
    echo "Usage: ./setup.sh [PROJECT_ID] [REGION]"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1} # Default to us-central1 if not provided
BUCKET_NAME="${PROJECT_ID}-data"

echo "🚧 STARTING SETUP..."
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo "   Bucket:  $BUCKET_NAME"
echo "------------------------------------------------------------------"

# Switch to the target project
gcloud config set project $PROJECT_ID

# 2. ENABLE GOOGLE CLOUD APIS
# ----------------------------------------------------------------------------------
echo "🔌 Enabling required APIs (this may take a minute)..."
gcloud services enable \
  bigquery.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  documentai.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project $PROJECT_ID

# 3. CREATE INFRASTRUCTURE (Storage & BigQuery)
# ----------------------------------------------------------------------------------
echo "📦 Creating Storage Bucket..."
# Check if bucket exists, if not create it
if ! gsutil ls -b gs://$BUCKET_NAME > /dev/null 2>&1; then
  gsutil mb -p $PROJECT_ID -l $REGION gs://$BUCKET_NAME/
  echo "   ✅ Bucket created: gs://$BUCKET_NAME"
else
  echo "   ⚠️ Bucket already exists. Skipping."
fi

echo "🗄️  Creating BigQuery Dataset..."
# Check if dataset exists, if not create it
if ! bq ls --project_id=$PROJECT_ID credit_risk_mvp > /dev/null 2>&1; then
  bq --location=$REGION mk -d --project_id=$PROJECT_ID credit_risk_mvp
  echo "   ✅ Dataset created."
else
  echo "   ⚠️ Dataset 'credit_risk_mvp' already exists. Skipping."
fi

# 4. DATA GENERATION (Synthetic Data)
# ----------------------------------------------------------------------------------
echo "------------------------------------------------------------------"
read -p "🎲 Do you want to generate 5,000 synthetic training records? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "⚡ Installing dependencies for data generator..."
    pip install google-cloud-storage --quiet

    echo "🚀 Running Data Generator Script..."
    # Passes the bucket name to the python script
    python3 ../scripts/generate_training_data.py $BUCKET_NAME
    
    echo "📥 Loading History CSV into BigQuery..."
    # Load the CSV file that the python script just uploaded to GCS
    bq load \
      --autodetect \
      --source_format=CSV \
      --skip_leading_rows=1 \
      credit_risk_mvp.credit_history \
      gs://$BUCKET_NAME/credit_history.csv
      
    echo "   ✅ Data loaded successfully."
else
    echo "⏩ Skipping data generation."
fi

# 5. DEPLOY DATABASE OBJECTS (Views & Models)
# ----------------------------------------------------------------------------------
echo "🧠 Deploying SQL Views and ML Models..."

# Create a temporary SQL file with the real bucket name injected
# We use sed to replace @BUCKET_NAME with the variable $BUCKET_NAME
sed "s/@BUCKET_NAME/$BUCKET_NAME/g" ../sql/schema.sql > ../sql/deployment.sql

# Execute the SQL
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < ../sql/deployment.sql

# Clean up temp file
rm ../sql/deployment.sql

echo "   ✅ Database objects deployed."

# 6. DEPLOY FRONTEND (Cloud Run)
# ----------------------------------------------------------------------------------
echo "🚀 Deploying Streamlit App to Cloud Run..."

# Move to frontend directory to execute deploy
cd ../frontend

gcloud run deploy credit-risk-portal \
  --source . \
  --project=$PROJECT_ID \
  --region=$REGION \
  --port=8501 \
  --allow-unauthenticated

# Move back to infra directory
cd ../infra

echo "------------------------------------------------------------------"
echo "✅ SETUP COMPLETE!"
echo "   Your app should be live at the URL above."
echo "------------------------------------------------------------------"