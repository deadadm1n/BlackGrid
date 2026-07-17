@echo off
setlocal
cd /D "%~dp0"

set "LOG=logs\wrapper.log"
if not exist "%LOG%" (
    echo WatchDog log not found yet: %CD%\%LOG%
    pause
    exit /b 1
)

echo Showing the last 120 lines of %LOG%.
echo Press Ctrl+C to stop if using PowerShell tail mode.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -Path '%LOG%' -Tail 120 -Wait"
