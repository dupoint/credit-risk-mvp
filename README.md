<h1>🏦 CoreBanking Risk Engine (MVP)</h1>

<p>
  A real-time credit risk decision engine built on <strong>Google Cloud Platform</strong>.
</p>
<p>
  This project demonstrates a serverless, event-driven architecture that combines <strong>Historical Data</strong> (BigQuery) with <strong>Live Application Data</strong> (GCS) to execute sub-second loan approvals using in-database machine learning.
</p>

<p>
  <img src="https://img.shields.io/badge/Architecture-Serverless-blue" alt="Architecture Status">
  <img src="https://img.shields.io/badge/Status-Live-success" alt="Status">
</p>

<h2>🏗 High-Level Architecture</h2>

<p>
  The system follows a "Data Silo" pattern common in banking, separating the <strong>System of Record</strong> from the <strong>Ingestion Layer</strong>.
</p>

<pre>
graph TD
    User((Bank Manager)) -->|1. Selects App| UI[Frontend (Cloud Run)]
    
    subgraph "Data Silos"
        GCS[GCS Bucket 'Inbox'] -->|2. Ingest JSON| UI
        BQ[(BigQuery 'History')] -->|3. Fetch Profile| UI
    end
    
    UI -->|4. Request Decision| Model[BigQuery ML Model]
    Model -->|5. Return Score| UI
</pre>

<h3>Key Components</h3>
<ul>
  <li><strong>Frontend:</strong> Python (Flask) on <strong>Cloud Run</strong>. Acts as the orchestration layer.</li>
  <li><strong>Ingestion (The "Inbox"):</strong> <strong>Cloud Storage</strong> bucket acting as a digital inbox for incoming loan applications (JSON).</li>
  <li><strong>System of Record:</strong> <strong>BigQuery</strong> holding 5,000 historical customer profiles (Income, Credit Score, Employment History).</li>
  <li><strong>Decision Engine:</strong> <strong>BigQuery ML</strong> (Logistic Regression) performing inference <em>inside</em> the database to minimize latency.</li>
</ul>

<hr>

<h2>🚀 Quick Start (One-Click Deploy)</h2>

<p>
  This project is fully automated using Terraform and Shell scripting. It bootstraps the entire environment from scratch in ~4 minutes.
</p>

<p><strong>Prerequisites:</strong></p>
<ul>
  <li>Google Cloud Project (Fresh or Existing)</li>
  <li>Google Cloud Shell (Recommended)</li>
</ul>

<p><strong>Run the Deployment:</strong></p>
<pre><code>./deploy.sh [YOUR_PROJECT_ID]</code></pre>

<p><em>What this script does:</em></p>
<ol>
  <li><strong>Bootstraps APIs:</strong> Enables Compute, Run, Build, BQ, etc.</li>
  <li><strong>Provisions Infra:</strong> Uses Terraform to build the Bucket, Dataset, and IAM bindings.</li>
  <li><strong>Generates Data:</strong> Creates 5,000 historical records (with injected risk signals) and 100 incoming JSON applications.</li>
  <li><strong>Trains Model:</strong> SQL-based training on the historical dataset.</li>
  <li><strong>Deploys App:</strong> Builds and launches the Cloud Run container.</li>
</ol>

<hr>

<h2>🧪 Demo Scenarios (How to use)</h2>

<p>
  The application simulates a "Bank Manager" dashboard. Use the <strong>Digital Inbox</strong> dropdown to simulate processing incoming applications.
</p>

<h3>Scenario A: The "Happy Path" (Approval)</h3>
<ul>
  <li><strong>Action:</strong> Select a standard file (e.g., <code>applications/app_20.json</code>).</li>
  <li><strong>Observation:</strong>
    <ul>
      <li>The "JSON Preview" shows the raw application data.</li>
      <li>Click <strong>Process Application</strong>.</li>
      <li><strong>Result:</strong> <span style="color:green; font-weight:bold;">APPROVED ✅</span></li>
      <li><em>Why:</em> The user has High Income/High Credit Score in the Historical Data (BigQuery).</li>
    </ul>
  </li>
