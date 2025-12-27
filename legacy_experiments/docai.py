import re
from google.cloud import storage
from google.cloud import documentai_v1 as documentai
from google.cloud import bigquery

# --- CONFIGURATION ---
PROJECT_ID = "credit-score-mvp"
LOCATION = "us" # or "us-central1" (Must match your Processor location)
PROCESSOR_ID ="13eb63445cedb15d" # Get this from DocAI Console
GCS_BUCKET_NAME = "cc-mock-data-tk"
BQ_DATASET = "credit_risk_mvp"
BQ_TABLE = "loan_applications"

# Initialize Clients
storage_client = storage.Client(project=PROJECT_ID)
bq_client = bigquery.Client(project=PROJECT_ID)
docai_client = documentai.DocumentProcessorServiceClient()

# Full Processor Name
processor_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

def process_pdf(blob):
    """
    Reads a PDF from GCS, sends to DocAI, extracts fields via Regex 
    (since our layout is simple text), and returns a row for BQ.
    """
    
    # 1. Download PDF bytes from GCS
    image_content = blob.download_as_bytes()
    
    # 2. Configure the DocAI Request
    raw_document = documentai.RawDocument(content=image_content, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
    
    # 3. Call the API (The "Magic" Step)
    result = docai_client.process_document(request=request)
    document = result.document
    text = document.text
    
    # 4. Extract Data (Using Regex for 100% reliability on our fake forms)
    # In a real "Form Parser", you would loop through document.pages.form_fields
    # But for this MVP, regex is faster and cheaper to debug.
    
    try:
        # Find ID
        id_match = re.search(r"Applicant ID: ([a-zA-Z0-9\-]+)", text)
        customer_id = id_match.group(1) if id_match else None
        
        # Find Income (Remove '$' and whitespace)
        inc_match = re.search(r"Declared Annual Income: \$([\d]+)", text)
        income = int(inc_match.group(1)) if inc_match else 0
        
        # Find Loan Amount
        loan_match = re.search(r"Requested Loan Amount: \$([\d]+)", text)
        loan_amount = int(loan_match.group(1)) if loan_match else 0
        
        # Find Date
        date_match = re.search(r"Application Date: ([\d\-]+)", text)
        app_date = date_match.group(1) if date_match else None
        
        return {
            "customer_id": customer_id,
            "income": income,
            "loan_amount": loan_amount,
            "app_date": app_date
        }
        
    except Exception as e:
        print(f"Error parsing {blob.name}: {e}")
        return None

# --- MAIN EXECUTION ---

print("🚀 Starting Batch Processing...")

bucket = storage_client.bucket(GCS_BUCKET_NAME)
blobs = list(bucket.list_blobs(prefix="application_forms/"))

rows_to_insert = []
batch_size = 50 # Write to BQ in chunks to be efficient

for i, blob in enumerate(blobs):
    # Skip folders
    if blob.name.endswith("/"):
        continue
        
    print(f"Processing {blob.name}...")
    
    row = process_pdf(blob)
    if row:
        rows_to_insert.append(row)
    
    # Flush to BigQuery every 50 records
    if len(rows_to_insert) >= batch_size:
        errors = bq_client.insert_rows_json(f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}", rows_to_insert)
        if errors:
            print(f"❌ Encounted errors inserting rows: {errors}")
        else:
            print(f"✅ Batch {i} inserted into BigQuery.")
        rows_to_insert = [] # Reset batch

# Insert remaining rows
if rows_to_insert:
    bq_client.insert_rows_json(f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}", rows_to_insert)
    print("✅ Final batch inserted.")

print("🎉 PIPELINE COMPLETE: PDFs are now structured data in BigQuery.")
