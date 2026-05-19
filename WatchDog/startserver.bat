@echo off
setlocal

cd /D "%~dp0"

echo Checking for leftover ATM11 server processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$root = (Resolve-Path '%~dp0atm11').Path; " ^
    "$matches = Get-CimInstance Win32_Process | Where-Object { " ^
    "    $_.Name -match '^javaw?\.exe$' -and $_.CommandLine -and ( " ^
    "        $_.CommandLine -like ('*' + $root + '*') -or " ^
    "        ($_.CommandLine -like '*neoforge*' -and $_.CommandLine -like '*26.1.2.48-beta*') " ^
    "    ) " ^
    "}; " ^
    "foreach ($process in $matches) { " ^
    "    Write-Host ('Stopping leftover ATM11 process PID ' + $process.ProcessId); " ^
    "    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue " ^
    "}"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" main.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Watchdog exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
