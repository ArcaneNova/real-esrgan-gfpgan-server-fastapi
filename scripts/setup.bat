@echo off
REM Development setup script for Windows

echo 🚀 Setting up Image Upscaler SaaS development environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.9 or later.
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install Python dependencies
echo 📥 Installing Python dependencies...
pip install -r requirements.txt

REM Create environment file
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ⚠️ Please update .env file with your Cloudinary credentials
)

REM Create directories
echo 📁 Creating necessary directories...
if not exist models mkdir models
if not exist temp mkdir temp
if not exist logs mkdir logs

REM Download AI models
echo 🤖 Downloading AI models...
python -c "from utils.model_downloader import ensure_models_downloaded; ensure_models_downloaded('./models'); print('✅ Models downloaded successfully')"

echo ✅ Development environment setup complete!
echo.
echo 🔥 To start the development server:
echo 1. Start Redis: redis-server
echo 2. Start FastAPI: uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo 3. Start Celery workers:
echo    - Terminal 1: celery -A tasks worker --loglevel=info --concurrency=2 -Q esrgan -n esrgan@%%h
echo    - Terminal 2: celery -A tasks worker --loglevel=info --concurrency=2 -Q gfpgan -n gfpgan@%%h
echo.
echo 🌐 API will be available at: http://localhost:8000
echo 📚 API docs available at: http://localhost:8000/docs

pause
