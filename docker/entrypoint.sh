#!/bin/bash
set -e

echo "🚀 Starting Image Upscaler SaaS..."

# Create log directory with proper permissions
mkdir -p /app/logs
chmod 755 /app/logs

# Start Redis server in background
echo "📡 Starting Redis server..."
redis-server --daemonize yes --bind 0.0.0.0 --port 6379 --save "" --dir /app/temp

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
until redis-cli ping >/dev/null 2>&1; do
  echo "  Redis not ready, waiting..."
  sleep 1
done
echo "✅ Redis is ready!"

# Download AI models if not present
echo "🤖 Checking AI models..."
python -c "
from utils.model_downloader import ensure_models_downloaded
from config import settings
import logging
logging.basicConfig(level=logging.INFO)
try:
    success = ensure_models_downloaded(settings.model_cache_dir)
    if success:
        print('✅ All models ready')
    else:
        print('⚠️ Some models failed to download, but continuing...')
except Exception as e:
    print(f'⚠️ Model download error: {e}, but continuing...')
"

echo "🚀 Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &
FASTAPI_PID=$!

echo "🤖 Starting Celery workers..."
celery -A tasks worker --loglevel=info --concurrency=1 -Q esrgan -n esrgan@%h &
ESRGAN_PID=$!

celery -A tasks worker --loglevel=info --concurrency=1 -Q gfpgan -n gfpgan@%h &
GFPGAN_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $FASTAPI_PID $ESRGAN_PID $GFPGAN_PID 2>/dev/null
    redis-cli shutdown
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGTERM SIGINT

echo "✅ All services started successfully!"
echo "🌐 API available at: http://0.0.0.0:8000"
echo "❤️ Health check: http://0.0.0.0:8000/health"

# Wait for all background processes
wait
