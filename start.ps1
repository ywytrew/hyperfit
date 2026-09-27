param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Local environment missing. Follow README.md to create .venv and install requirements-lock.txt.'
}
Push-Location $PSScriptRoot
try {
    Write-Host "HyperFit: http://127.0.0.1:$Port  (Ctrl+C to stop)"
    & $pythonPath -B -m uvicorn hyperfit.api:app --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
}
