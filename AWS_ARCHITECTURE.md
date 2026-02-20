# AWS Architecture (Basic + Easy Setup)

This version is intentionally minimal for quick setup and testing.

## 1) Minimal Architecture

```
Alexa Skill
  ↓
API Gateway (HTTP API)
  ↓
Lambda (Python)
  ↓
DynamoDB (patients, medications, sessions)
```

Optional for admins only:

```
Local machine or EC2
  ↓
Streamlit dashboards (admin + interaction)
```

---

## 2) AWS Services You Actually Need

1. Lambda (run backend)
2. API Gateway (public HTTPS endpoint)
3. DynamoDB (store data)
4. CloudWatch (logs, automatic)

No VPC, no ECS, no extra networking for MVP.

---

## 3) Fast Setup Steps

### Step A: Prepare Lambda handler

Install dependency:

```bash
pip install mangum
```

Create `handler.py`:

```python
from mangum import Mangum
from main import app

handler = Mangum(app)
```

### Step B: Package code

```bash
mkdir lambda_package
copy main.py lambda_package
copy data_models.py lambda_package
copy data_storage.py lambda_package
copy handler.py lambda_package
pip install -r requirements.txt -t lambda_package
cd lambda_package
powershell Compress-Archive -Path * -DestinationPath ..\lambda.zip -Force
cd ..
```

### Step C: Create Lambda

In AWS Console:

1. Lambda → Create function
2. Runtime: Python 3.11
3. Upload `lambda.zip`
4. Handler: `handler.handler`
5. Timeout: 30s, Memory: 512 MB

### Step D: Create API Gateway

1. API Gateway → HTTP API
2. Add Lambda integration (the function above)
3. Deploy default stage
4. Copy invoke URL

### Step E: Connect Alexa Skill

In Alexa Developer Console:

1. Endpoint type: HTTPS
2. Paste API Gateway invoke URL
3. Save and test intents

---

## 4) DynamoDB (Simple Table Plan)

Create 3 tables:

1. `patients` (PK: `patient_id`)
2. `medications` (PK: `medication_id`)
3. `sessions` (PK: `session_id`)

For MVP, use on-demand capacity (default).

---

## 5) Local Development (Keep It Simple)

Run locally first:

```bash
python main.py
streamlit run interaction_dashboard.py --server.port 8503
streamlit run admin_dashboard.py --server.port 8501
```

Only deploy to AWS after local flow works.

---

## 6) Estimated Cost (MVP)

- Low traffic/testing: usually very low cost (often within free tier)
- Main paid services after free tier: API Gateway + Lambda + DynamoDB

---

## 7) Troubleshooting Checklist

1. Lambda handler set to `handler.handler`
2. API Gateway points to correct Lambda
3. Alexa endpoint URL is the deployed API Gateway URL
4. CloudWatch logs show request/response errors
5. Data write permissions are enabled for DynamoDB in Lambda role

---

## 8) Recommended MVP Order

1. Get API working locally
2. Deploy Lambda + API Gateway
3. Connect Alexa endpoint
4. Move storage from JSON to DynamoDB
5. Keep Streamlit for admin/testing only
