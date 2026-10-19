# Starts Offer Letter: builds the web app, starts the server, opens it in your browser.
# Usage:  .\start.ps1                 (real teammates on your Claude plan, your data in C:\Users\Owner\OfferLetter)
#         .\start.ps1 -Fake           (canned teammates: no plan usage, for a look around)
#         .\start.ps1 -DataHome D:\tmp\ol (a different data folder)
param(
    [switch]$Fake,
    [string]$DataHome = "",
    [int]$Port = 8765,
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Building the web app..."
Push-Location (Join-Path $repo "web")
try { pnpm build | Out-Null } finally { Pop-Location }

$serveArgs = @("run", "--project", (Join-Path $repo "server"), "offerletter", "serve", "--port", "$Port")
if ($DataHome) { $serveArgs += @("--home", $DataHome) }
if ($Fake) { $serveArgs += "--fake-teammates" }

Write-Host "Starting the server on http://127.0.0.1:$Port ..."
$server = Start-Process -FilePath "uv" -ArgumentList $serveArgs -PassThru -NoNewWindow

$ready = $false
for ($i = 0; $i -lt 120; $i++) {
    try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; $ready = $true; break }
    catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) { Write-Host "The server didn't start. Look at the messages above."; exit 1 }
if (-not $h.teammates) { Write-Host "Teammates are off: $($h.claude.message)" }

if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
Write-Host "Offer Letter is running. Close this window (or press Ctrl+C) to stop it."
Wait-Process -Id $server.Id
