import pandas as pd
import random
import io
from faker import Faker
from fpdf import FPDF
from google.cloud import storage

# --- CONFIGURATION ---
PROJECT_ID = "credit-score-mvp"  # Replace with your Project ID
BUCKET_NAME = "cc-mock-data-tk" # Replace with your Bucket Name
NUM_RECORDS = 5000  # Start small (e.g., 100) to test, then ramp to 5000

# Initialize Clients
fake = Faker()
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

print(f"🚀 Starting generation of {NUM_RECORDS} records directly to GCS...")

# --- STEP 1: Generate Structured Data (CSV) ---
data = []
for _ in range(NUM_RECORDS):
    data.append({
        "customer_id": fake.uuid4(),
        "credit_score": random.randint(300, 850),
        "missed_payments_last_12m": random.choices([0, 1, 2, 5], weights=[70, 20, 5, 5])[0],
        "existing_debt": random.randint(0, 50000)
    })

df = pd.DataFrame(data)

# Upload CSV directly to Bucket (no local file)
csv_blob = bucket.blob("structured_data/credit_history.csv")
csv_blob.upload_from_string(df.to_csv(index=False), content_type='text/csv')
print("✅ credit_history.csv uploaded to GCS.")

# --- STEP 2: Generate Unstructured Data (PDFs) ---
# We define a custom class to suppress FPDF output to console/files
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page %s' % self.page_no(), 0, 0, 'C')

print("Generating PDFs... (This takes a moment)")

for index, row in df.iterrows():
    customer_id = row['customer_id']
    
    # Generate random income/loan for the "Application"
    income = random.randint(30000, 150000)
    loan_amount = random.randint(5000, 50000)
    
    # Create PDF in Memory
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="CREDIT CORP LOAN APPLICATION", ln=1, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Applicant ID: {customer_id}", ln=1)
    pdf.cell(200, 10, txt=f"Declared Annual Income: ${income}", ln=1)
    pdf.cell(200, 10, txt=f"Requested Loan Amount: ${loan_amount}", ln=1)
    pdf.cell(200, 10, txt=f"Application Date: {fake.date_this_year()}", ln=1)
    
    # Output PDF to a byte string (RAM) instead of disk
    # FPDF's output(dest='S') returns a string, we encode to bytes
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    # Upload to GCS
    blob = bucket.blob(f"application_forms/{customer_id}.pdf")
    blob.upload_from_string(pdf_bytes, content_type='application/pdf')
    
    if index % 100 == 0:
        print(f"   Processed {index} documents...")

print("🎉 DONE! All data is now in your GCP Bucket.")
