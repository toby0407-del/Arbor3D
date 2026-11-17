@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\docker-start.ps1" %*
pause
