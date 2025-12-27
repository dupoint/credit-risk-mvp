Markdown

# 🏦 Credit Risk Decision Engine (GCP Serverless MVP)

A serverless, real-time Machine Learning pipeline built on Google Cloud Platform to assess loan application risk. This project demonstrates an end-to-end "Lakehouse" architecture using **BigQuery ML** for inference, **Cloud Run** for the frontend, and **Cloud Storage** for document ingestion.

## 🚀 Project Overview

The goal of this MVP is to replace manual credit underwriting with an automated, explainable AI decision engine.

* **Ingestion:** Simulates the processing of 5,000+ loan application PDFs (via Document AI) into structured JSON.
* **Data Warehouse:** Uses BigQuery External Tables to query raw JSON data directly (ELT pattern) without complex ETL pipelines.
* **Modeling:** Trains a **Logistic Regression** model entirely within BigQuery (BQML) to predict default risk (AUC ~0.94).
* **Serving:** Deploys a **Streamlit** web interface on **Cloud Run** that performs real-time inference against the BigQuery model.

## 📂 Repository Structure

```text
credit-risk-mvp-repo/
├── frontend/                  # Streamlit Application
│   ├── app.py                 # Main UI logic (Real-time inference)
│   ├── Dockerfile             # Container definition for Cloud Run
│   └── requirements.txt       # Python dependencies
├── infra/                     # Infrastructure as Code (IaC)
│   └── setup.sh               # MASTER SCRIPT: Provisions entire GCP environment
├── scripts/                   # Data Engineering Utility Scripts
│   └── generate_training_data.py  # Generates 5,000 synthetic records (Privacy compliant)
├── sql/                       # Database Schema & Model Definitions
│   └── schema.sql             # SQL for External Tables, Views, and BQML Model training
├── legacy_experiments/        # Proof-of-concept scripts (Batch API, etc.)
├── .gitignore                 # Git configuration
└── README.md                  # Project Documentation
🛠️ Architecture
Flow:

Data Generation: Python script generates synthetic PDF metadata (JSON) and historical credit CSVs, uploading them to GCS.

Training: BigQuery ingests the data and trains a Logistic Regression model (risk_score_model).

Inference: The Streamlit app sends applicant details + Customer ID to BigQuery.

Decision: BigQuery calculates the probability of default and returns a "Confidence Score" to the UI.

⚡ Quick Start
You can deploy this entire stack to a fresh Google Cloud Project in under 5 minutes using the automated setup script.

Prerequisites
A Google Cloud Platform Project.

Google Cloud Shell (recommended) or a local terminal with gcloud installed.

Deployment Steps
Clone the Repository

Bash

git clone [https://github.com/YOUR_USERNAME/credit-risk-mvp.git](https://github.com/YOUR_USERNAME/credit-risk-mvp.git)
cd credit-risk-mvp
Run the Setup Script

This script enables APIs, creates buckets/datasets, generates data, trains the model, and deploys the app.

Bash

cd infra
chmod +x setup.sh
./setup.sh [YOUR_PROJECT_ID] [REGION]

# Example:
# ./setup.sh my-risk-project-2025 us-central1
Access the App

Once the script finishes, it will output a Service URL (e.g., https://credit-risk-portal-xyz-uc.a.run.app).

Click the link to access the Risk Portal.

🧪 How to Use the App
Enter Applicant Data: The app pre-fills a sample Customer ID (12345-abc).

Analyze Risk: Click the 🚀 Analyze Risk button.

Interpret Results:

Green: Loan Approved (Low probability of default).

Red: Loan Denied (High probability of default).

Confidence Score: Shows the model's certainty (e.g., "94% Confidence").

Explainability: Checks the Debt-to-Income (DTI) ratio as a secondary "Rule of Thumb."

🔧 Technical Highlights
Synthetic Data Generator: To ensure data privacy and portability, this repo includes a script (scripts/generate_training_data.py) that "hydrates" the environment with 5,000 synthetic records on deployment. This avoids committing large/sensitive datasets to Git.

Dynamic Configuration: The application automatically detects the underlying GCP Project ID using environment variables, making the code 100% portable across environments (Dev/Test/Prod).

Serverless First: Uses Cloud Run and BigQuery to ensure costs scale to zero when not in use.

🔮 Future Roadmap (Production Readiness)
Vertex AI Feature Store: Replace direct BigQuery lookups with a low-latency online store (Redis/Bigtable) to serve features in <10ms.

CI/CD Pipeline: Implement Cloud Build triggers to automate deployment on Git push.

Drift Detection: Set up Vertex AI Model Monitoring to alert if incoming data diverges from training data.
