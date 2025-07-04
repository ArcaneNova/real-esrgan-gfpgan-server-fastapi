# Railway Deployment Guide

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Cloudinary Account**: Sign up at [cloudinary.com](https://cloudinary.com)

## Environment Variables

Set these environment variables in your Railway project:

```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key  
CLOUDINARY_API_SECRET=your_api_secret
REDIS_BROKER=redis://localhost:6379/0
REDIS_BACKEND=redis://localhost:6379/0
ENVIRONMENT=production
MAX_WORKERS=2
MODEL_CACHE_DIR=/app/models
TEMP_DIR=/app/temp
```

## Deployment Steps

### Option 1: Railway CLI

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login to Railway:
```bash
railway login
```

3. Initialize project:
```bash
railway init
```

4. Set environment variables:
```bash
railway variables set CLOUDINARY_CLOUD_NAME=your_cloud_name
railway variables set CLOUDINARY_API_KEY=your_api_key
railway variables set CLOUDINARY_API_SECRET=your_api_secret
# ... set other variables
```

5. Deploy:
```bash
railway up
```

### Option 2: GitHub Integration

1. Push your code to GitHub
2. Connect your GitHub repository to Railway
3. Set environment variables in Railway dashboard
4. Deploy automatically on push

## Resource Requirements

- **RAM**: 4-8GB recommended
- **CPU**: 2-4 cores recommended
- **Storage**: 2-5GB for models and temp files
- **Network**: Good bandwidth for image uploads/downloads

## Monitoring

- Health check endpoint: `/health`
- Stats endpoint: `/stats`
- API documentation: `/docs`

## Performance Optimization

1. **Model Caching**: Models are downloaded once and cached
2. **Redis Queue**: Async processing with queue management
3. **Cloudinary**: Optimized image storage and delivery
4. **Supervisor**: Process management and auto-restart

## Troubleshooting

### Common Issues

1. **Models not downloading**: Check internet connection and disk space
2. **Redis connection failed**: Ensure Redis is running in container
3. **Out of memory**: Reduce concurrency or upgrade plan
4. **Slow processing**: Check GPU availability and model optimization

### Logs

View logs in Railway dashboard or use CLI:
```bash
railway logs
```

### Debug Mode

Set environment variable for debug logging:
```bash
PYTHONPATH=/app
DEBUG=true
```

## Scaling

Railway supports:
- Horizontal scaling (multiple instances)
- Vertical scaling (more CPU/RAM)
- Auto-scaling based on traffic

Configure in Railway dashboard under "Settings" > "Deploy".
