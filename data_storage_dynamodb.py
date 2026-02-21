import os
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from data_models import Patient, Medication


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
PATIENTS_TABLE_NAME = os.getenv("PATIENTS_TABLE", "patients")
MEDICATIONS_TABLE_NAME = os.getenv("MEDICATIONS_TABLE", "medications")
SESSIONS_TABLE_NAME = os.getenv("SESSIONS_TABLE", "sessions")
EST_TIMEZONE = ZoneInfo("America/New_York")


dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
patients_table = dynamodb.Table(PATIENTS_TABLE_NAME)
medications_table = dynamodb.Table(MEDICATIONS_TABLE_NAME)
sessions_table = dynamodb.Table(SESSIONS_TABLE_NAME)


def _model_dump(instance):
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    if hasattr(instance, "dict"):
        return instance.dict()
    return dict(instance)


def _build_patient(item: dict) -> Patient:
    return Patient(**item)


def _build_medication(item: dict) -> Medication:
    if "name" not in item and "medication_name" in item:
        item = dict(item)
        item["name"] = item["medication_name"]
    return Medication(**item)


def _scan_all(table) -> List[dict]:
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def _scan_filter(table, filter_expression) -> List[dict]:
    items = []
    response = table.scan(FilterExpression=filter_expression)
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=filter_expression,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
    return items


