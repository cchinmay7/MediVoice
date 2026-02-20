# Deployment Runbook (Step-by-Step)

This guide takes you from local code to a testable Alexa skill in AWS.

## What you have already
- FastAPI backend: `main.py`, `data_models.py`, `data_storage.py`
- DynamoDB storage module: `data_storage_dynamodb.py`
- Alexa skill project: `2-alexa-remote-api-example-skill`

## Goal
1. Deploy backend API
2. Put API behind API Gateway
3. Set up DynamoDB
4. Deploy Alexa skill and test end-to-end

---

## 0) Prerequisites (one-time)

Install and configure:
- AWS CLI (`aws --version`)
- Node.js + npm (`node -v`, `npm -v`)
- Python 3.11+
- Alexa Developer Console access

Configure AWS credentials:

```powershell
aws configure
```

Use the same AWS region for all resources (example: `us-east-1`).

---

## 1) Deploy Backend (FastAPI) to Lambda

Your current backend is FastAPI, so Lambda needs an adapter (`Mangum`).

### 1.1 Create Lambda handler file
Create `handler.py` in project root:

```python
from mangum import Mangum
from main import app

handler = Mangum(app)
```

### 1.2 Build deployment package (PowerShell)
From project root (`E:\Projects\Alexa Skill`):

```powershell
Remove-Item -Recurse -Force .\lambda_backend_package -ErrorAction SilentlyContinue
New-Item -ItemType Directory .\lambda_backend_package | Out-Null

Copy-Item .\main.py .\lambda_backend_package\
Copy-Item .\data_models.py .\lambda_backend_package\
Copy-Item .\data_storage.py .\lambda_backend_package\
Copy-Item .\data_storage_dynamodb.py .\lambda_backend_package\
Copy-Item .\handler.py .\lambda_backend_package\
Copy-Item .\requirements.txt .\lambda_backend_package\

python -m pip install -r .\requirements.txt -t .\lambda_backend_package
python -m pip install mangum -t .\lambda_backend_package

Remove-Item .\backend_lambda.zip -ErrorAction SilentlyContinue
Compress-Archive -Path .\lambda_backend_package\* -DestinationPath .\backend_lambda.zip -Force
```

### 1.3 Create backend Lambda (Console)
In AWS Console:
1. Lambda → Create function
2. Runtime: `Python 3.11`
3. Function name: `medication-backend-api`
4. Upload zip: `backend_lambda.zip`
5. Handler: `handler.handler`
6. Timeout: `30 sec`
7. Memory: `512 MB`

### 1.4 IAM permissions for backend Lambda
Attach permissions:
- `AWSLambdaBasicExecutionRole` (CloudWatch logs)
- DynamoDB access policy (start with `AmazonDynamoDBFullAccess` for dev only)

### 1.5 Set backend Lambda environment variables

Use these in Lambda:

- `STORAGE_BACKEND=dynamodb` (for AWS DynamoDB mode)
- `AWS_REGION=us-east-1` (or your chosen region)
- `PATIENTS_TABLE=patients`
- `MEDICATIONS_TABLE=medications`
- `SESSIONS_TABLE=sessions`

For local JSON mode, use:

- `STORAGE_BACKEND=json`

---

## 2) Create API Gateway for Backend

### 2.1 Create HTTP API
In API Gateway:
1. Create API → **HTTP API**
2. Integration: backend Lambda `medication-backend-api`
3. Add route: `ANY /{proxy+}`
4. Add route: `ANY /` (optional but useful)
5. Deploy default stage (for example `prod`)

Copy invoke URL. Example:

`https://abc123.execute-api.us-east-1.amazonaws.com`

(If your stage is explicit, it may be `...amazonaws.com/prod`.)

### 2.2 Test API Gateway endpoint

```powershell
# health
curl https://<your-api-id>.execute-api.<region>.amazonaws.com/

# create test patient
curl -X POST https://<your-api-id>.execute-api.<region>.amazonaws.com/patients -H "Content-Type: application/json" -d "{\"first_name\":\"Test\",\"last_name\":\"User\",\"pairing_code\":\"1234\",\"is_active\":true}"

# list patients
curl https://<your-api-id>.execute-api.<region>.amazonaws.com/patients
```

If these pass, backend deployment is working.

---

## 3) DynamoDB Setup

> Important: backend switching is now built in. `main.py` uses `STORAGE_BACKEND`:
> - `json` → `data_storage.py`
> - `dynamodb` → `data_storage_dynamodb.py`

