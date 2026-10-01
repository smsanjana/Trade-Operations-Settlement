# Backend startup script for Trade Operations & Settlement
param(
    [string]$ServerHost = "127.0.0.1",
    [int]$Port = 8000,
    [string]$EnvMode = "synthetic"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host "Starting Trade Operations & Settlement Backend ($EnvMode mode) on ${ServerHost}:${Port}..."

$env:TRADE_OPS_ENV = $EnvMode
$env:PYTHONPATH = (Join-Path $BackendDir "src")

$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPython)) {
    Write-Error "Python virtual environment not found. Please initialize .venv first."
    exit 1
}

Set-Location $BackendDir
& $VenvPython -m uvicorn trade_operations_settlement.api.main:app --host $ServerHost --port $Port
