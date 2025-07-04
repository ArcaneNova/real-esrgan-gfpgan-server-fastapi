from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from celery import Celery
from celery.result import AsyncResult
import os
import logging
from typing import Dict, Any, Optional, List
import time
from PIL import Image
import io

from config import settings
from utils import ensure_models_downloaded
from tasks import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for serialization errors
@app.exception_handler(UnicodeDecodeError)
async def unicode_decode_error_handler(request, exc):
    logger.error(f"Unicode decode error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error - data encoding issue"}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    if "cannot be serialized" in str(exc) or "json" in str(exc).lower():
        logger.error(f"JSON serialization error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error - data serialization issue"}
        )
    raise exc

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    error_msg = str(exc)
    if any(phrase in error_msg for phrase in [
        "utf-8 codec can't decode", 
        "UnicodeDecodeError",
        "cannot be serialized",
        "jsonable_encoder"
    ]):
        logger.error(f"Encoding/serialization error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error - data encoding/serialization issue"}
        )
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Global variables for tracking
startup_complete = False

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global startup_complete
    logger.info("Starting Image Upscaler SaaS API...")
    
    # Create necessary directories
    os.makedirs(settings.model_cache_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    
    # Download required models in background
    logger.info("Ensuring AI models are downloaded...")
    try:
        models_ready = ensure_models_downloaded(settings.model_cache_dir)
        if models_ready:
            logger.info("All AI models are ready")
        else:
            logger.warning("Some models failed to download. Check logs for details.")
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
    
    startup_complete = True
    logger.info("API startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Image Upscaler SaaS API...")

def validate_image(file: UploadFile) -> bool:
    """Validate uploaded image file."""
    # Check file size
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size // (1024*1024)}MB"
        )
    
    # Check file format
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    return True

async def get_image_info(file: UploadFile) -> Dict[str, Any]:
    """Get basic information about the uploaded image."""
    try:
        contents = await file.read()
        await file.seek(0)  # Reset file pointer
        
        image = Image.open(io.BytesIO(contents))
        return {
            "filename": file.filename,
            "size": file.size,
            "dimensions": image.size,
            "mode": image.mode,
            "format": image.format
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Image Upscaler SaaS API",
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "startup_complete": startup_complete,
        "timestamp": time.time(),
        "version": settings.api_version
    }

