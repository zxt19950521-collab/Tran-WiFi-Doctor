@echo off
setlocal
set PORT=17888
set PROXY=%USERPROFILE%\.claude\mimo-anthropic-proxy.py

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
  echo MiMo proxy already running on port %PORT% (PID %%P)
  goto run_claude
)

echo Starting MiMo anthropic proxy on port %PORT% ...
start "MiMo Proxy" /min python "%PROXY%"
timeout /t 2 /nobreak >nul

:run_claude
claude %*
