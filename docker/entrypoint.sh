#!/bin/bash
set -e

echo "Starting Image Upscaler SaaS..."

# Create log directory
mkdir -p /app/logs

# Wait for Redis to be ready
echo "Starting Redis server..."
redis-server --daemonize yes --bind 0.0.0.0 --port 6379

# Wait a moment for Redis to start
sleep 2

# Test Redis connection
until redis-cli ping; do
  echo "Waiting for Redis..."
  sleep 1
done

echo "Redis is ready!"

# Download AI models if not present
echo "Checking AI models..."
python -c "
from utils.model_downloader import ensure_models_downloaded
from config import settings
import logging
logging.basicConfig(level=logging.INFO)
ensure_models_downloaded(settings.model_cache_dir)
print('Models check completed')
"

echo "Starting services with supervisor..."

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
