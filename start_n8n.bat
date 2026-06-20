@echo off
title n8n - ContactCenterCustomerService (port 5678)
REM n8n stores its data globally in %USERPROFILE%\.n8n by default.
REM To keep this project's n8n data isolated instead, the line below points it
REM at a local folder. Remove it if you prefer the shared global instance.
set N8N_USER_FOLDER=%~dp0n8n-data
if not exist "%N8N_USER_FOLDER%" mkdir "%N8N_USER_FOLDER%"
set N8N_DIAGNOSTICS_ENABLED=false
echo Starting n8n...  Open http://localhost:5678 once it says "n8n ready".
n8n start
