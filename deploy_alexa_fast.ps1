param(
    [string]$FunctionName = "medication-alexa-skill",
    [string]$Region = "us-east-1",
    [string]$SkillPath = "2-alexa-remote-api-example-skill/lambda/custom",
    [string]$VerifyPayload = "invoke_payload.json"
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

$fullSkillPath = Join-Path $root $SkillPath
if (!(Test-Path $fullSkillPath)) {
    throw "Skill path not found: $fullSkillPath"
}

Set-Location $fullSkillPath

$zipPath = Join-Path $fullSkillPath "skill_lambda.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Packaging Alexa skill..."
Compress-Archive -Path "index.js","package.json","package-lock.json","node_modules" -DestinationPath $zipPath -Force

Write-Host "Deploying $FunctionName to $Region..."
$lastModified = aws lambda update-function-code --function-name $FunctionName --zip-file fileb://skill_lambda.zip --region $Region --query "LastModified" --output text
aws lambda wait function-updated --function-name $FunctionName --region $Region

Write-Host "Deploy complete. LastModified: $lastModified"

$payloadPath = Join-Path $fullSkillPath $VerifyPayload
if (Test-Path $payloadPath) {
    $outFile = Join-Path $fullSkillPath "out_verify.json"
    aws lambda invoke --function-name $FunctionName --payload fileb://$VerifyPayload --cli-binary-format raw-in-base64-out --region $Region $outFile | Out-Null
    Write-Host "Verification output:"
    Get-Content $outFile | Select-Object -First 1
} else {
    Write-Host "Verification payload not found at $payloadPath. Skipping invoke check."
}
