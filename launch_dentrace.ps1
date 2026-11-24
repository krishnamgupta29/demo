# DENTRACE Desktop Launcher — PowerShell Script
# Enforces Python 3.11 selection and initiates preflight verification.

$Host.UI.RawUI.WindowTitle = "DENTRACE - Clinical Decision Support Engine"

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "  DENTRACE: Clinical Decision Support Engine Launcher" -ForegroundColor Cyan
Write-Host "  Regulatory Notice: Draft for dentist review. Not a diagnosis." -ForegroundColor Yellow
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Locate Python 3.11
$PythonExe = $null

if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonExe = "$ScriptDir\.venv\Scripts\python.exe"
} else {
    try {
        $testPy = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($testPy) { $PythonExe = $testPy.Trim() }
    } catch {}
    if (-not $PythonExe) {
        try {
            $testPy2 = & python -c "import sys; print(sys.executable if sys.version_info.major==3 and sys.version_info.minor==11 else '')" 2>$null
            if ($testPy2) { $PythonExe = $testPy2.Trim() }
        } catch {}
    }
    if (-not $PythonExe) {
        if (Test-Path "D:\mini\.venv\Scripts\python.exe") {
            $PythonExe = "D:\mini\.venv\Scripts\python.exe"
        } elseif (Test-Path "C:\mini\.venv\Scripts\python.exe") {
            $PythonExe = "C:\mini\.venv\Scripts\python.exe"
        }
    }
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Python 3.11 runtime could not be resolved." -ForegroundColor Red
    Write-Host "[HINT] Please ensure Python 3.11.9 is installed." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "[*] Selected Python interpreter: $PythonExe" -ForegroundColor Green
Write-Host "[*] Executing DENTRACE Desktop Launcher..." -ForegroundColor Cyan
Write-Host ""

& $PythonExe "$ScriptDir\scripts\launcher\launcher.py"
