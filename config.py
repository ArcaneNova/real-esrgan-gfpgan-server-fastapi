import os
from typing import Optional, List
from pydantic import BaseSettings

def get_optimal_device():
    """Auto-detect the best available device for inference."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    except ImportError:
        return "cpu"

class Settings(BaseSettings):
    # Cloudinary settings
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    
    # Redis settings
    redis_broker: str = "redis://localhost:6379/0"
    redis_backend: str = "redis://localhost:6379/0"
    
    # Application settings
    environment: str = "development"
    max_workers: int = 4
    max_concurrent_tasks: int = 10
    model_cache_dir: str = "./models"
    temp_dir: str = "./temp"
    
    # API settings
    api_title: str = "Image Upscaler SaaS API"
    api_version: str = "1.0.0"
    api_description: str = "Production-grade image upscaling service"
    
    # Performance settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_formats: list = ["jpeg", "jpg", "png", "webp"]
    
    # AI inference settings
    device: str = get_optimal_device()  # Auto-detect best device
    enable_half_precision: bool = True  # Use FP16 on GPU for speed
    max_batch_size: int = 1  # Process images individually for consistency
    tile_size: int = 512  # Optimal tile size for memory/speed balance
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
