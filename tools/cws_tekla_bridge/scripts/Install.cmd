@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-CWS-Bridge.ps1"
if errorlevel 1 pause
