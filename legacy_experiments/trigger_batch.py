import re
from google.cloud import documentai_v1 as documentai
from google.cloud import storage

# --- CONFIGURATION ---
PROJECT_ID = "credit-score-mvp" # REPLACE THIS
LOCATION = "us" # REPLACE THIS (Must match DocAI Processor location)
PROCESSOR_ID = "13eb63445cedb15d" # REPLACE THIS
GCS_INPUT_URI = "gs://cc-mock-data-tk/application_forms/" # Where PDFs live
GCS_OUTPUT_URI = "gs://cc-mock-data-tk/batch_results/"    # Where JSONs go

def batch_process_documents(
    project_id,
    location,
    processor_id,
    gcs_input_uri,
    gcs_output_uri,
):
    opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor
    name = client.processor_path(project_id, location, processor_id)

    # 1. Define Input (Point to the whole GCS Prefix)
    gcs_documents = documentai.GcsPrefix(gcs_uri_prefix=gcs_input_uri)
    input_config = documentai.BatchDocumentsInputConfig(gcs_prefix=gcs_documents)

    # 2. Define Output (Where to dump the JSONs)
    gcs_output_config = documentai.DocumentOutputConfig(
        gcs_output_config={"gcs_uri": gcs_output_uri}
    )

    # 3. Create the Request
    request = documentai.BatchProcessRequest(
        name=name,
        input_documents=input_config,
        document_output_config=gcs_output_config,
    )

    # 4. Fire and Forget (Long Running Operation)
    print(f"🚀 Triggering Batch Job for {gcs_input_uri}...")
    operation = client.batch_process_documents(request=request)

    print(f"✅ Operation Started: {operation.operation.name}")
    print("   You can stop this script now. The job runs on Google's servers.")
    print("   Check the 'batch_results' bucket in 10-20 minutes.")
    
    # Optional: Wait for result (Block terminal)
    # print("Waiting for operation to complete...")
    # operation.result()

if __name__ == "__main__":
    batch_process_documents(
        PROJECT_ID,
        LOCATION,
        PROCESSOR_ID,
        GCS_INPUT_URI,
        GCS_OUTPUT_URI
    )
