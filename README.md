# Alexa Medication Management Backend

Production-style backend and utilities for an Alexa medication management workflow.

## Repository Overview

This repository contains:

- A FastAPI backend for patient, medication, and session management.
- Optional JSON file storage and DynamoDB storage backends.
- Deployment scripts for backend and Alexa skill Lambda functions.
- Basic edge case API testing.

## Main Components

- `main.py`: FastAPI application and HTTP endpoints.
- `handler.py`: AWS Lambda adapter/entrypoint.
- `data_models.py`: Shared data models.
- `data_storage.py`: Local JSON storage implementation.
- `data_storage_dynamodb.py`: DynamoDB storage implementation.
- `tests/edge_case_api_tests.py`: API edge-case validation script.
- `2-alexa-remote-api-example-skill/`: Alexa skill project.

## Local Development

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run locally:

```bash
uvicorn main:app --reload
```

## Deployment

- Backend deploy script: `deploy_backend_fast.ps1`
- Alexa skill deploy script: `deploy_alexa_fast.ps1`
- Combined deploy script: `deploy_both_skills.ps1`

See `DEPLOYMENT_RUNBOOK.md` for operational details.

## Data and Secrets

- Local session data (`data/sessions.json`) is ignored by git.
- Local secrets (`.streamlit/secrets.toml`) are ignored by git.
- Generated artifacts and local-only files are excluded via `.gitignore`.
