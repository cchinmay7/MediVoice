import json
import os
import tempfile
import shutil
from datetime import datetime
from typing import List, Optional, Dict
from data_models import Patient, Medication

DATA_DIR = "data"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.json")
MEDICATIONS_FILE = os.path.join(DATA_DIR, "medications.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def _ensure_file_exists(filepath, default_content):
    """Ensure JSON file exists with default content"""
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            json.dump(default_content, f, indent=2)

def _load_json_file(filepath, default_content):
    """Safely load JSON content, handling empty/corrupt files."""
    _ensure_file_exists(filepath, default_content)
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            if not content:
                return default_content.copy() if isinstance(default_content, dict) else default_content
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        with open(filepath, 'w') as f:
            json.dump(default_content, f, indent=2)
        return default_content.copy() if isinstance(default_content, dict) else default_content

def _get_next_patient_id() -> str:
    """Generate next patient ID (P001, P002, etc.)"""
    patients = load_patients()
    if not patients:
        return "P001"
    # Extract numeric parts from existing IDs
    nums = []
    for pid in patients.keys():
        if pid.startswith('P'):
            try:
                nums.append(int(pid[1:]))
            except ValueError:
                pass
    if nums:
        return f"P{max(nums) + 1:03d}"
    return "P001"

def _get_next_medication_id() -> str:
    """Generate next medication ID (MED001, MED002, etc.)"""
    medications = load_medications()
    if not medications:
        return "MED001"
    # Extract numeric parts from existing IDs
    nums = []
    for mid in medications.keys():
        if mid.startswith('MED'):
            try:
                nums.append(int(mid[3:]))
            except ValueError:
                pass
    if nums:
        return f"MED{max(nums) + 1:03d}"
    return "MED001"

# ============================================================================
# PATIENT FUNCTIONS
# ============================================================================

def load_patients() -> Dict[str, Patient]:
    """Load all patients from JSON"""
    data = _load_json_file(PATIENTS_FILE, {})
    return {pid: Patient(**pdata) for pid, pdata in data.items()}

def save_patients(patients: Dict[str, Patient]):
    """Save all patients to JSON (atomic write)"""
    try:
        data_to_save = {}
        for pid, p in patients.items():
            if hasattr(p, 'model_dump'):
                data_to_save[pid] = p.model_dump()
            else:
                data_to_save[pid] = p.__dict__ if hasattr(p, '__dict__') else p
        
        # Write to temp file first, then move (atomic operation)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=DATA_DIR, delete=False) as tmp:
            json.dump(data_to_save, tmp, indent=2)
            tmp_path = tmp.name
        
        # Move temp file to destination
        shutil.move(tmp_path, PATIENTS_FILE)
    except Exception as e:
        print(f"Error saving patients: {e}")
        raise

def get_patient(patient_id: str) -> Optional[Patient]:
    """Get a specific patient"""
    patients = load_patients()
    return patients.get(patient_id)

def create_patient(patient: Patient) -> Patient:
    """Create a new patient (auto-generates ID if not provided)"""
    patients = load_patients()
    # Auto-generate patient_id if not provided
    if not patient.patient_id:
        patient.patient_id = _get_next_patient_id()
    patient.created_at = datetime.now().isoformat()
    patient.updated_at = datetime.now().isoformat()
    patients[patient.patient_id] = patient
    save_patients(patients)
    return patient

def update_patient(patient_id: str, updated_patient: Patient) -> Optional[Patient]:
    """Update an existing patient"""
    patients = load_patients()
    if patient_id not in patients:
        return None
    updated_patient.updated_at = datetime.now().isoformat()
    patients[patient_id] = updated_patient
    save_patients(patients)
    return updated_patient

def delete_patient(patient_id: str) -> bool:
    """Delete a patient"""
    patients = load_patients()
    if patient_id not in patients:
        return False
    del patients[patient_id]
    save_patients(patients)
    # Also delete all medications for this patient
    delete_all_medications_for_patient(patient_id)
    delete_sessions_for_patient(patient_id)
    return True

def get_all_patients() -> List[Patient]:
    """Get all patients"""
    patients = load_patients()
    return list(patients.values())

# ============================================================================
# MEDICATION FUNCTIONS
# ============================================================================

def load_medications() -> Dict[str, Medication]:
    """Load all medications from JSON (keyed by medication_id)"""
    data = _load_json_file(MEDICATIONS_FILE, {})
    return {mid: Medication(**mdata) for mid, mdata in data.items()}

def save_medications(medications: Dict[str, Medication]):
    """Save all medications to JSON (atomic write)"""
    try:
        data_to_save = {}
        for mid, m in medications.items():
            if hasattr(m, 'model_dump'):
                data_to_save[mid] = m.model_dump()
            else:
                data_to_save[mid] = m.__dict__ if hasattr(m, '__dict__') else m
        
        # Write to temp file first, then move (atomic operation)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=DATA_DIR, delete=False) as tmp:
            json.dump(data_to_save, tmp, indent=2)
            tmp_path = tmp.name
        
        # Move temp file to destination
        shutil.move(tmp_path, MEDICATIONS_FILE)
    except Exception as e:
        print(f"Error saving medications: {e}")
        raise

def get_medications_for_patient(patient_id: str) -> List[Medication]:
    """Get all medications for a specific patient"""
    medications = load_medications()
    return [m for m in medications.values() if hasattr(m, 'patient_id') and m.patient_id == patient_id]

def add_medication_to_patient(patient_id: str, medication: Medication) -> Optional[Medication]:
    """Add a medication to a patient (auto-generates ID if not provided)"""
    # Verify patient exists
    if not get_patient(patient_id):
        return None
    
    medications = load_medications()
    # Auto-generate medication_id if not provided
    if not medication.medication_id:
        medication.medication_id = _get_next_medication_id()
    medication.patient_id = patient_id
    medications[medication.medication_id] = medication
    save_medications(medications)
    return medication

def remove_medication_from_patient(patient_id: str, medication_id: str) -> bool:
    """Remove a medication from a patient"""
    medications = load_medications()
    if medication_id not in medications:
        return False
    med = medications[medication_id]
    if not hasattr(med, 'patient_id') or med.patient_id != patient_id:
        return False
    del medications[medication_id]
    save_medications(medications)
    return True

def update_medication(medication_id: str, updated_medication: Medication) -> Optional[Medication]:
    """Update a medication (name and dose only, patient_id cannot be changed)"""
    medications = load_medications()
    if medication_id not in medications:
        return None
    
    existing = medications[medication_id]
    # Only allow updating name and dose, keep existing patient_id and medication_id
    existing.name = updated_medication.name
    existing.dose = updated_medication.dose
    medications[medication_id] = existing
    save_medications(medications)
    return existing

def delete_all_medications_for_patient(patient_id: str):
    """Delete all medications for a patient"""
    medications = load_medications()
    meds_to_delete = [mid for mid, m in medications.items() 
                      if hasattr(m, 'patient_id') and m.patient_id == patient_id]
    for mid in meds_to_delete:
        del medications[mid]
    save_medications(medications)

# ============================================================================
# SESSION FUNCTIONS
# ============================================================================

def save_session(session_id: str, session_data: dict):
    """Save a session (atomic write)"""
    try:
        sessions = _load_json_file(SESSIONS_FILE, {})
        sessions[session_id] = session_data
        
        # Write to temp file first, then move
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=DATA_DIR, delete=False) as tmp:
            json.dump(sessions, tmp, indent=2)
            tmp_path = tmp.name
        
        shutil.move(tmp_path, SESSIONS_FILE)
    except Exception as e:
        print(f"Error saving session: {e}")
        raise

