#requires -Version 5.1
<#
.SYNOPSIS
  Tea-Guide smoke pre-check (detect only, does NOT auto-start services)

.DESCRIPTION
  Checks backend :8000, frontend :5173, and the frontend /api proxy.
  Exit 0 when all pass (then follow scripts/SMOKE_CHECKLIST.md).
  Exit 1 and print start instructions when any check fails.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_smoke_env.ps1
#>

$ErrorActionPreference = 'Stop'
$Backend  = 'http://127.0.0.1:8000'
$Frontend = 'http://127.0.0.1:5173'
$failed = 0

function Test-Url {
    param([string]$Name, [string]$Url)
    try {
        $code = (Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5).StatusCode
        Write-Host "[OK]   $Name -> $Url (HTTP $code)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[FAIL] $Name -> $Url not responding" -ForegroundColor Red
        return $false
    }
}

Write-Host "== Smoke pre-check ==" -ForegroundColor Cyan
if (-not (Test-Url 'Backend health' "$Backend/api/v1/health")) { $failed++ }
if (-not (Test-Url 'Frontend home' "$Frontend/")) { $failed++ }
if (-not (Test-Url 'Frontend proxy' "$Frontend/api/v1/health")) { $failed++ }

if ($failed -gt 0) {
    Write-Host "`nPre-check FAILED ($failed item(s)). Start services in two terminals, then re-run:" -ForegroundColor Yellow
    Write-Host "  Terminal A (backend):  cd backend; python run.py    # :8000" -ForegroundColor Yellow
    Write-Host "  Terminal B (frontend): cd frontend; npm run dev     # :5173, proxies /api and /uploads" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nEnvironment ready. Open scripts/SMOKE_CHECKLIST.md and verify each item." -ForegroundColor Green
exit 0
