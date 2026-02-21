from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from data_models import (
    Patient, Medication, PatientCreate, MedicationCreate, PatientResponse, InteractionRequest, SessionResponse
)

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "json").lower()

if STORAGE_BACKEND == "dynamodb":
    from data_storage_dynamodb import (
        get_patient, get_all_patients, create_patient, update_patient,
        delete_patient, add_medication_to_patient, remove_medication_from_patient,
        update_medication, get_medications_for_patient, load_medications, save_session,
        load_session, load_sessions_for_patient, delete_sessions_for_patient
    )
else:
    from data_storage import (
        get_patient, get_all_patients, create_patient, update_patient,
        delete_patient, add_medication_to_patient, remove_medication_from_patient,
        update_medication, get_medications_for_patient, load_medications, save_session,
        load_session, load_sessions_for_patient, delete_sessions_for_patient
    )

app = FastAPI(title="Alexa Skill API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PATIENT MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Alexa Skill API is running"}

@app.get("/patients")
def list_patients():
    """Get all patients"""
    patients = get_all_patients()
    patient_list = []
    for p in patients:
        if hasattr(p, 'model_dump'):
            patient_dict = p.model_dump()
        else:
            patient_dict = p.__dict__ if hasattr(p, '__dict__') else p
        patient_list.append(patient_dict)
    return {"patients": patient_list}

@app.get("/patients/{patient_id}")
def get_patient_info(patient_id: str):
    """Get specific patient information"""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.post("/patients")
def create_new_patient(patient: PatientCreate):
    """Create a new patient (auto-generates ID)"""
    patient_dict = patient.dict() if hasattr(patient, 'dict') else vars(patient)
    patient_obj = Patient(**patient_dict)
    return create_patient(patient_obj)

@app.put("/patients/{patient_id}")
def update_patient_info(patient_id: str, patient: Patient):
    """Update patient information"""
    existing = get_patient(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.patient_id = patient_id
    return update_patient(patient_id, patient)

@app.delete("/patients/{patient_id}")
def delete_patient_endpoint(patient_id: str):
    """Delete a patient"""
    if not delete_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"message": "Patient deleted successfully"}

# ============================================================================
# MEDICATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/patients/{patient_id}/medications")
def add_medication(patient_id: str, medication: MedicationCreate):
    """Add a medication to a patient (auto-generates ID)"""
    med_dict = medication.dict() if hasattr(medication, 'dict') else vars(medication)
    med_obj = Medication(**med_dict)
    med = add_medication_to_patient(patient_id, med_obj)
    if not med:
        raise HTTPException(status_code=404, detail="Patient not found")
    return med

@app.put("/medications/{medication_id}")
def update_med(medication_id: str, medication: Medication):
    """Update a medication (name and dose only)"""
    updated = update_medication(medication_id, medication)
    if not updated:
        raise HTTPException(status_code=404, detail="Medication not found")
    return updated

@app.delete("/patients/{patient_id}/medications/{medication_id}")
def remove_medication(patient_id: str, medication_id: str):
    """Remove a medication from a patient"""
    success = remove_medication_from_patient(patient_id, medication_id)
    if not success:
        raise HTTPException(status_code=404, detail="Medication or patient not found")
    return {"message": "Medication removed successfully"}

@app.get("/medications")
def list_all_medications():
    """Get all medications (across all patients)"""
    medications = load_medications()
    med_list = [m for m in medications.values()]
    return {"medications": med_list}

@app.get("/patients/{patient_id}/medications")
def get_medications(patient_id: str):
    """Get all medications for a patient"""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    medications = get_medications_for_patient(patient_id)
    med_list = []
    for m in medications:
        if hasattr(m, 'model_dump'):
            med_list.append(m.model_dump())
        else:
            med_list.append(m.__dict__ if hasattr(m, '__dict__') else m)
    return {"patient_id": patient_id, "medications": med_list}

# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/sessions")
def save_session_data(session_data: dict):
    """Save a medication administration session (includes adherence info)"""
    if not session_data.get("patient_id"):
        raise HTTPException(status_code=400, detail="patient_id is required")
    
    patient = get_patient(session_data.get("patient_id"))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    session_id = session_data.get("session_id", f"{session_data.get('patient_id')}_{datetime.now().isoformat()}")
    save_session(session_id, session_data)
    return {"message": "Session saved successfully", "session_id": session_id}


@app.get("/sessions/{session_id}")
def get_session_data(session_id: str):
    """Get a specific saved session by session ID"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "session": session}


@app.get("/patients/{patient_id}/sessions")
def get_patient_sessions(patient_id: str):
    """Get all saved sessions for a patient"""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    sessions = load_sessions_for_patient(patient_id)
    session_list = []
    for sid, sdata in sessions.items():
        if isinstance(sdata, dict):
            session_item = {"session_id": sid}
            session_item.update(sdata)
            session_list.append(session_item)

    session_list.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"patient_id": patient_id, "sessions": session_list}


@app.delete("/patients/{patient_id}/sessions")
def delete_patient_sessions(patient_id: str):
    """Delete all saved sessions for a patient"""
    deleted_count = delete_sessions_for_patient(patient_id)
    return {
        "patient_id": patient_id,
        "deleted_sessions": deleted_count,
        "message": f"Deleted {deleted_count} session(s)"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