def load_session(session_id: str) -> Optional[dict]:
    """Load a session"""
    sessions = _load_json_file(SESSIONS_FILE, {})
    return sessions.get(session_id)

def load_all_sessions() -> Dict[str, dict]:
    """Load all sessions."""
    return _load_json_file(SESSIONS_FILE, {})

def load_sessions_for_patient(patient_id: str) -> Dict[str, dict]:
    """Load all sessions for a specific patient."""
    sessions = load_all_sessions()
    return {
        sid: sdata for sid, sdata in sessions.items()
        if isinstance(sdata, dict) and sdata.get("patient_id") == patient_id
    }


def delete_sessions_for_patient(patient_id: str) -> int:
    """Delete all sessions for a specific patient and return deleted count."""
    try:
        sessions = load_all_sessions()
        filtered_sessions = {
            sid: sdata
            for sid, sdata in sessions.items()
            if not (isinstance(sdata, dict) and sdata.get("patient_id") == patient_id)
        }
        deleted_count = len(sessions) - len(filtered_sessions)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=DATA_DIR, delete=False) as tmp:
            json.dump(filtered_sessions, tmp, indent=2)
            tmp_path = tmp.name

        shutil.move(tmp_path, SESSIONS_FILE)
        return deleted_count
    except Exception as e:
        print(f"Error deleting sessions for patient {patient_id}: {e}")
        raise



