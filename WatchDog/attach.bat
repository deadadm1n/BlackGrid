@echo off
setlocal
cd /D "%~dp0"

echo Windows batch cannot reattach to a console after it has been closed.
echo.
echo Use the WatchDog window that start-watchdog.bat opened, or inspect logs with:
echo   logs.bat
echo.
echo If you need real detach/reattach, run this server under Linux/WSL with tmux.
pause
