$ErrorActionPreference = "Stop"

# Config
$REPO_NAME = "carbmate-backend"
$GITHUB_USER = "RyzaHacks"
$RENDER_API_KEY = "rnd_uJKhkz1b5GtVcFayELAq0dYOJjMk"

# API Endpoints
$CREATE_SERVICE_URL = "https://api.render.com/v1/services"
$DEPLOY_SERVICE_URL = "https://api.render.com/v1/services/carbmate-backend/deploys"

# Ensure correct directory
Set-Location "C:\Users\ryanm\Desktop\carbmate\backend"

# Install GitHub CLI if missing
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Write-Host "Installing GitHub CLI..."
  winget install GitHub.cli --accept-source-agreements --accept-package-agreements
}

# Authenticate GitHub
Write-Host "Authenticating GitHub..."
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  gh auth login --hostname github.com
}

# Ensure GitHub repo exists
Write-Host "Preparing GitHub repo..."
$repoCheck = gh repo view "$GITHUB_USER/$REPO_NAME" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "Creating GitHub repo..."
  gh repo create "$REPO_NAME" --public --confirm
}

# Bind remote URL and push
$env:REPO_URL = "https://github.com/$GITHUB_USER/$REPO_NAME.git"

Write-Host "Rebinding Git remote..."
git remote remove origin 2>$null | Out-Null
git branch -M main 2>$null | Out-Null
git remote add origin $env:REPO_URL

Write-Host "Committing & pushing code..."
git add .
git config user.name "Ryan Murray"
git config user.email "ryanm@example.dev"
git commit -m "Initial CarbMate backend deploy" 2>$null | Out-Null
git push -u origin main

# Create Render Web Service via API
Write-Host "Creating Render Web Service via API..."

$renderPayload = @{
  "type" = "web_service"
  "name" = "carbmate-backend"
  "repo" = "$GITHUB_USER/$REPO_NAME"
  "branch" = "main"
  "runtime" = "python"
  "region" = "oregon"
  "buildCommand" = "pip install -r requirements.txt"
  "startCommand" = "uvicorn app:app --host 0.0.0.0 --port 8080"
  "healthCheckPath" = "/health"
  "autoDeploy" = $true
}

$renderJson = $renderPayload | ConvertTo-Json -Depth 6 -Compress

curl.exe -sS -X POST $CREATE_SERVICE_URL `
  -H "Authorization: Bearer $RENDER_API_KEY" `
  -H "Content-Type: application/json" `
  -d $renderJson | Out-File -Encoding utf8 render_service_response.json

Write-Host "Render service created ✔"

# Trigger first deploy
Write-Host "Triggering first deploy..."
Invoke-RestMethod -Uri $DEPLOY_SERVICE_URL -Method Post -Headers @{
  Authorization = "Bearer $RENDER_API_KEY"
  "Content-Type" = "application/json"
} -Body "{}"

Write-Host "Deployment started ✔"
Write-Host "Done!"
