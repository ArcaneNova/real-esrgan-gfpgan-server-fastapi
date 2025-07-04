@echo off
REM Start all services for development on Windows

echo 🚀 Starting Image Upscaler SaaS services...

REM Check if Redis is running
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo 🔴 Please start Redis server manually: redis-server
    echo Then run this script again.
    pause
    exit /b 1
) else (
    echo ✅ Redis is running
)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start FastAPI server
echo 🚀 Starting FastAPI server...
start "FastAPI Server" cmd /k "uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for FastAPI to start
timeout /t 3 /nobreak >nul

REM Start Celery workers
echo 🤖 Starting Real-ESRGAN worker...
start "Real-ESRGAN Worker" cmd /k "celery -A tasks worker --loglevel=info --concurrency=1 -Q esrgan -n esrgan@%%h"

echo 😀 Starting GFPGAN worker...
start "GFPGAN Worker" cmd /k "celery -A tasks worker --loglevel=info --concurrency=1 -Q gfpgan -n gfpgan@%%h"

echo.
echo ✅ All services started successfully!
echo 🌐 API available at: http://localhost:8000
echo 📚 API docs at: http://localhost:8000/docs
echo ❤️ Health check: http://localhost:8000/health
echo.
echo Press any key to exit...
pause
