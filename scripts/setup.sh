#!/bin/bash

# Development setup script for Image Upscaler SaaS

set -e

echo "🚀 Setting up Image Upscaler SaaS development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or later."
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis is not installed. Installing Redis..."
    
    # Install Redis based on OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install redis
    else
        echo "❌ Please install Redis manually for your OS"
        exit 1
    fi
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Create environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your Cloudinary credentials"
fi

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p models temp logs

# Download AI models
echo "🤖 Downloading AI models..."
python -c "
from utils.model_downloader import ensure_models_downloaded
ensure_models_downloaded('./models')
print('✅ Models downloaded successfully')
"

echo "✅ Development environment setup complete!"
echo ""
echo "🔥 To start the development server:"
echo "1. Start Redis: redis-server"
echo "2. Start FastAPI: uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "3. Start Celery workers:"
echo "   - Terminal 1: celery -A tasks worker --loglevel=info --concurrency=2 -Q esrgan -n esrgan@%h"
echo "   - Terminal 2: celery -A tasks worker --loglevel=info --concurrency=2 -Q gfpgan -n gfpgan@%h"
echo ""
echo "🌐 API will be available at: http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