### 3.1 Create DynamoDB tables (simple practical schema)
Use On-Demand capacity.

#### Table A: `patients`
- Partition key: `patient_id` (String)

#### Table B: `medications`
- Partition key: `patient_id` (String)
- Sort key: `medication_id` (String)

#### Table C: `sessions`
- Partition key: `patient_id` (String)
- Sort key: `session_id` (String)

This key design makes your existing API operations straightforward:
- list medications by patient
- list sessions by patient

### 3.2 Required app setting
No code rewrite required now. Just set backend Lambda environment variables:

- `STORAGE_BACKEND=dynamodb`
- `PATIENTS_TABLE=patients`
- `MEDICATIONS_TABLE=medications`
- `SESSIONS_TABLE=sessions`

Then redeploy the backend Lambda zip if needed and retest `/patients`.

---

## 4) Deploy Alexa Skill Lambda (Node)

This is the Lambda for `2-alexa-remote-api-example-skill/lambda/custom/index.js`.

### 4.1 Build skill Lambda package

```powershell
cd "E:\Projects\Alexa Skill\2-alexa-remote-api-example-skill\lambda\custom"
npm install

Remove-Item .\skill_lambda.zip -ErrorAction SilentlyContinue
Compress-Archive -Path .\* -DestinationPath .\skill_lambda.zip -Force
```

### 4.2 Create skill Lambda (Console)
1. Lambda → Create function
2. Runtime: `Node.js 18.x` (or 20.x)
3. Function name: `medication-alexa-skill`
4. Upload `skill_lambda.zip`
5. Handler: `index.handler`

### 4.3 Set skill Lambda environment variable
Set:
- `API_BASE_URL` = your API Gateway backend URL from Step 2

Example:
- `https://abc123.execute-api.us-east-1.amazonaws.com`

---

## 5) Deploy Skill Configuration in Alexa Developer Console

### 5.1 Import or create skill
Use files from:
- `2-alexa-remote-api-example-skill/skill.json`
- `2-alexa-remote-api-example-skill/models/en-US.json`

### 5.2 Set endpoint
In Alexa Console → Build → Endpoint:
- Choose **AWS Lambda ARN**
- Paste ARN of `medication-alexa-skill`

### 5.3 Build interaction model
- Click **Save Model**
- Click **Build Model**

---

## 6) Test the Skill (this is the key part)

In Alexa Developer Console → **Test** tab (Development):

Use this sequence:
1. `open medication check`
2. `my identifier is 1234`
3. `i took my medicine`
4. `no` (to medication change question)
5. answer med questions with `yes` / `no`
6. confirm response with `yes` / `no`
7. education prompt: `yes`/`no`, then `one`/`two`/`three`/`leave now`

### Verify persistence
Check backend API:

```powershell
curl https://<your-api-id>.execute-api.<region>.amazonaws.com/patients/P001/sessions
```

You should see session objects with `medication_administration` entries.

---

## 7) Troubleshooting

### Alexa says generic error
- Check CloudWatch logs for `medication-alexa-skill`
- Ensure skill Lambda has `API_BASE_URL` set correctly

### Skill cannot reach backend
- `API_BASE_URL` is wrong or not public
- API Gateway route missing (`ANY /{proxy+}`)

### Backend works but data not in DynamoDB
- Backend Lambda env var `STORAGE_BACKEND` not set to `dynamodb`
- DynamoDB table env vars are missing or table names mismatch
- Lambda role missing DynamoDB permissions

### Model not matching utterances
- Rebuild Alexa model after editing `en-US.json`

---

## 8) Recommended order (fastest path)
1. Deploy backend Lambda + API Gateway
2. Test backend with `curl`
3. Deploy Alexa skill Lambda with `API_BASE_URL`
4. Build model in Alexa Console
5. Run simulator flow
6. Set `STORAGE_BACKEND=dynamodb` and verify DynamoDB writes

---

If needed, next step is adding GSIs and stricter validation for production-scale query patterns.

---

## 9) AWS Console Click Path (No Guesswork)

Use this exact order the first time.

### A. Create backend Lambda (`medication-backend-api`)
1. AWS Console → **Lambda**
2. Click **Create function**
3. Select **Author from scratch**
4. Function name: `medication-backend-api`
5. Runtime: `Python 3.11`
6. Architecture: `x86_64`
7. Click **Create function**
8. In **Code** tab → **Upload from** → `.zip file` → choose `backend_lambda.zip`
9. In **Runtime settings** → **Edit** → Handler = `handler.handler` → Save
10. In **Configuration** → **General configuration** → Edit:
	- Timeout: `30 sec`
	- Memory: `512 MB`
