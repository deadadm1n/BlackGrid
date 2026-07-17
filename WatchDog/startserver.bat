@echo off
setlocal

cd /D "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" main.py %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo WatchDog exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