</ul>

<h3>Scenario B: The "High Risk" Applicant (Rejection)</h3>
<ul>
  <li><strong>Action:</strong> Select a file corresponding to a lower credit tier (randomly distributed).</li>
  <li><strong>Observation:</strong>
    <ul>
      <li>Click <strong>Process Application</strong>.</li>
      <li><strong>Result:</strong> <span style="color:red; font-weight:bold;">REJECTED 🛑</span></li>
      <li><em>Why:</em> The model detected risk factors (Low Score / High Debt-to-Income) based on the training data signals.</li>
    </ul>
  </li>
</ul>

<h3>Scenario C: The "Net-New" Customer (HITL Workflow)</h3>
<ul>
  <li><strong>Action:</strong> Select a file named <code>applications/NEW_USER_x.json</code>.</li>
  <li><strong>Observation:</strong>
    <ul>
      <li>Click <strong>Process Application</strong>.</li>
      <li><strong>Result:</strong> <span style="color:#d4a017; font-weight:bold;">⚠️ MANUAL REVIEW REQUIRED</span></li>
      <li><em>Why:</em> The system detected this ID does not exist in the Data Warehouse. Instead of "hallucinating" a score, it triggers a <strong>Human-in-the-Loop (HITL)</strong> exception for manual KYC.</li>
    </ul>
  </li>
</ul>

<hr>

<h2>🛡️ Engineering Decisions</h2>

<h3>1. Why BigQuery ML?</h3>
<p>
  Moving data out of a warehouse to an API endpoint (Vertex AI/SageMaker) introduces latency and security risks. By bringing the model <em>to the data</em>, we achieve scoring in milliseconds while keeping the data governance boundary intact.
</p>

<h3>2. Why the "Inbox" Pattern?</h3>
<p>
  Real-world banking is asynchronous. Applications arrive as documents (JSON/PDFs) in a landing zone (GCS). This architecture demonstrates how a modern app decouples <strong>Ingestion</strong> (GCS) from <strong>Decisioning</strong> (Compute).
</p>

<h3>3. Data Consistency</h3>
<p>
  The <code>generate_training_data.py</code> script ensures referential integrity. It generates the BigQuery History first, then samples valid IDs to create the JSON applications, ensuring 100% match rates for the "Happy Path" demo.
</p>

<hr>

<h2>📂 Project Structure</h2>

<ul>
  <li><code>frontend/</code>: Flask application & Dockerfile.</li>
  <li><code>infra/</code>: Terraform definitions for GCS, BigQuery, and IAM.</li>
  <li><code>scripts/</code>: Python data generators (uses <code>numpy</code> for signal injection).</li>
  <li><code>sql/</code>: Schema and Model training definitions.</li>
  <li><code>deploy.sh</code>: Master orchestration script.</li>
</ul>

## 📂 Repository Structure

```text
credit-risk-mvp-repo/
├── frontend/                  # Streamlit Application
│   ├── app.py                 # Main UI logic (Real-time inference)
│   ├── Dockerfile             # Container definition for Cloud Run
│   └── requirements.txt       # Python dependencies
├── infra/                     # Infrastructure as Code (IaC)
│   └── main.tf                # MASTER Terraform sciprt: Provisions entire GCP environment, API and permissions
├── scripts/                   # Data Engineering Utility Scripts
│   └── generate_training_data.py  # Generates 5,000 synthetic records (Privacy compliant) + 100 form application data (new + exisitng users)
├── sql/                       # Database Schema & Model Definitions
│   └── schema.sql             # SQL for External Tables, Views, and BQML Model training
├── legacy_experiments/        # Proof-of-concept scripts (Batch API, etc.)
├── .gitignore                 # Git configuration
└── README.md                  # Project Documentation
└── deploy.sh                  # One-click Deployment
