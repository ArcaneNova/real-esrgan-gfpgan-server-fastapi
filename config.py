import os
from typing import Optional, List
from pydantic import BaseSettings

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
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
