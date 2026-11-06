@echo off
title GlaciarSense - Monitoreo de Glaciares
echo ===================================================
echo   Iniciando GlaciarSense...
echo ===================================================

cd /d "%~dp0"

if exist ".\venv\Scripts\python.exe" (
    echo Usando entorno virtual: .\venv
    .\venv\Scripts\python.exe -m streamlit run app.py
) else (
    echo Usando Python del sistema...
    python -m streamlit run app.py
)

pause

