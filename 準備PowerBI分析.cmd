@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m powerbi.local_workflow prepare
pause
