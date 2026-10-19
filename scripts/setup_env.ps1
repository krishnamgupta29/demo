<#
.SYNOPSIS
    DENTRACE Level 1 Environment Setup Script.
.DESCRIPTION
    Creates Python 3.11 virtual environment at C:\mini\.venv, installs pinned Level 1 dependencies,
    initializes directories on C:, and applies SQLite database migrations.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DENTRACE Level 1 — Environment Setup & Verification" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$WorkspaceRoot = "C:\mini"
$VenvPath = "C:\mini\.venv"
$PythonExe = "$VenvPath\Scripts\python.exe"

# 1. Verify Python 3.11 installation
Write-Host "`n[1/5] Verifying Python 3.11 runtime..." -ForegroundColor Yellow
try {
    $pyVersion = py -3.11 --version 2>&1
    Write-Host "Found Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Error "Python 3.11 (py -3.11) was not found on PATH. Please install Python 3.11.9."
}

# 2. Create or verify virtual environment
Write-Host "`n[2/5] Checking virtual environment at $VenvPath..." -ForegroundColor Yellow
if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating dedicated virtual environment..." -ForegroundColor Yellow
    py -3.11 -m venv $VenvPath
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# 3. Install pinned dependencies
Write-Host "`n[3/5] Installing Level 1 dependencies..." -ForegroundColor Yellow
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r "$WorkspaceRoot\requirements.txt"

# 4. Initialize storage directories
Write-Host "`n[4/5] Initializing local storage directories..." -ForegroundColor Yellow
$Directories = @(
    "$WorkspaceRoot\data\storage",
    "$WorkspaceRoot\data\previews",
    "$WorkspaceRoot\models\checkpoints",
    "$WorkspaceRoot\reports\generated"
)
foreach ($dir in $Directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Gray
    }
}

# 5. Apply database migrations
Write-Host "`n[5/5] Running SQLite schema migrations..." -ForegroundColor Yellow
& $PythonExe -c "from backend.database.migrations import run_migrations; print('Applied migrations:', run_migrations())"
& "$VenvPath\Scripts\alembic.exe" upgrade head

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host " Environment setup and database initialization complete!" -ForegroundColor Green
Write-Host " To start backend: .\scripts\start_backend.ps1" -ForegroundColor Cyan
Write-Host " To run tests:    .\scripts\run_tests.ps1" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Green
