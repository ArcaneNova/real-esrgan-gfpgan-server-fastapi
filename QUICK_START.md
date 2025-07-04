# 🚀 Quick Start Guide - Image Upscaler SaaS

## ⚡ Overview

This is a **production-grade, real-time scalable image upscaler SaaS** with:

- 🤖 **Real-ESRGAN** - 4x image upscaling
- 😀 **GFPGAN** - Face enhancement and restoration  
- 🔁 **Celery** - Async task queue system
- 🚀 **FastAPI** - High-performance API backend
- ⚡ **Redis** - Fast message broker
- 🔗 **Cloudinary** - Image storage and CDN
- 🐳 **Docker** - Containerized deployment
- 🚂 **Railway** - Cloud deployment ready

## 🏗️ Architecture

```
Frontend → FastAPI Gateway → Redis Queue → Celery Workers → AI Models → Cloudinary
```

## 🎯 Performance Targets

- ⏱️ **< 5 seconds** per image processing
- 🧠 **< 8GB RAM** server requirement
- 💻 **4 Core CPU** optimization
- 📈 **Horizontally scalable**

## 🚀 Quick Start (Development)

### Prerequisites

- Python 3.9+
- Redis Server
- Git

### Windows Setup

```powershell
# 1. Clone and navigate
cd path\to\your\projects
git clone <your-repo>
cd image-upscaler\server-api

# 2. Run setup script
.\scripts\setup.bat

# 3. Update environment
# Edit .env file with your Cloudinary credentials

# 4. Start all services
.\scripts\start-dev.bat
```

### Linux/macOS Setup

```bash
# 1. Clone and navigate
cd /path/to/your/projects
git clone <your-repo>
cd image-upscaler/server-api

# 2. Run setup script
chmod +x scripts/*.sh
./scripts/setup.sh

# 3. Update environment
# Edit .env file with your Cloudinary credentials

# 4. Start all services
./scripts/start-dev.sh
```

### Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your settings

# 4. Create directories
mkdir -p models temp logs

# 5. Start Redis
redis-server

# 6. Start FastAPI (Terminal 1)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 7. Start Real-ESRGAN Worker (Terminal 2)
celery -A tasks worker --loglevel=info --concurrency=2 -Q esrgan -n esrgan@%h

# 8. Start GFPGAN Worker (Terminal 3)
celery -A tasks worker --loglevel=info --concurrency=2 -Q gfpgan -n gfpgan@%h
```

## 🌐 Access Points

Once running:

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Stats**: http://localhost:8000/stats

## 🧪 Test the API

```bash
# Test with Python script
python scripts/test_api.py --upscale path/to/image.jpg

# Test with curl
curl -X POST "http://localhost:8000/upscale" \
  -F "file=@test_image.jpg" \
  -F "format=webp"

# Get result
curl "http://localhost:8000/result/TASK_ID_HERE"
```

## ☁️ Deploy to Railway

### Prerequisites

1. **Railway Account**: [railway.app](https://railway.app)
2. **Cloudinary Account**: [cloudinary.com](https://cloudinary.com)

### Deploy Steps

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set CLOUDINARY_CLOUD_NAME=your_cloud_name
railway variables set CLOUDINARY_API_KEY=your_api_key
railway variables set CLOUDINARY_API_SECRET=your_api_secret

# 5. Deploy
railway up
```

### Alternative: GitHub Deploy

1. Push code to GitHub
2. Connect GitHub repo to Railway
3. Set environment variables in Railway dashboard
4. Deploy automatically

## 📋 Environment Variables

**Required:**
```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Optional:**
```bash
REDIS_BROKER=redis://localhost:6379/0
REDIS_BACKEND=redis://localhost:6379/0
ENVIRONMENT=production
MAX_WORKERS=4
MODEL_CACHE_DIR=/app/models
TEMP_DIR=/app/temp
```

## 🔧 Configuration

### Performance Tuning

**Low Resource (2GB RAM, 1 CPU):**
```bash
MAX_WORKERS=1
MAX_CONCURRENT_TASKS=2
```

**Medium Resource (4GB RAM, 2 CPU):**
```bash
MAX_WORKERS=2
MAX_CONCURRENT_TASKS=5
```

**High Resource (8GB RAM, 4 CPU):**
```bash
MAX_WORKERS=4
MAX_CONCURRENT_TASKS=10
```

### Model Configuration

Edit `utils/model_downloader.py` to:
- Add new models
- Change download URLs
- Modify model parameters

## 📊 Monitoring

### Built-in Monitoring

```bash
# Real-time monitoring
python scripts/monitor.py

# One-time check
python scripts/monitor.py --once

# Custom monitoring
python scripts/monitor.py --interval 30 --duration 3600
```

### Key Metrics

- CPU usage < 80%
- Memory usage < 80%
- Processing time < 5s
- Queue length < 10

## 🚨 Troubleshooting

### Common Issues

**Models not downloading:**
```bash
# Check internet connection and disk space
python -c "from utils.model_downloader import ensure_models_downloaded; ensure_models_downloaded('./models')"
```

**Redis connection failed:**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

**Out of memory:**
```bash
# Reduce concurrency
export MAX_WORKERS=1
export MAX_CONCURRENT_TASKS=2
```

**Slow processing:**
```bash
# Check GPU availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
export PYTHONPATH=/app

# View detailed logs
tail -f logs/*.log
```

## 📚 Documentation

- **API Docs**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Railway Deploy**: [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- **Architecture**: [README.md](README.md)

## 🔗 Useful Commands

```bash
# Check API health
curl http://localhost:8000/health

# View active tasks
curl http://localhost:8000/tasks/active

# Get system stats
curl http://localhost:8000/stats

# Clear GPU cache
curl -X POST http://localhost:8000/admin/clear-cache

# Monitor Celery workers
celery -A tasks inspect active

# View Redis queue
redis-cli monitor
```

## 🆘 Support

If you encounter issues:

1. Check logs in `logs/` directory
2. Verify environment variables in `.env`
3. Test Redis connection: `redis-cli ping`
4. Check disk space for models
5. Monitor system resources

## 🎉 Success!

If everything is working:

- ✅ Health check returns "healthy"
- ✅ Models downloaded successfully  
- ✅ Redis responds to ping
- ✅ Workers processing tasks
- ✅ Images uploaded to Cloudinary

Your **Image Upscaler SaaS** is ready for production! 🚀
