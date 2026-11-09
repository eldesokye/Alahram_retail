# Quick Start Script for Al Ahram Retail Odoo 20
param(
    [switch]$Build,
    [switch]$Down,
    [switch]$Logs
)

$PSScriptRootLocation = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $PSScriptRootLocation

# Check if Docker on Windows is available
$useNativeDocker = $false
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        $useNativeDocker = $true
    }
} catch {
    $useNativeDocker = $false
}

if ($Down) {
    Write-Host "[*] Stopping Odoo services..." -ForegroundColor Yellow
    if ($useNativeDocker) {
        docker compose down
    } else {
        wsl -d Ubuntu bash -c "cd /mnt/d/WORK/Alahram_retail_odoo/Alahram_retail && docker compose down"
    }
    Write-Host "[+] Services stopped." -ForegroundColor Green
    exit 0
}

if ($Logs) {
    if ($useNativeDocker) {
        docker compose logs -f odoo
    } else {
        wsl -d Ubuntu bash -c "cd /mnt/d/WORK/Alahram_retail_odoo/Alahram_retail && docker compose logs -f odoo"
    }
    exit 0
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Al Ahram Retail Odoo 20 Enterprise Stack" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$composeCmd = "docker compose up -d"
if ($Build) {
    $composeCmd = "docker compose up -d --build"
}

if ($useNativeDocker) {
    Write-Host "[*] Using Windows Docker Desktop..." -ForegroundColor Gray
    Invoke-Expression $composeCmd
} else {
    Write-Host "[*] Docker Desktop not detected; running via WSL2 Ubuntu Docker..." -ForegroundColor Gray
    wsl -d Ubuntu bash -c "cd /mnt/d/WORK/Alahram_retail_odoo/Alahram_retail && $composeCmd"
}

Write-Host "`n[*] Waiting for Odoo to become healthy..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8071/web/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        # continue waiting
    }
}

if ($healthy) {
    Write-Host "`n[+] SUCCESS: Odoo 20 Enterprise is UP and ready!" -ForegroundColor Green
    Write-Host "----------------------------------------------------------"
    Write-Host " URL:             http://localhost:8071" -ForegroundColor Cyan
    Write-Host " Admin Password:  fIuBfIyOP3AFnoHk6zq6Kvil" -ForegroundColor Yellow
    Write-Host " DB Host/Port:    localhost:5432 / db:5432"
    Write-Host " DB User:         odoo"
    Write-Host " DB Name:         odoo20"
    Write-Host "----------------------------------------------------------"
} else {
    Write-Host "`n[!] Odoo is still starting up. Check status with: .\start-odoo.ps1 -Logs" -ForegroundColor Yellow
}

