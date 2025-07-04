#!/bin/bash

# Start all services for development

set -e

echo "🚀 Starting Image Upscaler SaaS services..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Redis is running
if ! command_exists redis-cli || ! redis-cli ping >/dev/null 2>&1; then
    echo "🔴 Starting Redis server..."
    redis-server --daemonize yes --bind 127.0.0.1 --port 6379
    sleep 2
else
    echo "✅ Redis is already running"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Start services in background
echo "🚀 Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

echo "🤖 Starting Real-ESRGAN worker..."
celery -A tasks worker --loglevel=info --concurrency=1 -Q esrgan -n esrgan@%h &
ESRGAN_PID=$!

echo "😀 Starting GFPGAN worker..."
celery -A tasks worker --loglevel=info --concurrency=1 -Q gfpgan -n gfpgan@%h &
GFPGAN_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $FASTAPI_PID $ESRGAN_PID $GFPGAN_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

echo ""
echo "✅ All services started successfully!"
echo "🌐 API available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo "❤️  Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for all background processes
wait
