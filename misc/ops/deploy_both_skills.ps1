param(
    [string]$Region = "us-east-1",
    [string]$BackendFunction = "medication-backend-api",
    [string]$SkillFunction = "medication-alexa-skill",
    [switch]$SkipBackendBuild,
    [switch]$SkipSkillBuild,
    [switch]$SkipBackendDeploy,
    [switch]$SkipSkillDeploy
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = $PSScriptRoot
$tmpRoot = Join-Path $projectRoot ".deploy_tmp"
$backendBuildDir = Join-Path $tmpRoot "backend_build"
$backendZip = Join-Path $tmpRoot "backend_lambda.zip"
$skillDir = Join-Path $projectRoot "alexa-remote-api-skill\lambda\custom"
$skillZip = Join-Path $tmpRoot "skill_lambda.zip"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$lambdaRequirements = Join-Path $projectRoot "requirements.lambda.txt"
$requirementsFile = Join-Path $projectRoot "requirements.txt"
$backendPackages = @(
    "fastapi==0.115.8",
    "pydantic==2.10.6",
    "python-multipart==0.0.20",
    "boto3==1.36.26",
    "requests==2.32.3",
    "mangum==0.21.0"
)

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' not found in PATH."
    }
}

function Invoke-CheckedCommand([string]$Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

Write-Host "Validating prerequisites..." -ForegroundColor Cyan
Require-Command "aws"
Require-Command "npm"

$pythonCmd = "python"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
} else {
    Require-Command "python"
}

if (-not (Test-Path (Join-Path $skillDir "index.js"))) {
    throw "Alexa skill index.js not found at: $skillDir"
}

Write-Host "Preparing temp build directory..." -ForegroundColor Cyan
if (-not (Test-Path $tmpRoot)) {
    New-Item -ItemType Directory -Path $tmpRoot | Out-Null
}

if (-not $SkipBackendBuild) {
    if (Test-Path $backendBuildDir) {
        Remove-Item -Recurse -Force $backendBuildDir
    }
    New-Item -ItemType Directory -Path $backendBuildDir | Out-Null
}

if (-not $SkipBackendBuild) {
    Write-Host "Building backend package..." -ForegroundColor Cyan
    $requirementsForLambda = $null
    if (Test-Path $lambdaRequirements) {
        $requirementsForLambda = "requirements.lambda.txt"
    } elseif (Test-Path $requirementsFile) {
        $requirementsForLambda = "requirements.txt"
    }

    if ($requirementsForLambda) {
        Write-Host "Using dependency file: $requirementsForLambda" -ForegroundColor Cyan
    } else {
        Write-Host "No requirements file found. Using embedded backend dependency list." -ForegroundColor Yellow
    }

    $backendFiles = @(
        "main.py",
        "data_models.py",
        "data_storage.py",
        "data_storage_dynamodb.py",
        "handler.py"
    )

    if (Test-Path $lambdaRequirements) {
        $backendFiles += "requirements.lambda.txt"
    } elseif (Test-Path $requirementsFile) {
        $backendFiles += "requirements.txt"
    }

    foreach ($file in $backendFiles) {
        Copy-Item (Join-Path $projectRoot $file) $backendBuildDir -Force
    }

    Push-Location $projectRoot
    if ($requirementsForLambda) {
        Invoke-CheckedCommand $pythonCmd @("-m", "pip", "install", "-r", $requirementsForLambda, "-t", $backendBuildDir, "--upgrade")
    } else {
        $pipArgs = @("-m", "pip", "install", "-t", $backendBuildDir, "--upgrade") + $backendPackages
        Invoke-CheckedCommand $pythonCmd $pipArgs
    }
    Pop-Location

    Compress-Archive -Path (Join-Path $backendBuildDir "*") -DestinationPath $backendZip -Force
} else {
    Write-Host "Skipping backend build (using existing zip if available)..." -ForegroundColor Yellow
}

if (-not $SkipBackendDeploy) {
    if (-not (Test-Path $backendZip)) {
        throw "Backend zip not found: $backendZip. Run without -SkipBackendBuild first."
    }
    Write-Host "Deploying backend Lambda: $BackendFunction" -ForegroundColor Cyan
    Invoke-CheckedCommand "aws" @("lambda", "update-function-code", "--region", $Region, "--function-name", $BackendFunction, "--zip-file", "fileb://$backendZip")
} else {
    Write-Host "Skipping backend deploy." -ForegroundColor Yellow
}

if (-not $SkipSkillBuild) {
    Write-Host "Building Alexa skill package..." -ForegroundColor Cyan
    Push-Location $skillDir
    Invoke-CheckedCommand "npm" @("install")
    Compress-Archive -Path * -DestinationPath $skillZip -Force
    Pop-Location
} else {
    Write-Host "Skipping Alexa skill build (using existing zip if available)..." -ForegroundColor Yellow
}

if (-not $SkipSkillDeploy) {
    if (-not (Test-Path $skillZip)) {
        throw "Skill zip not found: $skillZip. Run without -SkipSkillBuild first."
    }
    Write-Host "Deploying Alexa skill Lambda: $SkillFunction" -ForegroundColor Cyan
    Invoke-CheckedCommand "aws" @("lambda", "update-function-code", "--region", $Region, "--function-name", $SkillFunction, "--zip-file", "fileb://$skillZip")
} else {
    Write-Host "Skipping Alexa skill deploy." -ForegroundColor Yellow
}

Write-Host "Cleaning temporary files..." -ForegroundColor Cyan
if (Test-Path $tmpRoot) {
    Remove-Item -Recurse -Force $tmpRoot
}

Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Backend: $BackendFunction | Skill: $SkillFunction | Region: $Region" -ForegroundColor Green
