param(
    [string]$FunctionName = "medication-backend-api",
    [string]$Region = "us-east-1",
    [string]$ApiHealthUrl = "https://807pdm6rih.execute-api.us-east-1.amazonaws.com/",
    [string]$RequirementsFile = "requirements.lambda.txt",
    [bool]$IncludeLocalData = $false
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

$pythonExe = Join-Path $root ".venv/Scripts/python.exe"
$pipExe = Join-Path $root ".venv/Scripts/pip.exe"
if (!(Test-Path $pythonExe) -or !(Test-Path $pipExe)) {
    throw "Python venv not found. Expected at .venv/Scripts"
}

$buildDir = Join-Path $root ".deploy_tmp/backend_build"
$zipPath = Join-Path $root "backend_lambda.zip"

if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $buildDir | Out-Null

Write-Host "Installing Linux-compatible backend dependencies..."
& $pipExe install --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: -r $RequirementsFile -t $buildDir --upgrade

Write-Host "Copying backend source files..."
Copy-Item "main.py","handler.py","data_models.py","data_storage.py","data_storage_dynamodb.py" $buildDir -Force
if ($IncludeLocalData -and (Test-Path "data")) {
    Copy-Item "data" $buildDir -Recurse -Force
}

Write-Host "Pruning unnecessary package artifacts..."
Get-ChildItem -Path $buildDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $buildDir -Recurse -File -Include "*.pyc","*.pyo" | Remove-Item -Force
Get-ChildItem -Path $buildDir -Recurse -Directory -Include "tests","test","docs","examples","bin" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $buildDir -Recurse -Directory -Filter "*.dist-info" | Remove-Item -Recurse -Force

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Packaging backend zip..."
Compress-Archive -Path "$buildDir/*" -DestinationPath $zipPath -Force

Write-Host "Deploying $FunctionName to $Region..."
$lastModified = aws lambda update-function-code --function-name $FunctionName --zip-file fileb://backend_lambda.zip --region $Region --query "LastModified" --output text
aws lambda wait function-updated --function-name $FunctionName --region $Region

Write-Host "Deploy complete. LastModified: $lastModified"

Write-Host "Checking API health..."
$health = Invoke-WebRequest -Uri $ApiHealthUrl -UseBasicParsing
Write-Host "Health response:"
$health.Content
