from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo


EST_TIMEZONE = ZoneInfo("America/New_York")

class Medication(BaseModel):
    medication_id: Optional[str] = None  # Auto-generated if not provided
    patient_id: Optional[str] = None  # FK to patient_table
    name: str
    dose: str  # e.g., "20 mg"
    frequency: str = "once"  # e.g., "once", "twice", "thrice"

class MedicationCreate(BaseModel):
    """Model for creating new medications (without ID)"""
    name: str
    dose: str
    frequency: str = "once"

class Patient(BaseModel):
    patient_id: Optional[str] = None  # Auto-generated if not provided
    first_name: str
    last_name: str
    pairing_code: str
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(EST_TIMEZONE).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(EST_TIMEZONE).isoformat())

class PatientCreate(BaseModel):
    """Model for creating new patients (without ID)"""
    first_name: str
    last_name: str
    pairing_code: str
    is_active: bool = True

class PatientResponse(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    pairing_code: str
    is_active: bool

class SessionResponse(BaseModel):
    session_id: str
    patient_id: str
    current_step: str
    responses: dict
    timestamp: str

class InteractionRequest(BaseModel):
    patient_id: str
    user_input: str
    session_id: Optional[str] = None
