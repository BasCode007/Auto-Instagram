@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\comfyui\smoke_test.ps1 2>&1 | Tee-Object -FilePath smoke_report.txt }"
echo.
echo Report saved to smoke_report.txt in this folder. Press any key to close.
pause >nul
