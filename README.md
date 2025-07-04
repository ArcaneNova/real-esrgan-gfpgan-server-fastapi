# Image Upscaler SaaS - Server API

A production-grade, real-time scalable image upscaler SaaS with Real-ESRGAN and GFPGAN APIs.

## Features

- 🔁 Celery queue system for async processing
- 🚀 FastAPI backend with high performance
- ⚡ Multiprocessing & multithreading support
- 🔗 Cloudinary integration for image storage
- 🧠 Optimized for under 8GB RAM / 4 Core servers
- ⏱ Target processing time: < 5 seconds per image

## Architecture

```
[Frontend Client] → [FastAPI Gateway] → [Redis Queue] → [Celery Workers]
                                                      ↓
                    [Real-ESRGAN Worker] ← → [GFPGAN Worker]
                                                      ↓
                                        [Cloudinary Storage]
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
REDIS_BROKER=redis://localhost:6379/0
REDIS_BACKEND=redis://localhost:6379/0
```

3. Download AI models (automatically handled on first run)

4. Start Redis server:
```bash
redis-server
```

5. Start FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

6. Start Celery workers:
```bash
# Terminal 1 - Real-ESRGAN Worker
celery -A tasks worker --loglevel=info --concurrency=2 -Q esrgan -n esrgan@%h

# Terminal 2 - GFPGAN Worker  
celery -A tasks worker --loglevel=info --concurrency=2 -Q gfpgan -n gfpgan@%h
```

## API Endpoints

- `POST /upscale` - Upscale image using Real-ESRGAN
- `POST /face-enhance` - Enhance faces using GFPGAN
- `GET /result/{task_id}` - Get processing result
- `GET /health` - Health check

## Docker Deployment

Use the provided Dockerfile for containerized deployment on Railway or any cloud platform.
