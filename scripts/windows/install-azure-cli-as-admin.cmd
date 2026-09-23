@echo off
REM Run this file as Administrator (right-click → 以系統管理員身分執行)
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-azure-cli.ps1"
pause
