# Startup script for all services
# Use Windows Terminal to open two tabs for two services

$scriptPath = "$PSScriptRoot\.scripts"

# Start Windows Terminal with two tabs running batch files
wt --title "LangGraph Backend" cmd /k "$scriptPath\start_langgraph.bat" `;  new-tab --title "Frontend" cmd /k "$scriptPath\start_frontend.bat"

Write-Host "All services started successfully!" -ForegroundColor Green
