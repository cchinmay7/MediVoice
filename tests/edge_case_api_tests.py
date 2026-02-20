import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE_URL = os.getenv("API_URL", "https://807pdm6rih.execute-api.us-east-1.amazonaws.com").rstrip("/")


class TestFailure(Exception):
    pass


def request_json(method: str, path: str, payload=None):
    url = f"{API_BASE_URL}{path}"
    body = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url=url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return response.status, parsed
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return error.code, parsed


def assert_status(actual, expected, context):
    if actual != expected:
        raise TestFailure(f"{context}: expected status {expected}, got {actual}")


def assert_true(condition, context):
    if not condition:
        raise TestFailure(context)


def run_case(name, fn, results):
    try:
        fn()
        results.append((name, True, ""))
        print(f"✅ {name}")
    except Exception as error:
        results.append((name, False, str(error)))
        print(f"❌ {name} -> {error}")


def main():
    print(f"Running API edge tests against: {API_BASE_URL}")
    results = []

    temp = {
        "patient_id": None,
        "medication_id": None,
        "session_id": None,
    }

    unique_suffix = str(int(time.time() * 1000))[-6:]
    patient_payload = {
        "first_name": "Edge",
        "last_name": f"Case{unique_suffix}",
        "pairing_code": f"EC{unique_suffix}",
        "is_active": True,
    }

    def case_health_check():
        status, body = request_json("GET", "/")
        assert_status(status, 200, "Health check")
        assert_true(body.get("status") == "ok", "Health check body missing status=ok")

    def case_get_missing_patient():
        status, body = request_json("GET", "/patients/DOES_NOT_EXIST")
        assert_status(status, 404, "Missing patient should return 404")
        assert_true("detail" in body, "Missing patient response should include detail")

    def case_create_patient_validation_error():
        bad_payload = {"first_name": "BadOnly"}
        status, _ = request_json("POST", "/patients", bad_payload)
        assert_status(status, 422, "Invalid patient payload should return 422")

    def case_create_temp_patient():
        status, body = request_json("POST", "/patients", patient_payload)
        assert_status(status, 200, "Create temp patient")
        patient_id = body.get("patient_id")
        assert_true(bool(patient_id), "Create patient response missing patient_id")
        temp["patient_id"] = patient_id

    def case_add_medication_to_missing_patient():
        status, _ = request_json(
            "POST",
            "/patients/DOES_NOT_EXIST/medications",
            {"name": "Lisinopril", "dose": "10 mg"},
        )
        assert_status(status, 404, "Add medication to missing patient should return 404")

    def case_add_medication_validation_error():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, _ = request_json(
            "POST",
            f"/patients/{temp['patient_id']}/medications",
            {"name": "MissingDose"},
        )
        assert_status(status, 422, "Medication payload missing dose should return 422")

    def case_add_temp_medication():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, body = request_json(
            "POST",
            f"/patients/{temp['patient_id']}/medications",
            {"name": "EdgeMed", "dose": "1 mg"},
        )
        assert_status(status, 200, "Create temp medication")
        med_id = body.get("medication_id")
        assert_true(bool(med_id), "Create medication response missing medication_id")
        temp["medication_id"] = med_id

    def case_get_patient_medications():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, body = request_json("GET", f"/patients/{temp['patient_id']}/medications")
        assert_status(status, 200, "Get patient medications")
        meds = body.get("medications", [])
        assert_true(any(m.get("medication_id") == temp["medication_id"] for m in meds), "Temp medication not found in patient medication list")

    def case_update_missing_medication():
        status, _ = request_json(
            "PUT",
            "/medications/MED_DOES_NOT_EXIST",
            {"name": "X", "dose": "1 mg"},
        )
        assert_status(status, 404, "Update missing medication should return 404")

    def case_save_session_missing_patient_id():
        status, _ = request_json("POST", "/sessions", {"session_id": "S_BAD"})
        assert_status(status, 400, "Session payload without patient_id should return 400")

    def case_save_session_unknown_patient():
        status, _ = request_json("POST", "/sessions", {"session_id": "S_BAD2", "patient_id": "DOES_NOT_EXIST"})
        assert_status(status, 404, "Session payload with unknown patient_id should return 404")

    def case_save_valid_session():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        sid = f"S_EDGE_{temp['patient_id']}_{int(time.time())}"
        payload = {
            "session_id": sid,
            "patient_id": temp["patient_id"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ended_at": None,
            "medication_administration": [
                {
                    "administration_id": 1,
                    "patient_id": temp["patient_id"],
                    "medication_id": temp["medication_id"],
                    "medication_name": "EdgeMed",
                    "patient_confirmed": True,
                    "interaction_flag": True,
                    "interaction_completion_flag": True,
                    "nurse_contact_required": False,
                    "educational_prompt_delivered": False,
                    "medication_change_reported": False,
                    "medication_change_details": "",
                    "error_flag": False,
                    "error_description": "",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ],
        }
        status, body = request_json("POST", "/sessions", payload)
        assert_status(status, 200, "Save valid session")
        assert_true(body.get("session_id") == sid, "Saved session_id mismatch")
        temp["session_id"] = sid

    def case_get_saved_session():
        assert_true(temp["session_id"] is not None, "Valid session was not saved")
        status, body = request_json("GET", f"/sessions/{temp['session_id']}")
        assert_status(status, 200, "Get saved session")
        session = body.get("session", {})
        assert_true(session.get("patient_id") == temp["patient_id"], "Saved session patient_id mismatch")

    def case_get_patient_sessions():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, body = request_json("GET", f"/patients/{temp['patient_id']}/sessions")
        assert_status(status, 200, "Get patient sessions")
        sessions = body.get("sessions", [])
        assert_true(any(s.get("session_id") == temp["session_id"] for s in sessions), "Saved session missing from patient session list")

    def case_delete_missing_medication():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, _ = request_json(
            "DELETE",
            f"/patients/{temp['patient_id']}/medications/MED_DOES_NOT_EXIST",
        )
        assert_status(status, 404, "Delete missing medication should return 404")

    def case_cleanup_delete_patient():
        if not temp["patient_id"]:
            raise TestFailure("No temp patient to clean up")
        status, _ = request_json("DELETE", f"/patients/{temp['patient_id']}")
        assert_status(status, 200, "Cleanup delete temp patient")

    def case_verify_deleted_patient():
        assert_true(temp["patient_id"] is not None, "Temp patient was not created")
        status, _ = request_json("GET", f"/patients/{temp['patient_id']}")
        assert_status(status, 404, "Deleted patient should return 404")

    test_cases = [
        ("Health check", case_health_check),
        ("Missing patient returns 404", case_get_missing_patient),
        ("Invalid patient payload returns 422", case_create_patient_validation_error),
        ("Create temp patient", case_create_temp_patient),
        ("Add medication to missing patient returns 404", case_add_medication_to_missing_patient),
        ("Invalid medication payload returns 422", case_add_medication_validation_error),
        ("Create temp medication", case_add_temp_medication),
        ("Read temp patient medications", case_get_patient_medications),
        ("Update missing medication returns 404", case_update_missing_medication),
        ("Session missing patient_id returns 400", case_save_session_missing_patient_id),
        ("Session unknown patient returns 404", case_save_session_unknown_patient),
        ("Save valid session", case_save_valid_session),
        ("Get saved session", case_get_saved_session),
        ("Get patient sessions includes new session", case_get_patient_sessions),
        ("Delete missing medication returns 404", case_delete_missing_medication),
        ("Cleanup delete temp patient", case_cleanup_delete_patient),
        ("Verify temp patient deleted", case_verify_deleted_patient),
    ]

    for name, fn in test_cases:
        run_case(name, fn, results)

    failed = [item for item in results if not item[1]]
    total = len(results)
    passed = total - len(failed)

    print("\n--- Edge Case Test Summary ---")
    print(f"Passed: {passed}/{total}")

    if failed:
        print("Failures:")
        for name, _, reason in failed:
            print(f"- {name}: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
