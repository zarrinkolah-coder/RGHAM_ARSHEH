@echo off
setlocal
cd /d "%~dp0"
if "%RAGHAM_HOST%"=="" set RAGHAM_HOST=0.0.0.0
if "%RAGHAM_PORT%"=="" set RAGHAM_PORT=8080
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 server.py
) else (
  python server.py
)
pause
