<#
.SYNOPSIS
    DENTRACE Level 1 Backend Server Launcher.
.DESCRIPTION
    Starts the FastAPI backend bound strictly to 127.0.0.1:8000 with auto-reload.
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DENTRACE Clinical Decision Support Engine — Backend Launcher" -ForegroundColor Cyan
Write-Host " Host: http://${HostAddress}:${Port}" -ForegroundColor Cyan
Write-Host " Notice: Draft for dentist review. Not a diagnosis." -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

$WorkspaceRoot = "C:\mini"
$VenvPath = "C:\mini\.venv"
$UvicornExe = "$VenvPath\Scripts\uvicorn.exe"

if (-not (Test-Path $UvicornExe)) {
    Write-Error "Virtual environment not found at $VenvPath. Run .\scripts\setup_env.ps1 first."
}

# Ensure storage directories exist
New-Item -ItemType Directory -Path "$WorkspaceRoot\data\storage", "$WorkspaceRoot\data\previews" -Force | Out-Null

# Set PYTHONPATH and launch server
$env:PYTHONPATH = $WorkspaceRoot
Set-Location $WorkspaceRoot

Write-Host "Starting Uvicorn development server on ${HostAddress}:${Port}..." -ForegroundColor Green
& $UvicornExe backend.main:app --host $HostAddress --port $Port --reload
