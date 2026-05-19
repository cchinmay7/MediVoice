# Edge Case Testing Guide

This project now includes an automated API edge-case runner plus a manual Alexa edge-case matrix.

## 1) Run API edge-case tests

From the project root:

```powershell
python tests/edge_case_api_tests.py
```

To test a different backend URL:

```powershell
$env:API_URL="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
python tests/edge_case_api_tests.py
```

What this script covers:
- Health endpoint availability
- 404 behavior for missing patient/medication
- 422 validation errors for malformed payloads
- 400 behavior for missing required `patient_id` in sessions
- Create/read session round-trip
- Patient sessions list includes newly-saved session
- Cleanup path (deletes temporary patient)

## 2) Alexa conversation edge-case matrix (manual)

Use Alexa Simulator with the same skill and verify these outcomes.

### A. Identifier and startup
1. Say: `open medication check`
   - Expected: asks for identifier.
2. Say invalid identifier (e.g. `ABC123`)
   - Expected: "could not find an active patient" reprompt.
3. Say valid identifier (`0000`, `9999`, `1234`, `P001`, etc.)
   - Expected: "Hello, how can I help you?"

### B. State-order robustness
1. Before identifier, say: `I took my medication`
   - Expected: asks for identifier first.
2. During medication flow, say unrelated phrase
   - Expected: fallback/reprompt path, not crash.

### C. Medication confirmation correctness
1. Follow flow to medication confirmation.
2. Confirm response should include exact medication name + dose.
   - Expected format: "You told me that you took your [name] [dose]. Is this correct?"

### D. Education topic parsing
At education topic prompt, test each utterance:
- `one` / `1` / `diet`
- `two` / `2` / `exercise`
- `three` / `3` / `tips`
- `leave now`

Expected:
- `one|two|three` returns matching educational content then goodbye.
- `leave now` exits cleanly with goodbye.
- Unknown topic (e.g. `banana`) should reprompt with "say one, two, three, or leave now."

## 3) Data persistence checks

After each completed Alexa run, verify session persistence:

```powershell
Invoke-WebRequest -Uri "https://807pdm6rih.execute-api.us-east-1.amazonaws.com/patients/P001/sessions" | Select-Object -ExpandProperty Content
```

Expected: a new session item appears with updated timestamps and medication administration details.

## 4) Quick fail triage

- API script failures at connectivity stage: verify API Gateway URL and Lambda health.
- Alexa says generic error: inspect CloudWatch logs for `medication-alexa-skill`.
- Session missing after Alexa run: verify skill Lambda `API_BASE_URL` and backend `/sessions` endpoint response.
