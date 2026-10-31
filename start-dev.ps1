# Next Basket — Development Startup Script
# Run this in PowerShell to start both backend and frontend

Write-Host "Starting Next Basket development servers..." -ForegroundColor Cyan

# Start backend
Write-Host "`n[1/2] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow
$backend = Start-Process -PassThru -WindowStyle Minimized -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory "e:\next_basket\backend"
Start-Sleep -Seconds 3
Write-Host "Backend: http://localhost:8000/docs" -ForegroundColor Green

# Start frontend
Write-Host "`n[2/2] Starting Vite frontend on port 5173..." -ForegroundColor Yellow
$frontend = Start-Process -PassThru -WindowStyle Minimized -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "e:\next_basket\frontend"
Start-Sleep -Seconds 3
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green

Write-Host "`nBoth servers running. Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "Admin login: admin / admin123" -ForegroundColor Gray

try {
    Wait-Process -Id $backend.Id
} finally {
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
}
