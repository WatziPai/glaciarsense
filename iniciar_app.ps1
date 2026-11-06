# Script PowerShell para iniciar GlaciarSense
Set-Location -Path $PSScriptRoot

if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "Iniciando GlaciarSense con el entorno virtual .\venv..." -ForegroundColor Cyan
    & ".\venv\Scripts\python.exe" -m streamlit run app.py
} else {
    Write-Host "Iniciando GlaciarSense con Python del sistema..." -ForegroundColor Yellow
    python -m streamlit run app.py
}

