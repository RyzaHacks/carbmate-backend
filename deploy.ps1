$ErrorActionPreference = "Stop"

$REPO_NAME = "carbmate-backend"
$GITHUB_USER = "RyzaHacks"
$RENDER_API_KEY = "rnd_uJKhkz1b5GtVcFayELAq0dYOJjMk"
$RENDER_API = "https://api.render.com/v1/services"
$DEPLOY_API = "https://api.render.com/v1/services/carbmate-backend/deploys"

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

# Create GitHub repo if missing
Write-Host "Checking GitHub repo..."
gh repo view "$GITHUB_USER/$REPO_NAME" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Creating GitHub repo..."
  gh repo create "$REPO_NAME" --public --confirm
}

# Force-set repo URL and push
$env:REPO_URL = "https://github.com/$GITHUB_USER/$REPO_NAME.git"

Write-Host "Initializing Git..."
git init 2>$null
git branch -M main 2>$null
git remote remove origin 2>$null
git remote add origin $env:REPO_URL

Write-Host "Committing & pushing to GitHub..."
git add .
git config user.name "Ryan Murray"
git config user.email "ryanm@example.dev"
git commit -m "Initial CarbMate backend deploy" 2>$null
git push -u origin main

# Create Render service via API
Write-Host "Creating Render Web Service via API..."
$renderBody = @"
{
  "type": "web_service",
  "name": "carbmate-backend",
  "repo": "RyzaHacks/carbmate-backend",
  "branch": "main",
  "runtime": "python",
  "region": "oregon",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "uvicorn app:app --host 0.0.0.0 --port 8080",
  "healthCheckPath": "/health",
  "autoDeploy": true
}
"@

$service = curl.exe -sS -X POST $RENDER_API `
  -H "Authorization: Bearer $RENDER_API_KEY" `
  -H "Content-Type: application/json" `
  -d $renderBody

Write-Host "Service created on Render ✔"

# Trigger first deploy
Write-Host "Triggering first deploy..."
curl.exe -sS -X POST $DEPLOY_API `
  -H "Authorization: Bearer $RENDER_API_KEY" `
  -H "Content-Type: application/json" `
  -d "{}"

Write-Host "Deployment started ✔"
Write-Host "Done!"
