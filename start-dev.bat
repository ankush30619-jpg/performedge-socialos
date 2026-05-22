@echo off
echo Starting SocialOS Development Environment...
echo.

echo [1/3] Starting Fastify Backend (port 4000)...
start "SocialOS Backend" cmd /k "cd backend && npm run dev"

echo [2/3] Starting Python Agents Service (port 8000)...
start "SocialOS Agents" cmd /k "cd agents && python main.py"

echo [3/3] Starting Next.js Frontend (port 3000)...
start "SocialOS Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo All services starting...
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:4000
echo   Agents:    http://localhost:8000
echo.
pause
