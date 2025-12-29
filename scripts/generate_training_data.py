import pandas as pd
import numpy as np
import uuid
import random
import json
import sys
from google.cloud import storage

def generate_data(bucket_name):
    print(f"🚀 Initializing Data Generator for bucket: {bucket_name}")
    
    # 1. GENERATE HISTORY (With Signal)
    NUM_CUSTOMERS = 5000
    print(f"   - Generating {NUM_CUSTOMERS} historical customer profiles...")
    
    np.random.seed(42)
    fake_ids = [str(uuid.uuid4()) for _ in range(NUM_CUSTOMERS)]
    
    # Generate Features first
    age = np.random.randint(18, 70, NUM_CUSTOMERS)
    income = np.random.normal(70000, 25000, NUM_CUSTOMERS).astype(int)
    credit_score = np.random.randint(300, 850, NUM_CUSTOMERS)
    months_employed = np.random.randint(0, 120, NUM_CUSTOMERS)
    num_credit_lines = np.random.randint(0, 15, NUM_CUSTOMERS)
    interest_rate = np.round(np.random.uniform(3.5, 25.0, NUM_CUSTOMERS), 2)
    dti_ratio = np.round(np.random.uniform(0.1, 0.9, NUM_CUSTOMERS), 2)
    loan_amount = np.random.randint(5000, 50000, NUM_CUSTOMERS)
    
    # --- SYNTHETIC LOGIC: INJECT SIGNAL ---
    # Start with base probability of default (10%)
    risk_prob = np.full(NUM_CUSTOMERS, 0.10)
    
    # Penalize Low Credit Score (Major Factor)
    risk_prob += np.where(credit_score < 500, 0.6, 0.0)    # +60% risk if score < 500
    risk_prob += np.where(credit_score < 650, 0.2, 0.0)    # +20% risk if score < 650
    
    # Penalize Low Income
    risk_prob += np.where(income < 30000, 0.3, 0.0)        # +30% risk if income < 30k
    
    # Penalize High DTI (Debt to Income)
    risk_prob += np.where(dti_ratio > 0.6, 0.2, 0.0)       # +20% risk if DTI > 60%
    
    # Reward High Stability (Employment)
    risk_prob -= np.where(months_employed > 24, 0.05, 0.0) # -5% risk if employed > 2 years
    
    # Cap probabilities between 0 and 1
    risk_prob = np.clip(risk_prob, 0.0, 1.0)
    
    # Generate Target based on weighted probability
    default_risk = np.random.binomial(1, risk_prob)
    # --------------------------------------

    df = pd.DataFrame({
        'customer_id': fake_ids,
        'age': age,
        'income': income,
        'credit_score': credit_score,
        'months_employed': months_employed,
        'num_credit_lines': num_credit_lines,
        'interest_rate': interest_rate,
        'dti_ratio': dti_ratio,
        'loan_amount': loan_amount,
        'default_risk': default_risk
    })
    
    csv_filename = 'credit_history.csv'
    df.to_csv(csv_filename, index=False)
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(csv_filename)
    blob.upload_from_filename(csv_filename)
    print(f"   - Uploaded {csv_filename} to GCS (Signal Injected).")

    # 2. GENERATE INBOX APPLICATIONS (90 Existing + 10 Net New)
    NUM_JSON_APPS = 100
    print(f"   - Generating {NUM_JSON_APPS} applications (90% Existing, 10% Net New)...")
    
    existing_pool = random.sample(fake_ids, 90)
    new_pool = [str(uuid.uuid4()) for _ in range(10)]
    mixed_pool = existing_pool + new_pool
    random.shuffle(mixed_pool)
    
    for i, cust_id in enumerate(mixed_pool):
        is_new = cust_id in new_pool
        prefix = "NEW_USER" if is_new else "app"
        
        app_data = {
            "application_id": str(uuid.uuid4()),
            "customer_id": cust_id,
            "timestamp": "2025-12-29T10:00:00Z",
            "loan_amount": random.randint(5000, 50000),
            "loan_purpose": random.choice(["home_improvement", "debt_consolidation", "auto"])
        }
        
        blob_name = f"applications/{prefix}_{i}.json"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(app_data), content_type='application/json')
        
    print("✅ Data Generation Complete: Signal Injected & Inbox Synced.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_training_data.py [BUCKET_NAME]")
        sys.exit(1)
    generate_data(sys.argv[1])