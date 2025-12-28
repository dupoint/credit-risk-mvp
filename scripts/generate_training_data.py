import sys
import os
import json
import random
import pandas as pd
import numpy as np
from faker import Faker
from concurrent.futures import ThreadPoolExecutor

# Usage: python3 generate_training_data.py [BUCKET_NAME]
if len(sys.argv) < 2:
    print("❌ Error: Bucket name required.")
    sys.exit(1)

BUCKET_NAME = sys.argv[1]
fake = Faker()

# Configuration
NUM_HISTORY_RECORDS = 5000  # For Model Training (CSV)
NUM_NEW_APPLICATIONS = 100  # For Pipeline Demo (JSON) 
# Note: We limit JSONs to 100 for speed. Generating/Uploading 5,000 small files 
# takes 10+ mins in Cloud Shell. 100 is enough to show the "flow".

print(f"🎲 Step 1: Generating {NUM_HISTORY_RECORDS} Historical Records (CSV)...")

# --- SHARED DATA LOGIC ---
def generate_record(record_id=None):
    if not record_id:
        record_id = fake.uuid4()
        
    # Realistic distributions
    income = np.random.randint(20000, 150000)
    loan_amount = np.random.randint(1000, 50000)
    credit_score = np.random.randint(300, 850)
    dti = np.round(np.random.uniform(0.1, 0.9), 2)
    
    # Calculate Risk (The "Truth")
    score = 0
    if credit_score < 600: score += 5
    if dti > 0.5: score += 3
    if income < 30000: score += 2
    if loan_amount > (income * 0.6): score += 3
    
    is_default = 1 if score >= 5 else 0

    return {
        'customer_id': record_id,
        'age': np.random.randint(18, 70),
        'income': income,
        'loan_amount': loan_amount,
        'credit_score': credit_score,
        'months_employed': np.random.randint(0, 120),
        'num_credit_lines': np.random.randint(0, 12),
        'interest_rate': np.round(np.random.uniform(2.5, 25.0), 2),
        'dti_ratio': dti,
        'default_risk': is_default
    }

# --- PART A: CSV GENERATION (History) ---
history_data = [generate_record() for _ in range(NUM_HISTORY_RECORDS)]
df = pd.DataFrame(history_data)
df.to_csv('credit_history.csv', index=False)
print(f"   ✅ History CSV saved locally.")

# --- PART B: JSON GENERATION (New Applications) ---
print(f"🎲 Step 2: Generating {NUM_NEW_APPLICATIONS} 'New Application' JSONs...")
os.makedirs('batch_results', exist_ok=True)

def create_json_file(i):
    rec = generate_record()
    # Simulate Document AI structure
    doc_ai_output = {
        "text": f"Applicant ID: {rec['customer_id']}\nDeclared Annual Income: ${rec['income']}\nRequested Loan Amount: ${rec['loan_amount']}\nApplication Date: 2025-01-15",
        "confidence": round(random.uniform(0.85, 0.99), 4),
        "entities": rec # We embed the raw data for easier parsing in demo
    }
    fname = f"batch_results/app_{rec['customer_id']}.json"
    with open(fname, 'w') as f:
        json.dump(doc_ai_output, f)

# Generate JSONs locally
for i in range(NUM_NEW_APPLICATIONS):
    create_json_file(i)
print(f"   ✅ JSONs generated locally.")

# --- PART C: UPLOAD ---
print("🚀 Step 3: Uploading to Cloud Storage...")

# 1. Upload CSV
os.system(f"gsutil cp credit_history.csv gs://{BUCKET_NAME}/credit_history.csv")

# 2. Upload JSONs (Using -m for parallel upload because files are small)
# This prevents the script from hanging for 10 minutes
os.system(f"gsutil -m cp -r batch_results gs://{BUCKET_NAME}/")

print(f"✅ Data Generation Complete. Assets in gs://{BUCKET_NAME}")
