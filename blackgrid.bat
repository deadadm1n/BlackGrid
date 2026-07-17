@echo off
setlocal

cd /D "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" blackgrid.py %*
exit /b %ERRORLEVEL%
