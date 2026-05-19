@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%remote-watchdog.ps1" %*
exit /b %ERRORLEVEL%
