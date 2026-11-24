<#
.SYNOPSIS
    DENTRACE Level 5 Clinical Workstation PowerShell Launcher.
.DESCRIPTION
    Launches the complete offline local clinical system:
    1. Verifies Python 3.11 virtual environment and storage directories.
    2. Checks local Ollama instance on http://127.0.0.1:11434.
    3. Launches FastAPI backend on http://127.0.0.1:8000 in background process.
    4. Launches Streamlit Clinical Workstation on http://127.0.0.1:8501.
    5. Displays regulatory notices and zero cloud egress guarantees.
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 8501
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$VenvPath = "$ProjectRoot\.venv"
$PythonExe = "$VenvPath\Scripts\python.exe"
$StreamlitExe = "$VenvPath\Scripts\streamlit.exe"
$UvicornExe = "$VenvPath\Scripts\uvicorn.exe"

Clear-Host
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "       DENTRACE — CLINICAL DECISION-SUPPORT WORKSTATION (LEVEL 5)        " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " Notice: Draft for dentist review. Not a diagnosis." -ForegroundColor Yellow
Write-Host " Regulation: Academic Decision Support Prototype (Not FDA/CE/MDR Certified)" -ForegroundColor Yellow
Write-Host " Security: Zero Cloud Egress — Strictly Localhost 127.0.0.1" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Environment & Venv Validation
if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not detected at $VenvPath. Run scripts\setup_env.ps1 first."
}

# 2. Storage Directory Readiness
$StorageDirs = @(
    "$ProjectRoot\data\storage",
    "$ProjectRoot\data\previews",
    "$ProjectRoot\data\temp"
)
foreach ($dir in $StorageDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 3. Check Local Ollama Service
Write-Host "[1/3] Checking Ollama service on 127.0.0.1:11434..." -ForegroundColor Cyan
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction SilentlyContinue
    $hasModel = $ollamaCheck.models | Where-Object { $_.name -like "*qwen2.5:3b*" }
    if ($hasModel) {
        Write-Host "       Ollama active with model 'qwen2.5:3b'." -ForegroundColor Green
    } else {
        Write-Host "       Ollama active, but 'qwen2.5:3b' not detected in tags." -ForegroundColor Yellow
    }
} catch {
    Write-Host "       Ollama service not detected at 127.0.0.1:11434. Deterministic fallback will be active." -ForegroundColor Yellow
}

# 4. Launch FastAPI Core Backend (Background Job)
Write-Host "[2/3] Starting FastAPI Backend on http://${HostAddress}:${BackendPort}..." -ForegroundColor Cyan
$BackendJob = Start-Job -ScriptBlock {
    param($root, $uvicorn, $hostAddr, $port)
    $env:PYTHONPATH = $root
    Set-Location $root
    & $uvicorn backend.main:app --host $hostAddr --port $port
} -ArgumentList $ProjectRoot, $UvicornExe, $HostAddress, $BackendPort

Start-Sleep -Seconds 2

# 5. Launch Streamlit Clinical Workstation
Write-Host "[3/3] Launching Curie-Nordic Streamlit Workstation on http://${HostAddress}:${FrontendPort}..." -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to terminate both Frontend and Backend services." -ForegroundColor DarkGray
Write-Host ""

$env:PYTHONPATH = $ProjectRoot
Set-Location $ProjectRoot

try {
    & $StreamlitExe run "$ProjectRoot\frontend\app.py" --server.port $FrontendPort --server.address $HostAddress
} finally {
    Write-Host ""
    Write-Host "Shutting down background FastAPI backend process..." -ForegroundColor Yellow
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
    Write-Host "All DENTRACE services terminated cleanly." -ForegroundColor Cyan
}