def _query_medications_by_patient(patient_id: str) -> List[dict]:
    try:
        response = medications_table.query(
            KeyConditionExpression=Key("patient_id").eq(patient_id)
        )
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = medications_table.query(
                KeyConditionExpression=Key("patient_id").eq(patient_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return items
    except ClientError:
        return _scan_filter(medications_table, Attr("patient_id").eq(patient_id))


def _find_medication_item(medication_id: str) -> Optional[dict]:
    items = _scan_filter(medications_table, Attr("medication_id").eq(medication_id))
    return items[0] if items else None


def _find_session_item_by_id(session_id: str) -> Optional[dict]:
    try:
        response = sessions_table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if item:
            return item
    except ClientError:
        pass

    items = _scan_filter(sessions_table, Attr("session_id").eq(session_id))
    return items[0] if items else None


def _get_next_patient_id() -> str:
    patients = load_patients()
    if not patients:
        return "P001"
    numbers = []
    for patient_id in patients.keys():
        if patient_id.startswith("P"):
            try:
                numbers.append(int(patient_id[1:]))
            except ValueError:
                continue
    if not numbers:
        return "P001"
    return f"P{max(numbers) + 1:03d}"


def _get_next_medication_id() -> str:
    medications = load_medications()
    if not medications:
        return "MED001"
    numbers = []
    for medication_id in medications.keys():
        if medication_id.startswith("MED"):
            try:
                numbers.append(int(medication_id[3:]))
            except ValueError:
                continue
    if not numbers:
        return "MED001"
    return f"MED{max(numbers) + 1:03d}"


# ============================================================================
# PATIENT FUNCTIONS
# ============================================================================

def load_patients() -> Dict[str, Patient]:
    items = _scan_all(patients_table)
    return {item["patient_id"]: _build_patient(item) for item in items if "patient_id" in item}


def save_patients(patients: Dict[str, Patient]):
    existing_items = _scan_all(patients_table)
    existing_ids = {item.get("patient_id") for item in existing_items if item.get("patient_id")}
    incoming_ids = set(patients.keys())

    with patients_table.batch_writer() as batch:
        for patient_id in existing_ids - incoming_ids:
            batch.delete_item(Key={"patient_id": patient_id})
        for patient_id, patient in patients.items():
            payload = _model_dump(patient)
            payload["patient_id"] = patient_id
            batch.put_item(Item=payload)


def get_patient(patient_id: str) -> Optional[Patient]:
    response = patients_table.get_item(Key={"patient_id": patient_id})
    item = response.get("Item")
    if not item:
        return None
    return _build_patient(item)


def create_patient(patient: Patient) -> Patient:
    if not patient.patient_id:
        patient.patient_id = _get_next_patient_id()
    now = datetime.now(EST_TIMEZONE).isoformat()
    patient.created_at = now
    patient.updated_at = now

    payload = _model_dump(patient)
    patients_table.put_item(Item=payload)
    return patient


def update_patient(patient_id: str, updated_patient: Patient) -> Optional[Patient]:
    existing = get_patient(patient_id)
    if not existing:
        return None

    updated_patient.patient_id = patient_id
    updated_patient.created_at = existing.created_at
    updated_patient.updated_at = datetime.now(EST_TIMEZONE).isoformat()

    payload = _model_dump(updated_patient)
    patients_table.put_item(Item=payload)
    return updated_patient


def delete_patient(patient_id: str) -> bool:
    existing = get_patient(patient_id)
    if not existing:
        return False

    patients_table.delete_item(Key={"patient_id": patient_id})
    delete_all_medications_for_patient(patient_id)
    delete_sessions_for_patient(patient_id)
    return True


def get_all_patients() -> List[Patient]:
    return list(load_patients().values())


# ============================================================================
# MEDICATION FUNCTIONS
# ============================================================================

def load_medications() -> Dict[str, Medication]:
    items = _scan_all(medications_table)
    medications = {}
    for item in items:
        medication_id = item.get("medication_id")
        if medication_id:
            medications[medication_id] = _build_medication(item)
    return medications


def save_medications(medications: Dict[str, Medication]):
    existing_items = _scan_all(medications_table)
    existing_keys = {
        (item.get("patient_id"), item.get("medication_id"))
        for item in existing_items
        if item.get("patient_id") and item.get("medication_id")
    }

    incoming_keys = set()
    with medications_table.batch_writer() as batch:
        for medication in medications.values():
            payload = _model_dump(medication)
            key = (payload.get("patient_id"), payload.get("medication_id"))
            if key[0] and key[1]:
                incoming_keys.add(key)
                batch.put_item(Item=payload)

        for patient_id, medication_id in existing_keys - incoming_keys:
            batch.delete_item(Key={"patient_id": patient_id, "medication_id": medication_id})


def get_medications_for_patient(patient_id: str) -> List[Medication]:
    items = _query_medications_by_patient(patient_id)
    return [_build_medication(item) for item in items]


def add_medication_to_patient(patient_id: str, medication: Medication) -> Optional[Medication]:
    if not get_patient(patient_id):
        return None

    if not medication.medication_id:
        medication.medication_id = _get_next_medication_id()
    medication.patient_id = patient_id

    payload = _model_dump(medication)
    medications_table.put_item(Item=payload)
    return medication


def remove_medication_from_patient(patient_id: str, medication_id: str) -> bool:
    existing = medications_table.get_item(
        Key={"patient_id": patient_id, "medication_id": medication_id}
    ).get("Item")

    if not existing:
        return False

    medications_table.delete_item(Key={"patient_id": patient_id, "medication_id": medication_id})
    return True


def update_medication(medication_id: str, updated_medication: Medication) -> Optional[Medication]:
    existing_item = _find_medication_item(medication_id)
    if not existing_item:
        return None

    patient_id = existing_item["patient_id"]
    payload = {
        "patient_id": patient_id,
        "medication_id": medication_id,
        "name": updated_medication.name,
        "dose": updated_medication.dose,
        "frequency": updated_medication.frequency,
    }
    medications_table.put_item(Item=payload)
    return _build_medication(payload)


def delete_all_medications_for_patient(patient_id: str):
    items = _query_medications_by_patient(patient_id)
    with medications_table.batch_writer() as batch:
        for item in items:
            medication_id = item.get("medication_id")
            if medication_id:
                batch.delete_item(Key={"patient_id": patient_id, "medication_id": medication_id})


# ============================================================================
# SESSION FUNCTIONS
# ============================================================================

def save_session(session_id: str, session_data: dict):
    patient_id = session_data.get("patient_id")
    if not patient_id:
        raise ValueError("patient_id is required in session_data for DynamoDB storage")

    item = {
        "patient_id": patient_id,
        "session_id": session_id,
        "session_data": session_data,
    }
    sessions_table.put_item(Item=item)


def load_session(session_id: str) -> Optional[dict]:
    item = _find_session_item_by_id(session_id)
    if not item:
        return None
    if "session_data" in item and isinstance(item["session_data"], dict):
        return item["session_data"]
    return item


def load_all_sessions() -> Dict[str, dict]:
    items = _scan_all(sessions_table)
    sessions = {}
    for item in items:
        session_id = item.get("session_id")
        if not session_id:
            continue
        payload = item.get("session_data") if isinstance(item.get("session_data"), dict) else item
        sessions[session_id] = payload
    return sessions


def load_sessions_for_patient(patient_id: str) -> Dict[str, dict]:
    try:
        response = sessions_table.query(KeyConditionExpression=Key("patient_id").eq(patient_id))
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = sessions_table.query(
                KeyConditionExpression=Key("patient_id").eq(patient_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
    except ClientError:
        items = _scan_filter(sessions_table, Attr("patient_id").eq(patient_id))

    sessions = {}
    for item in items:
        session_id = item.get("session_id")
        if not session_id:
            continue
        payload = item.get("session_data") if isinstance(item.get("session_data"), dict) else item
        sessions[session_id] = payload
    return sessions


def delete_sessions_for_patient(patient_id: str) -> int:
    try:
        response = sessions_table.query(KeyConditionExpression=Key("patient_id").eq(patient_id))
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = sessions_table.query(
                KeyConditionExpression=Key("patient_id").eq(patient_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
    except ClientError:
        items = _scan_filter(sessions_table, Attr("patient_id").eq(patient_id))

    deleted_count = 0
    with sessions_table.batch_writer() as batch:
        for item in items:
            session_id = item.get("session_id")
            if session_id:
                batch.delete_item(Key={"patient_id": patient_id, "session_id": session_id})
                deleted_count += 1

    return deleted_count