@app.post("/upscale")
async def upscale_image_endpoint(
    file: UploadFile = File(..., description="Image file to upscale"),
    format: str = "webp",
    quality: str = "auto"
):
    """
    Upscale an image using Real-ESRGAN.
    
    - **file**: Image file (JPEG, PNG, WebP)
    - **format**: Output format (webp, png, jpeg)
    - **quality**: Output quality (auto, high, medium, low)
    """
    # Validate input
    validate_image(file)
    
    if format not in ["webp", "png", "jpeg", "jpg"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use: webp, png, jpeg")
    
    try:
        # Get image info
        image_info = await get_image_info(file)
        logger.info(f"Received upscale request: {image_info}")
        
        # Read file contents
        contents = await file.read()
        
        # Create task options
        options = {
            "format": format,
            "quality": quality
        }
        
        # Send task to Celery
        task = celery_app.send_task(
            "tasks.upscale_esrgan",
            args=[contents, file.filename, options],
            queue="esrgan"
        )
        
        logger.info(f"Created upscale task: {task.id}")
        
        return {
            "success": True,
            "task_id": task.id,
            "status": "queued",
            "message": "Image upscaling started",
            "image_info": image_info,
            "options": options,
            "estimated_time": "2-5 seconds"
        }
        
    except Exception as e:
        logger.error(f"Upscale endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/face-enhance")
async def enhance_face_endpoint(
    file: UploadFile = File(..., description="Image file with faces to enhance"),
    format: str = "webp",
    quality: str = "auto",
    only_center_face: bool = False
):
    """
    Enhance faces in an image using GFPGAN.
    
    - **file**: Image file containing faces (JPEG, PNG, WebP)
    - **format**: Output format (webp, png, jpeg)
    - **quality**: Output quality (auto, high, medium, low)
    - **only_center_face**: Only enhance the center face if multiple faces detected
    """
    # Validate input
    validate_image(file)
    
    if format not in ["webp", "png", "jpeg", "jpg"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use: webp, png, jpeg")
    
    try:
        # Get image info
        image_info = await get_image_info(file)
        logger.info(f"Received face enhance request: {image_info}")
        
        # Read file contents
        contents = await file.read()
        
        # Create task options
        options = {
            "format": format,
            "quality": quality,
            "only_center_face": only_center_face
        }
        
        # Send task to Celery
        task = celery_app.send_task(
            "tasks.enhance_gfpgan",
            args=[contents, file.filename, options],
            queue="gfpgan"
        )
        
        logger.info(f"Created face enhance task: {task.id}")
        
        return {
            "success": True,
            "task_id": task.id,
            "status": "queued",
            "message": "Face enhancement started",
            "image_info": image_info,
            "options": options,
            "estimated_time": "3-8 seconds"
        }
        
    except Exception as e:
        logger.error(f"Face enhance endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """
    Get the result of a processing task.
    
    - **task_id**: The task ID returned from upscale or face-enhance endpoints
    """
    try:
        # Get task result from Celery
        result = AsyncResult(task_id, app=celery_app)
        
        if result.ready():
            if result.successful():
                task_result = result.get()
                
                # Completely clean the result to ensure JSON serialization
                def clean_for_json(obj):
                    """Recursively clean an object for JSON serialization."""
                    if obj is None:
                        return None
                    elif isinstance(obj, bool):
                        return obj
                    elif isinstance(obj, (int, float)):
                        return obj
                    elif isinstance(obj, str):
                        # Ensure string is valid UTF-8
                        try:
                            obj.encode('utf-8')
                            return obj
                        except UnicodeError:
                            return str(obj)
                    elif isinstance(obj, bytes):
                        # Never include bytes in the result
                        return f"<binary data: {len(obj)} bytes>"
                    elif isinstance(obj, dict):
                        cleaned = {}
                        for k, v in obj.items():
                            try:
                                key = str(k)
                                cleaned[key] = clean_for_json(v)
                            except Exception:
                                pass  # Skip problematic keys
                        return cleaned
                    elif isinstance(obj, (list, tuple)):
                        cleaned = []
                        for item in obj:
                            try:
                                cleaned_item = clean_for_json(item)
                                if cleaned_item is not None:
                                    cleaned.append(cleaned_item)
                            except Exception:
                                pass  # Skip problematic items
                        return cleaned
                    else:
                        # Convert everything else to string, but safely
                        try:
                            return str(obj)
                        except Exception:
                            return "<unserializable object>"
                
                cleaned_result = clean_for_json(task_result)
                
                return {
                    "success": True,
                    "status": "completed",
                    "task_id": task_id,
                    "result": cleaned_result
                }
            else:
                error = str(result.info) if result.info else "Unknown error"
                return {
                    "success": False,
                    "status": "failed",
                    "task_id": task_id,
                    "error": error
                }
        else:
            # Task is still processing
            return {
                "success": True,
                "status": "processing",
                "task_id": task_id,
                "message": "Task is still being processed"
            }
            
    except Exception as e:
        logger.error(f"Get result error for task {task_id}: {e}")
        return {
            "success": False,
            "status": "error",
            "task_id": task_id,
            "error": str(e)
        }

@app.get("/tasks/active")
async def get_active_tasks():
    """Get information about active tasks."""
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        # Clean the response to avoid serialization issues
        cleaned_tasks = {}
        if active_tasks:
            for worker, tasks in active_tasks.items():
                cleaned_tasks[worker] = []
                for task in tasks:
                    # Only include serializable fields
                    cleaned_task = {
                        "id": task.get("id", ""),
                        "name": task.get("name", ""),
                        "time_start": task.get("time_start", 0)
                    }
                    cleaned_tasks[worker].append(cleaned_task)
        
        return {
            "success": True,
            "active_tasks": cleaned_tasks,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Get active tasks error: {e}")
        # Return empty result instead of raising exception
        return {
            "success": True,
            "active_tasks": {},
            "timestamp": time.time(),
            "error": "Could not retrieve active tasks"
        }

@app.get("/stats")
async def get_stats():
    """Get system and queue statistics."""
    try:
        import psutil
        import torch
        
        # System stats
        system_stats = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
        
        # GPU stats
        gpu_stats = {
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        if torch.cuda.is_available():
            try:
                gpu_stats["memory"] = {
                    "allocated": torch.cuda.memory_allocated(),
                    "cached": torch.cuda.memory_reserved()
                }
            except Exception:
                gpu_stats["memory"] = {"error": "Could not get GPU memory stats"}
        
        # Simplified Celery stats to avoid serialization issues
        celery_stats = {
            "workers_online": 0,
            "active_task_count": 0
        }
        
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            if stats:
                celery_stats["workers_online"] = len(stats)
            
            active = inspect.active()
            if active:
                total_active = sum(len(tasks) for tasks in active.values())
                celery_stats["active_task_count"] = total_active
        except Exception:
            pass  # Ignore Celery inspection errors
        
        return {
            "success": True,
            "system": system_stats,
            "gpu": gpu_stats,
            "celery": celery_stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/admin/clear-cache")
async def clear_cache():
    """Clear GPU memory cache (admin endpoint)."""
    try:
        import torch
        import gc
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        gc.collect()
        
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/download-models")
async def download_models():
    """Manually trigger model downloads (admin endpoint)."""
    try:
        logger.info("Starting manual model download...")
        models_ready = ensure_models_downloaded(settings.model_cache_dir)
        
        if models_ready:
            return {
                "success": True,
                "message": "All models downloaded successfully"
            }
        else:
            return {
                "success": False,
                "message": "Some models failed to download. Check logs for details."
            }
    except Exception as e:
        logger.error(f"Manual model download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/restart-models")
async def restart_models():
    """Restart AI models for optimal performance (admin endpoint)."""
    try:
        # Clear model cache to force reload with latest settings
        from tasks import _model_cache
        _model_cache['realesrgan'] = None
        _model_cache['gfpgan'] = None
        
        # Clear GPU memory
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        
        import gc
        gc.collect()
        
        return {
            "success": True,
            "message": "Models restarted successfully. Next inference will reload models."
        }
    except Exception as e:
        logger.error(f"Restart models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
