import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "https://807pdm6rih.execute-api.us-east-1.amazonaws.com")
SESSIONS_FILE = os.path.join("data", "sessions.json")
EST_TIMEZONE = ZoneInfo("America/New_York")


EDUCATIONAL_PROMPTS = {
    "Diet": (
        "A balanced diet includes vegetables, proteins, whole grains, and healthy oils "
        "which help to control high blood pressure. Also, cutting back the salt can "
        "decrease the blood pressure."
    ),
    "Exercise": (
        "Including regular exercise can help control high blood pressure. Walking is a "
        "low-impact exercise, but contact your doctor before starting a new workout plan."
    ),
    "Other tips": (
        "Drinking alcohol and smoking cigarettes both increase your risk of high blood "
        "pressure. If you drink alcohol, limit the amount you drink to one serving size "
        "per day for women and two servings per day for men. For strategies to help you "
        "quit smoking, please get in touch with your doctor or nurse."
    ),
}


st.set_page_config(page_title="Interaction Dashboard", layout="wide")
st.title("🗣️ Interaction Dashboard - Intervention Script")
st.caption("Simulates the intervention flow and stores medication-administration session data.")


def now_iso() -> str:
    return datetime.now(EST_TIMEZONE).isoformat()


def parse_yes_no(value: str) -> Optional[bool]:
    normalized = value.strip().lower()
    if normalized in {"1", "yes", "y"}:
        return True
    if normalized in {"2", "no", "n"}:
        return False
    return None


def parse_yes_no_unregistered(value: str) -> Optional[str]:
    normalized = value.strip().lower()
    if normalized in {"1", "yes", "y"}:
        return "yes"
    if normalized in {"2", "no", "n"}:
        return "no"
    if normalized in {"3", "unable", "unable to register input", "unregistered"}:
        return "unregistered"
    return None


def parse_topic_choice(value: str) -> Optional[str]:
    normalized = value.strip().lower()
    if normalized in {"1", "diet"}:
        return "Diet"
    if normalized in {"2", "exercise"}:
        return "Exercise"
    if normalized in {"3", "other tips", "other", "tips"}:
        return "Other tips"
    if normalized in {"4", "leave", "leave now", "no response"}:
        return "Leave now / No response"
    return None


def _safe_json_load(path: str) -> Dict:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=2)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            text = file.read().strip()
            if not text:
                return {}
            return json.loads(text)
    except (json.JSONDecodeError, OSError):
        with open(path, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=2)
        return {}


