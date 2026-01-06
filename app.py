from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import re
import os
import tempfile
from datetime import datetime
from azure.storage.blob import BlobServiceClient

class TextInput(BaseModel):
    text: str

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def load_model():
    global nlp
    model_dir = "/app/hf_cache"
    model_name = "obi/deid_roberta_i2b2"

    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_name, cache_dir=model_dir)

    nlp = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple"
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/redact")
def redact(input_data: TextInput):
    entities = nlp(input_data.text)
    entities.sort(key=lambda x: x['start'], reverse=True)
    redacted = input_data.text
    for e in entities:
        redacted = redacted[:e['start']] + f"[{e['entity_group']}]" + redacted[e['end']:]
    return {"redacted": redacted}

@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    """Display the hospital patient form"""
    return templates.TemplateResponse("form.html", {"request": request})

def format_clinical_note(date: str, patient_name: str, email: str, ssn: str,
                        address: str, department: str, symptoms: str,
                        cause: str, therapy: str) -> str:
    """Format form data into a clinical note text"""
    note = f"""PATIENT INFORMATION
Date: {date}
Patient Name: {patient_name}
Email: {email}
Social Security Number: {ssn}
Address: {address}

HOSPITAL INFORMATION
Hospital Department: {department}

CLINICAL INFORMATION
Symptoms: {symptoms}
Cause: {cause}
Therapy: {therapy}
"""
    return note

def anonymize_text(text: str) -> str:
    """Anonymize text using the deid_roberta_i2b2 model"""
    entities = nlp(text)
    entities.sort(key=lambda x: x['start'], reverse=True)
    redacted = text
    for e in entities:
        redacted = redacted[:e['start']] + f"[{e['entity_group']}]" + redacted[e['end']:]
    return redacted

def parse_anonymized_note(anonymized_text: str) -> dict:
    """Parse anonymized clinical note back into structured data"""
    data = {}

    # Extract date
    date_match = re.search(r'Date:\s*(.+?)\n', anonymized_text)
    data['date'] = date_match.group(1).strip() if date_match else ""

    # Extract patient name
    name_match = re.search(r'Patient Name:\s*(.+?)\n', anonymized_text)
    data['patient_name'] = name_match.group(1).strip() if name_match else ""

    # Extract email
    email_match = re.search(r'Email:\s*(.+?)\n', anonymized_text)
    data['email'] = email_match.group(1).strip() if email_match else ""

    # Extract SSN
    ssn_match = re.search(r'Social Security Number:\s*(.+?)\n', anonymized_text)
    data['ssn'] = ssn_match.group(1).strip() if ssn_match else ""

    # Extract address
    address_match = re.search(r'Address:\s*(.+?)\n', anonymized_text)
    data['address'] = address_match.group(1).strip() if address_match else ""

    # Extract department
    dept_match = re.search(r'Hospital Department:\s*(.+?)\n', anonymized_text)
    data['department'] = dept_match.group(1).strip() if dept_match else ""

    # Extract symptoms
    symptoms_match = re.search(r'Symptoms:\s*(.+?)\nCause:', anonymized_text, re.DOTALL)
    data['symptoms'] = symptoms_match.group(1).strip() if symptoms_match else ""

    # Extract cause
    cause_match = re.search(r'Cause:\s*(.+?)\nTherapy:', anonymized_text, re.DOTALL)
    data['cause'] = cause_match.group(1).strip() if cause_match else ""

    # Extract therapy
    therapy_match = re.search(r'Therapy:\s*(.+?)$', anonymized_text, re.DOTALL)
    data['therapy'] = therapy_match.group(1).strip() if therapy_match else ""

    return data

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    date: str = Form(...),
    patient_name: str = Form(...),
    email: str = Form(...),
    ssn: str = Form(...),
    address: str = Form(...),
    department: str = Form(...),
    symptoms: str = Form(...),
    cause: str = Form(...),
    therapy: str = Form(...)
):
    """Handle form submission, anonymize data, and display result"""
    # Format the form data into a clinical note
    clinical_note = format_clinical_note(
        date, patient_name, email, ssn, address,
        department, symptoms, cause, therapy
    )

    # Anonymize the clinical note
    anonymized_note = anonymize_text(clinical_note)

    # Parse the anonymized note back into structured data
    anonymized_data = parse_anonymized_note(anonymized_note)

    # Add the full anonymized note text as clinical_note for display
    anonymized_data['clinical_note'] = anonymized_note

    # Render the result template with anonymized data
    return templates.TemplateResponse("result.html", {
        "request": request,
        **anonymized_data
    })

@app.post("/send", response_class=HTMLResponse)
async def send_to_azure(
    request: Request,
    clinical_note: str = Form(...)
):
    """Save edited anonymized data to file and upload to Azure Blob Storage"""
    try:
        # Get Azure connection string from environment variable
        azure_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not azure_connection_string:
            return templates.TemplateResponse("result.html", {
                "request": request,
                "error": "Azure connection string not configured",
                "clinical_note": clinical_note
            })

        # Create a temporary file with the clinical note
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"medical_record_{timestamp}.txt"

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='medical_record_') as tmp_file:
            tmp_file.write(clinical_note)
            tmp_file_path = tmp_file.name

        try:
            # Initialize Azure Blob Service Client
            blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)

            # Get container name from environment variable (default to 'medical-records')
            container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "medical-records")

            # Get or create container
            try:
                container_client = blob_service_client.get_container_client(container_name)
                container_client.get_container_properties()
            except Exception:
                # Container doesn't exist, create it
                container_client = blob_service_client.create_container(container_name)

            # Upload the file to Azure Blob Storage
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=filename
            )

            with open(tmp_file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)

            # Clean up temporary file
            os.unlink(tmp_file_path)

            # Return success message with the clinical note
            return templates.TemplateResponse("result.html", {
                "request": request,
                "clinical_note": clinical_note,
                "success_message": f"Successfully uploaded to Azure Blob Storage as {filename}"
            })

        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            raise e

    except Exception as e:
        # Return error message with the clinical note so user can try again
        return templates.TemplateResponse("result.html", {
            "request": request,
            "clinical_note": clinical_note,
            "error": f"Error uploading to Azure: {str(e)}"
        })
