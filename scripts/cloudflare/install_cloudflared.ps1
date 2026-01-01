$existing = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($null -eq $existing) {
    winget install --id Cloudflare.cloudflared -e
} else {
    Write-Output "cloudflared is already installed."
}