def _save_session_local(session_id: str, payload: Dict) -> None:
    sessions = _safe_json_load(SESSIONS_FILE)
    sessions[session_id] = payload
    with open(SESSIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(sessions, file, indent=2)


def fetch_patients() -> List[Dict]:
    response = requests.get(f"{API_URL}/patients", timeout=10)
    response.raise_for_status()
    return response.json().get("patients", [])


def fetch_medications(patient_id: str) -> List[Dict]:
    response = requests.get(f"{API_URL}/patients/{patient_id}/medications", timeout=10)
    response.raise_for_status()
    return response.json().get("medications", [])


def initialize_session_state() -> None:
    defaults = {
        "flow_started": False,
        "flow_step": "identify",
        "selected_patient": None,
        "patient_medications": [],
        "current_medication_index": 0,
        "medication_records": [],
        "session_payload": {},
        "education_selected_topic": None,
        "education_text": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_flow() -> None:
    for key in [
        "flow_started",
        "flow_step",
        "selected_patient",
        "patient_medications",
        "current_medication_index",
        "medication_records",
        "session_payload",
        "education_selected_topic",
        "education_text",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    initialize_session_state()


def build_session_payload(patient: Dict, medications: List[Dict]) -> Dict:
    session_id = f"S_{patient['patient_id']}_{datetime.now(EST_TIMEZONE).strftime('%Y%m%d%H%M%S')}"
    created_at = now_iso()

    return {
        "session_id": session_id,
        "patient_id": patient["patient_id"],
        "created_at": created_at,
        "updated_at": created_at,
        "ended_at": None,
        "interaction_completed": False,
        "medication_administration": [],
        "medication_change_reported": False,
        "medication_change_details": "",
    }


def build_administration_record(
    administration_index: int,
    payload: Dict,
    medication: Dict,
    final_taken: Optional[bool],
    unresolved_input: bool,
    force_nurse_contact: bool = False,
) -> Dict:
    timestamp = now_iso()
    return {
        "administration_id": administration_index,
        "patient_id": payload["patient_id"],
        "medication_id": medication.get("medication_id"),
        "medication_name": medication.get("name"),
        "medication_frequency": medication.get("frequency", "once"),
        "patient_confirmed": bool(final_taken),
        "interaction_flag": True,
        "interaction_completion_flag": not unresolved_input,
        "nurse_contact_required": unresolved_input or force_nurse_contact,
        "educational_prompt_delivered": False,
        "medication_change_reported": payload.get("medication_change_reported", False),
        "medication_change_details": payload.get("medication_change_details", ""),
        "error_flag": unresolved_input,
        "error_description": "Input could not be registered" if unresolved_input else "",
        "created_at": timestamp,
        "updated_at": timestamp,
        "ended_at": timestamp,
    }


def sanitize_session_payload_for_schema(payload: Dict) -> Dict:
    session_fields = {
        "session_id",
        "patient_id",
        "created_at",
        "updated_at",
        "ended_at",
        "interaction_completed",
        "medication_administration",
    }
    admin_fields = {
        "administration_id",
        "patient_id",
        "medication_id",
        "medication_name",
        "medication_frequency",
        "patient_confirmed",
        "interaction_flag",
        "interaction_completion_flag",
        "nurse_contact_required",
        "educational_prompt_delivered",
        "medication_change_reported",
        "medication_change_details",
        "error_flag",
        "error_description",
        "created_at",
        "updated_at",
        "ended_at",
    }

    cleaned = {k: payload.get(k) for k in session_fields if k in payload}
    administration_records = payload.get("medication_administration", [])
    cleaned["medication_administration"] = []
    for record in administration_records:
        cleaned_record = {k: record.get(k) for k in admin_fields if k in record}
        cleaned["medication_administration"].append(cleaned_record)

    return cleaned


def save_session(payload: Dict) -> str:
    payload["updated_at"] = now_iso()
    cleaned_payload = sanitize_session_payload_for_schema(payload)
    try:
        response = requests.post(f"{API_URL}/sessions", json=cleaned_payload, timeout=10)
        response.raise_for_status()
        return "Saved through API to sessions.json"
    except Exception:
        _save_session_local(cleaned_payload["session_id"], cleaned_payload)
        return "API unavailable, saved directly to data/sessions.json"


initialize_session_state()

if st.button("Reset Interaction", type="secondary"):
    reset_flow()
    st.rerun()

st.header("1) Identify Participant")

if not st.session_state.flow_started:
    st.write("Alexa: Hello, what is your identifier?")
    identifier_value = st.text_input("Participant identifier", placeholder="Example: 1234")

    if st.button("Start Interaction", type="primary"):
        if not identifier_value.strip():
            st.error("Identifier is required.")
        else:
            try:
                all_patients = fetch_patients()
                active_patients = [p for p in all_patients if p.get("is_active", True)]

                matched_patient = None
                for patient in active_patients:
                    if patient.get("pairing_code") == identifier_value.strip():
                        matched_patient = patient
                        break

                if not matched_patient:
                    for patient in active_patients:
                        if patient.get("patient_id") == identifier_value.strip():
                            matched_patient = patient
                            break

                if not matched_patient:
                    st.error("No active patient found for the provided identifier.")
                else:
                    medications = fetch_medications(matched_patient["patient_id"])
                    st.session_state.selected_patient = matched_patient
                    st.session_state.patient_medications = medications
                    st.session_state.session_payload = build_session_payload(matched_patient, medications)
                    st.session_state.flow_started = True
                    st.session_state.flow_step = "medication_change_check"
                    st.success(
                        f"Patient identified: {matched_patient['first_name']} {matched_patient['last_name']} ({matched_patient['patient_id']})"
                    )
                    st.rerun()
            except Exception as error:
                st.error(f"Could not start interaction: {error}")

else:
    patient = st.session_state.selected_patient
    payload = st.session_state.session_payload
    medications = st.session_state.patient_medications

    st.success(
        f"Active patient: {patient['first_name']} {patient['last_name']} | ID: {patient['patient_id']} | Pairing code: {patient['pairing_code']}"
    )

    if st.session_state.flow_step == "medication_change_check":
        st.header("2) Medication Change Check")
        st.write(
            "Alexa: Great, let's begin. Before we continue, have any changes been made "
            "to your blood pressure medications?"
        )
        st.caption("Type 1 for Yes, 2 for No")
        change_input = st.text_input("Participant response", key="change_input")
        change_details = st.text_area(
            "Change details (optional)",
            placeholder="Capture any reported medication changes...",
        )

        if st.button("Continue"):
            change_answer = parse_yes_no(change_input)
            if change_answer is None:
                st.error("Invalid response. Please type 1 (Yes) or 2 (No).")
                st.stop()

            payload["medication_change_reported"] = change_answer
            payload["medication_change_details"] = change_details.strip() if change_answer else ""
            payload["updated_at"] = now_iso()

            if change_answer:
                payload["nurse_contact_required"] = True
                if medications:
                    change_records = []
                    for index, medication in enumerate(medications, start=1):
                        change_records.append(
                            build_administration_record(
                                administration_index=index,
                                payload=payload,
                                medication=medication,
                                final_taken=False,
                                unresolved_input=False,
                                force_nurse_contact=True,
                            )
                        )
                    st.session_state.medication_records = change_records
                    payload["medication_administration"] = change_records
                st.session_state.flow_step = "education_interest"
            else:
                if medications:
                    st.session_state.flow_step = "medication_questions"
                    st.session_state.current_medication_index = 0
                else:
                    st.session_state.flow_step = "education_interest"
            st.rerun()

    elif st.session_state.flow_step == "medication_questions":
        current_index = st.session_state.current_medication_index

        if current_index >= len(medications):
            st.session_state.flow_step = "education_interest"
            st.rerun()

        medication = medications[current_index]
        med_frequency = medication.get("frequency", "once")
        st.header(f"3) Medication Confirmation ({current_index + 1}/{len(medications)})")
        st.write(
            "Alexa: Okay, did you take your "
            f"**{medication['name']} {medication['dose']}** today? It is for your blood pressure and you take it **{med_frequency} a day**."
        )

        st.caption("Type 1 for Yes, 2 for No, 3 for Unable to register input")
        initial_input = st.text_input("Participant response", key=f"initial_answer_{current_index}")

        st.write(
            "Alexa: You told me that you took your medication, or you told me that you "
            "have not taken your medication. Is this correct?"
        )
        st.caption("Type 1 for Yes, 2 for No")
        confirm_input = st.text_input("Participant confirmation", key=f"confirm_answer_{current_index}")

        confirm_answer = parse_yes_no(confirm_input)

        retry_answer = None
        if confirm_answer is False:
            st.caption("Repeat prompt: type 1 for Yes, 2 for No, 3 for Unable to register input")
            retry_answer = st.text_input("Repeat response", key=f"retry_answer_{current_index}")

        if st.button("Save Medication Response"):
            unresolved = False
            final_taken: Optional[bool] = None
            parsed_initial = parse_yes_no_unregistered(initial_input)
            parsed_confirm = parse_yes_no(confirm_input)

            if parsed_initial is None:
                st.error("Invalid initial response. Use 1, 2, or 3.")
                st.stop()

            if parsed_confirm is None:
                st.error("Invalid confirmation response. Use 1 or 2.")
                st.stop()

            if parsed_initial == "unregistered":
                unresolved = True
            else:
                resolved_answer = parsed_initial
                if parsed_confirm is False:
                    parsed_retry = parse_yes_no_unregistered(retry_answer or "")
                    if parsed_retry is None:
                        st.error("Invalid repeat response. Use 1, 2, or 3.")
                        st.stop()
                    if parsed_retry == "unregistered":
                        unresolved = True
                    else:
                        resolved_answer = parsed_retry
                final_taken = True if resolved_answer == "yes" else False

            record = build_administration_record(
                administration_index=current_index + 1,
                payload=payload,
                medication=medication,
                final_taken=final_taken,
                unresolved_input=unresolved,
            )

            if unresolved:
                st.warning("Input could not be registered. Nurse contact is required.")

            st.session_state.medication_records.append(record)
            payload["medication_administration"] = st.session_state.medication_records
            payload["updated_at"] = now_iso()

            if unresolved:
                st.session_state.flow_step = "education_interest"
            else:
                st.session_state.current_medication_index += 1
                if st.session_state.current_medication_index >= len(medications):
                    st.session_state.flow_step = "education_interest"
            st.rerun()

    elif st.session_state.flow_step == "education_interest":
        st.header("4) Educational Prompt")
        st.write("Alexa: Would you like more information about taking care of your high blood pressure?")
        st.caption("Type 1 for Yes, 2 for No")
        education_interest_input = st.text_input("Participant response", key="education_interest_input")

        if st.button("Continue to Confirmation"):
            education_interest = parse_yes_no(education_interest_input)
            if education_interest is None:
                st.error("Invalid response. Please type 1 (Yes) or 2 (No).")
                st.stop()

            payload["updated_at"] = now_iso()
            if education_interest is False:
                st.session_state.flow_step = "finalize"
            else:
                st.session_state.flow_step = "education_confirm"
            st.rerun()

    elif st.session_state.flow_step == "education_confirm":
        st.header("5) Confirm Educational Intent")
        st.write("Alexa: You want to hear more about how to take care of high blood pressure. Correct?")
        st.caption("Type 1 for Yes, 2 for No")
        education_confirm_input = st.text_input("Participant response", key="education_confirm_input")

        if st.button("Continue to Topic Selection"):
            education_confirm = parse_yes_no(education_confirm_input)
            if education_confirm is None:
                st.error("Invalid response. Please type 1 (Yes) or 2 (No).")
                st.stop()

            payload["updated_at"] = now_iso()
            if education_confirm is False:
                st.session_state.flow_step = "finalize"
            else:
                st.session_state.flow_step = "education_topic"
            st.rerun()

    elif st.session_state.flow_step == "education_topic":
        st.header("6) Select Educational Topic")
        st.write(
            "Alexa: If you would like to hear more information about eating right, say 1; "
            "if you would like to hear about exercise, say 2; if you would like to hear "
            "more tips, say 3; if you are finished, say 4."
        )
        st.caption("Type 1 (Diet), 2 (Exercise), 3 (Other tips), or 4 (Leave now)")
        selected_topic_input = st.text_input("Participant response", key="topic_input")

        if st.button("Apply Topic"):
            mapped_topic = parse_topic_choice(selected_topic_input)
            if mapped_topic is None:
                st.error("Invalid response. Please type 1, 2, 3, or 4.")
                st.stop()

            if mapped_topic in EDUCATIONAL_PROMPTS:
                payload["educational_prompt_delivered"] = True
                st.session_state.education_selected_topic = mapped_topic
                st.session_state.education_text = EDUCATIONAL_PROMPTS[mapped_topic]
            else:
                payload["educational_prompt_delivered"] = False
                st.session_state.education_selected_topic = None
                st.session_state.education_text = None

            payload["updated_at"] = now_iso()
            st.session_state.flow_step = "finalize"
            st.rerun()

    elif st.session_state.flow_step == "finalize":
        st.header("7) Finalize Session")

        if st.session_state.education_selected_topic:
            st.info(
                f"Educational prompt delivered: {st.session_state.education_selected_topic}"
            )
            st.write(st.session_state.education_text)
        else:
            st.write("No educational topic delivered.")

        payload["medication_administration"] = st.session_state.medication_records
        for record in payload["medication_administration"]:
            record["educational_prompt_delivered"] = payload.get("educational_prompt_delivered", False)
            record["updated_at"] = now_iso()

        unresolved_any = any(r.get("error_flag") for r in payload["medication_administration"])
        payload["ended_at"] = now_iso()
        payload["interaction_completed"] = True

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Medication records", len(payload["medication_administration"]))
        with col2:
            st.metric("Nurse contact required", "Yes" if unresolved_any or payload.get("medication_change_reported") else "No")

        if st.button("Save Session", type="primary"):
            save_message = save_session(payload)
            st.success(f"Session complete. {save_message}")
            st.json(payload)

        if st.button("Start New Interaction"):
            reset_flow()
            st.rerun()
