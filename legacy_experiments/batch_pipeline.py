import argparse
import logging
import re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.io import fileio
from google.cloud import documentai_v1 as documentai
from google.cloud import storage

# --- CONFIGURATION ---
PROJECT_ID = "credit-score-mvp" # REPLACE THIS
LOCATION = "us" # REPLACE THIS (Must match DocAI Processor location)
PROCESSOR_ID = "13eb63445cedb15d" # REPLACE THIS
BUCKET_NAME = "cc-mock-data-tk" # REPLACE THIS

class ProcessPdfFn(beam.DoFn):
    def setup(self):
        self.docai_client = documentai.DocumentProcessorServiceClient()
        self.storage_client = storage.Client()
        self.processor_name = self.docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    def process(self, file_path):
        try:
            parts = file_path.split("/")
            bucket_name = parts[2]
            blob_name = "/".join(parts[3:])
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            image_content = blob.download_as_bytes()

            raw_document = documentai.RawDocument(content=image_content, mime_type="application/pdf")
            request = documentai.ProcessRequest(name=self.processor_name, raw_document=raw_document)
            result = self.docai_client.process_document(request=request)
            text = result.document.text

            id_match = re.search(r"Applicant ID: ([a-zA-Z0-9\-]+)", text)
            inc_match = re.search(r"Declared Annual Income: \$([\d]+)", text)
            loan_match = re.search(r"Requested Loan Amount: \$([\d]+)", text)
            date_match = re.search(r"Application Date: ([\d\-]+)", text)

            yield {
                "customer_id": id_match.group(1) if id_match else None,
                "income": int(inc_match.group(1)) if inc_match else 0,
                "loan_amount": int(loan_match.group(1)) if loan_match else 0,
                "app_date": date_match.group(1) if date_match else None,
                "file_name": blob_name
            }
            
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

def run():
    parser = argparse.ArgumentParser()
    # Explicitly add these args so we can access them in the script
    parser.add_argument('--input_bucket', required=True)
    parser.add_argument('--temp_location', required=True) 
    
    known_args, pipeline_args = parser.parse_known_args()
    
    # Initialize PipelineOptions
    pipeline_options = PipelineOptions(pipeline_args)
    
    # FORCE Dataflow Runner settings explicitly
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = PROJECT_ID
    google_cloud_options.region = "us-central1"
    google_cloud_options.job_name = "pdf-batch-processing-fixed"
    google_cloud_options.temp_location = known_args.temp_location
    
    # We must explicitly set the setup file for workers to find dependencies
    pipeline_options.view_as(SetupOptions).setup_file = './setup.py'

    with beam.Pipeline(options=pipeline_options) as p:
        (
            p
            | 'Create Pattern' >> beam.Create([f"gs://{known_args.input_bucket}/application_forms/*.pdf"])
            | 'Match Files' >> fileio.MatchAll()
            | 'Get Paths' >> beam.Map(lambda x: x.path)
            | 'Process PDFs' >> beam.ParDo(ProcessPdfFn())
            | 'Write to BQ' >> beam.io.WriteToBigQuery(
                table=f"{PROJECT_ID}:credit_risk_mvp.loan_applications",
                schema="customer_id:STRING, income:INTEGER, loan_amount:INTEGER, app_date:DATE, file_name:STRING",
                # HERE IS THE FIX: Explicitly tell BQ where to put temp files
                custom_gcs_temp_location=known_args.temp_location, 
                method="FILE_LOADS",
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
