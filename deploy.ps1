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

# GitHub CLI check
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

# Git repo setup
Write-Host "Preparing GitHub repo..."
$repoExists = gh repo view "$GITHUB_USER/$REPO_NAME" 2>&1
if ($repoExists -match "not found") {
  gh repo create "$REPO_NAME" --public --confirm
}

# Set remote URL
$env:REPO_URL = "https://github.com/$GITHUB_USER/$REPO_NAME.git"
git remote remove origin 2>$null | Out-Null
git branch -M main 2>$null | Out-Null
git remote add origin $env:REPO_URL

# Commit + push
Write-Host "Committing & pushing code..."
git add .
git config user.name "Ryan Murray"
git config user.email "ryanm@example.dev"
git commit -m "Initial CarbMate backend deploy" 2>$null | Out-Null
git push -u origin main

# Render service creation payload (NO CLI FLAGS)
Write-Host "Creating Render Web Service..."
$renderPayload = @{
  type = "web_service"
  name = "carbmate-backend"
  repo = "$GITHUB_USER/$REPO_NAME"
  branch = "main"
  runtime = "python"
  region = "oregon"
  buildCommand = "pip install -r requirements.txt"
  startCommand = "uvicorn app:app"
  healthCheckPath = "/health"
  autoDeploy = $true
}

# Call Render API to create service
Invoke-RestMethod -Uri $CREATE_SERVICE_URL -Method Post -Headers @{
  Authorization = "Bearer $RENDER_API_KEY"
  "Content-Type" = "application/json"
} -Body ($renderPayload | ConvertTo-Json -Depth 6) | Out-File -Encoding utf8 render_service_response.json

Write-Host "Render service created ✔"

# Trigger deploy
Write-Host "Triggering deployment..."
Invoke-RestMethod -Uri $DEPLOY_SERVICE_URL -Method Post -Headers @{
  Authorization = "Bearer $RENDER_API_KEY"
  "Content-Type" = "application/json"
} -Body "{}"

Write-Host "Deployment started ✔"
Write-Host "Done!"
