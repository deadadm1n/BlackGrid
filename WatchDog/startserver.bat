@echo off
setlocal

cd /D "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

set "PYTHON=.venv\Scripts\python.exe"

if not exist ".venv\blackgrid-ready" (
    "%PYTHON%" -m pip install --upgrade pip
    "%PYTHON%" -m pip install -r requirements.txt
    echo ready> .venv\blackgrid-ready
)

"%PYTHON%" main.py %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo WatchDog exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
