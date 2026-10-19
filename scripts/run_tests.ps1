<#
.SYNOPSIS
    DENTRACE Automated QA & Test Execution Runner.
.DESCRIPTION
    Executes the full Level 1 test suite using pytest and displays formatted results.
#>

[CmdletBinding()]
param(
    [switch]$Detailed = $true
)

$ErrorActionPreference = "Continue"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DENTRACE Level 1 -- Automated QA Test Suite" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$WorkspaceRoot = "C:\mini"
$VenvPath = "C:\mini\.venv"
$PytestExe = "$VenvPath\Scripts\pytest.exe"

if (-not (Test-Path $PytestExe)) {
    Write-Error "pytest not found at $PytestExe. Run .\scripts\setup_env.ps1 first."
    exit 1
}

$env:PYTHONPATH = $WorkspaceRoot
Set-Location $WorkspaceRoot

$testArgs = @("-v", "--tb=short")
if (-not $Detailed) {
    $testArgs = @("-q")
}

& $PytestExe @testArgs
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host " ALL LEVEL 1 TESTS PASSED SUCCESSFULLY!" -ForegroundColor Green
} else {
    Write-Host " TEST RUN COMPLETED WITH FAILURES" -ForegroundColor Red
}
Write-Host "======================================================================" -ForegroundColor Cyan

exit $exitCode
