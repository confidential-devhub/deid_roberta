import csv
import random
import json
from faker import Faker
from datetime import datetime, timedelta

# Initialize Faker
fake = Faker('en_US')

# Configuration
OUTPUT_FILE = "synthetic_clinical_notes.csv"
NUM_RECORDS = 100

# The obi/deid_roberta_i2b2 model detects these specific categories.
# We will generate data specifically to trigger these.
# Categories: NAME, PROFESSION, LOCATION, AGE, DATE, CONTACT, ID

def generate_note():
    """
    Generates a single synthetic clinical note and tracks the injected PII.
    Returns: (text, entities_dict)
    """

    # 1. Generate Synthetic Entities
    gender = random.choice(['M', 'F'])
    first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
    last_name = fake.last_name()
    patient_name = f"{first_name} {last_name}"

    doctor_name = f"Dr. {fake.first_name()} {fake.last_name()}"
    hospital = f"{fake.city()} {random.choice(['General', 'Memorial', 'Community'])} Hospital"

    # Dates
    admit_date = fake.date_between(start_date='-2y', end_date='-1y')
    discharge_date = admit_date + timedelta(days=random.randint(1, 14))
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90)

    # IDs and Contacts
    mrn = fake.random_number(digits=7)
    ssn = fake.ssn()
    phone = fake.phone_number()
    email = f"{first_name[0].lower()}{last_name.lower()}@{fake.free_email_domain()}"

    # Demographics
    age = (datetime.now().date() - dob).days // 365
    profession = fake.job()
    street = fake.street_address()
    city = fake.city()
    state = fake.state()
    zip_code = fake.zipcode()

    # 2. Select a Random Template
    # We use multiple templates to ensure variety in the dataset
    templates = [
        (
            f"ADMISSION NOTE\n"
            f"Patient: {patient_name}\n"
            f"MRN: {mrn}\n"
            f"DOB: {dob.strftime('%m/%d/%Y')} (Age: {age})\n"
            f"Date of Admission: {admit_date.strftime('%Y-%m-%d')}\n"
            f"Physician: {doctor_name}\n"
            f"Hospital: {hospital}\n\n"
            f"History of Present Illness:\n"
            f"Mr./Ms. {last_name} is a {age}-year-old {profession} who presents with chest pain. "
            f"Patient lives at {street}, {city}, {state} {zip_code}. "
            f"Can be reached at {phone} or {email}.\n"
        ),
        (
            f"DISCHARGE SUMMARY\n"
            f"Name: {patient_name}\n"
            f"Unit No: {mrn}\n"
            f"Admission Date: {admit_date.strftime('%m/%d/%Y')}\n"
            f"Discharge Date: {discharge_date.strftime('%m/%d/%Y')}\n\n"
            f"Social History: Patient works as a {profession}. "
            f"Lives with spouse in {city}. "
            f"Contact number: {phone}. Emergency contact: {fake.name()} (Relationship: Spouse).\n"
            f"Follow up with {doctor_name} at {hospital} in 2 weeks.\n"
        ),
        (
            f"CLINICAL NOTE\n"
            f"ID: {ssn}\n"
            f"Date: {datetime.now().strftime('%B %d, %Y')}\n"
            f"Location: {hospital}, {city} Branch\n"
            f"Provider: {doctor_name}\n\n"
            f"Symptoms: Patient {patient_name} complains of headache. "
            f"States they have been under stress at work ({profession}).\n"
            f"Observations: BP 120/80. Pulse 72.\n"
            f"Assessment: Tension headache.\n"
            f"Plan: Rest, ibuprofen. Call {phone} if symptoms persist.\n"
        )
    ]

    note_text = random.choice(templates)

    # 3. Track Ground Truth (What entities are present?)
    # This dictionary helps you verify if the model actually caught them.
    ground_truth = {
        "PATIENT": patient_name,
        "DOCTOR": doctor_name,
        "HOSPITAL": hospital,
        "DATE": [admit_date.strftime('%Y-%m-%d'), dob.strftime('%m/%d/%Y')],
        "ID": [str(mrn), ssn],
        "PHONE": phone,
        "PROFESSION": profession,
        "LOCATION": [street, city, state, zip_code],
        "AGE": str(age)
    }

    return note_text, ground_truth

def main():
    print(f"Generating {NUM_RECORDS} synthetic records...")

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        # We save 'text' for input and 'ground_truth' for validation
        # fieldnames = ['text', 'ground_truth_json']
        fieldnames = ['text']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(NUM_RECORDS):
            text, entities = generate_note()
            writer.writerow({
                'text': text,
                # 'ground_truth_json': json.dumps(entities)
            })

            if (i + 1) % 10 == 0:
                print(f"Generated {i + 1} records...")

    print(f"Done! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()