@echo off
setlocal

cd /D "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" blackgrid_system_check.py
if errorlevel 1 (
    echo.
    echo BlackGrid system check failed. Fix the FAIL items above before running setup.
    pause
    exit /b 1
)

"%PYTHON%" blackgrid.py %*
exit /b %ERRORLEVEL%
