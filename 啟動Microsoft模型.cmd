@echo off
cd /d "%~dp0"
set "ARBOR_MODEL_PYTHON=%USERPROFILE%\.cache\arbor3d\foundry-venv\Scripts\python.exe"
if not exist "%ARBOR_MODEL_PYTHON%" (
  echo Foundry Local SDK environment is missing. See docs/microsoft/LIVE_CONNECTIONS.md
  pause
  exit /b 1
)
"%ARBOR_MODEL_PYTHON%" -u scripts/run_foundry_local.py
pause
