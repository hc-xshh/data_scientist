# Startup script for all services
# Use Windows Terminal to open three tabs for three services

$scriptPath = "$PSScriptRoot\.scripts"

# Start Windows Terminal with three tabs running batch files
wt --title "LangGraph Backend" cmd /k "$scriptPath\start_langgraph.bat" `;  new-tab --title "Frontend" cmd /k "$scriptPath\start_frontend.bat" `; new-tab --title "File Service" cmd /k "$scriptPath\start_fileservice.bat"

Write-Host "All services started successfully!" -ForegroundColor Green
