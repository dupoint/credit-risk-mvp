import json
import random
import uuid
from google.cloud import storage

# CONFIG
NUM_RECORDS = 5000

def generate_record():
    """Creates a synthetic DocAI JSON output and matching CSV history logic"""
    customer_id = str(uuid.uuid4())[:8]
    
    # 1. Generate Random 'Application' Data (The JSON part)
    income = random.randint(30000, 150000)
    loan_amount = random.randint(5000, 50000)
    
    # 2. Generate 'History' Data (The CSV logic)
    # We rig the logic so the model can actually learn something (Pattern Injection)
    # Rule: High Debt + Low Credit Score = BAD
    credit_score = random.randint(300, 850)
    existing_debt = random.randint(0, 50000)
    
    # Simulate the "text" field that DocAI would output
    docai_text = f"""
    Applicant ID: {customer_id}
    Declared Annual Income: ${income}
    Requested Loan Amount: ${loan_amount}
    Application Date: 2025-01-01
    """
    
    json_payload = {
        "text": docai_text,
        "confidence": round(random.uniform(0.8, 0.99), 2)
    }

    # Return tuple of (JSON filename, JSON content, CSV row)
    return (
        f"{customer_id}.json", 
        json.dumps(json_payload), 
        f"{customer_id},{credit_score},{random.randint(0,5)},{existing_debt}"
    )

def upload_and_save(bucket_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    print(f"🚀 Generating {NUM_RECORDS} synthetic records...")
    
    csv_rows = ["customer_id,credit_score,missed_payments_last_12m,existing_debt"]
    
    # In a real script, we'd use threading/multiprocessing for speed
    # For demo, we just loop
    for i in range(NUM_RECORDS):
        fname, json_content, csv_row = generate_record()
        
        # Upload JSON (Simulating DocAI Output)
        blob = bucket.blob(f"batch_results/{fname}")
        blob.upload_from_string(json_content, content_type='application/json')
        
        csv_rows.append(csv_row)
        
        if i % 100 == 0:
            print(f"   ... {i} records created")

    # Upload the Matching CSV (Simulating the Database Dump)
    csv_content = "\n".join(csv_rows)
    blob_csv = bucket.blob("credit_history.csv")
    blob_csv.upload_from_string(csv_content, content_type='text/csv')
    
    print("✅ Data Generation Complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        upload_and_save(sys.argv[1])
    else:
        print("Please provide a bucket name.")