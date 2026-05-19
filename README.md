# Alexa Medication Management Backend

Production-style backend and utilities for an Alexa medication management workflow.

## Repository Overview

This repository contains:

- A FastAPI backend for patient, medication, and session management.
- Optional JSON file storage and DynamoDB storage backends.
- Alexa skill integration project for remote API calls.
- Basic edge case API testing.

## Main Components

- `main.py`: FastAPI application and HTTP endpoints.
- `handler.py`: AWS Lambda adapter/entrypoint.
- `data_models.py`: Shared data models.
- `data_storage.py`: Local JSON storage implementation.
- `data_storage_dynamodb.py`: DynamoDB storage implementation.
- `tests/edge_case_api_tests.py`: API edge-case validation script.
- `alexa-remote-api-skill/`: Alexa skill project.

## Local Development

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install fastapi uvicorn pydantic python-multipart boto3 requests mangum
```

3. Run locally:

```bash
uvicorn main:app --reload
```

## Misc Folder

Operational and non-essential files are organized under `misc/`:

- `misc/docs/`: archived architecture/deployment notes
- `misc/ops/`: optional deployment scripts and AWS helper files
- `misc/ui-tools/`: optional dashboard utilities

## Data and Secrets

- Local session data (`data/sessions.json`) is ignored by git.
- Local secrets (`.streamlit/secrets.toml`) are ignored by git.
- Generated artifacts and local-only files are excluded via `.gitignore`.