11. In **Configuration** → **Environment variables** → Add:
	- `STORAGE_BACKEND=dynamodb`
	- `AWS_REGION=us-east-1`
	- `PATIENTS_TABLE=patients`
	- `MEDICATIONS_TABLE=medications`
	- `SESSIONS_TABLE=sessions`
12. In **Configuration** → **Permissions** → click role name → attach:
	- `AWSLambdaBasicExecutionRole`
	- `AmazonDynamoDBFullAccess` (dev only)

### B. Create DynamoDB tables
1. AWS Console → **DynamoDB** → **Tables** → **Create table**
2. Create `patients`:
	- Partition key: `patient_id` (String)
3. Create `medications`:
	- Partition key: `patient_id` (String)
	- Sort key: `medication_id` (String)
4. Create `sessions`:
	- Partition key: `patient_id` (String)
	- Sort key: `session_id` (String)
5. Keep **Capacity mode = On-demand** for MVP

### C. Create API Gateway for backend
1. AWS Console → **API Gateway**
2. Click **Create API** under **HTTP API**
3. Click **Build**
4. **Add integration** → choose Lambda → select `medication-backend-api`
5. In **Configure routes**:
	- Add route `ANY /{proxy+}`
	- Add route `ANY /`
6. Continue with default stage (for example `$default`)
7. Click **Create**
8. Copy **Invoke URL** from API details

### D. Smoke test backend URL
1. Open **CloudShell** (or use local terminal)
2. Run:
	- `curl <invoke-url>/`
	- `curl <invoke-url>/patients`
3. Confirm JSON responses

### E. Create Alexa skill Lambda (`medication-alexa-skill`)
1. AWS Console → **Lambda** → **Create function**
2. Name: `medication-alexa-skill`
3. Runtime: `Node.js 18.x` (or 20.x)
4. Create function
5. Upload `skill_lambda.zip`
6. Runtime settings → Handler: `index.handler`
7. Environment variables:
	- `API_BASE_URL=<your-api-gateway-invoke-url>`

### F. Wire Alexa skill to Lambda
1. Alexa Developer Console → open your skill
2. **Build** tab → **Endpoint**
3. Select **AWS Lambda ARN**
4. Paste ARN for `medication-alexa-skill`
5. Click **Save Endpoints**
6. Go to **Interaction Model**
7. Click **Save Model** then **Build Model**

### G. Test in Alexa Console
1. **Test** tab → set mode to **Development**
2. Try:
	- `open medication check`
	- `my identifier is 1234`
	- `i took my medicine`
3. If it fails, check logs:
	- CloudWatch log group for `medication-alexa-skill`
	- CloudWatch log group for `medication-backend-api`

---

## 8) Deploy Admin Dashboard on Streamlit via GitHub

This is the fastest way to host `admin_dashboard.py` for team access.

### A. Prepare repo (already added in this project)
- `admin_dashboard.py` is the app entrypoint
- `requirements.txt` includes `streamlit` and `requests`
- `.streamlit/config.toml` sets Streamlit server defaults
- `.streamlit/secrets.toml.example` shows required secret keys

### B. Push code to GitHub
From project root:

```powershell
git add .
git commit -m "Add Streamlit deployment config for admin dashboard"
git push origin <your-branch>
```

If this repository is not on GitHub yet:

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

### C. Deploy on Streamlit Community Cloud
1. Go to `https://share.streamlit.io/`
2. Sign in with GitHub
3. Click **Create app**
4. Select:
	- Repository: your repo
	- Branch: `main` (or deployment branch)
	- Main file path: `admin_dashboard.py`
5. Click **Advanced settings** and add Secrets:

```toml
API_URL = "https://807pdm6rih.execute-api.us-east-1.amazonaws.com"
```

6. Click **Deploy**

### D. Verify after deploy
1. Open the app URL from Streamlit Cloud
2. In **Patients** tab, click **Refresh Patient List**
3. Confirm data loads from your API Gateway backend

### E. Common fixes
- If app fails to start, confirm `requirements.txt` is in repo root
- If API calls fail, confirm `API_URL` in Streamlit Secrets matches API Gateway base URL
- If backend returns CORS/auth errors, validate API Gateway/Lambda configuration
