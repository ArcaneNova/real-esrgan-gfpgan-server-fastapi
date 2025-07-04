#!/usr/bin/env python3
"""
Alternative model downloader with better URLs and fallbacks
"""

import os
import requests
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Working model URLs (verified and tested)
WORKING_MODELS = {
    "realesrgan_x4plus": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "filename": "RealESRGAN_x4plus.pth",
        "description": "Real-ESRGAN 4x upscaler",
        "essential": True
    },
    "realesrgan_x4plus_anime": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        "filename": "RealESRGAN_x4plus_anime_6B.pth", 
        "description": "Real-ESRGAN 4x anime upscaler",
        "essential": False
    }
}

def download_file(url: str, filepath: Path) -> bool:
    """Download a file with progress tracking."""
    try:
        logger.info(f"📥 Downloading {filepath.name}...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(filepath, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Progress every 10MB
                    if downloaded_size % (10 * 1024 * 1024) == 0:
                        mb_downloaded = downloaded_size / (1024 * 1024)
                        logger.info(f"  Downloaded {mb_downloaded:.1f}MB...")
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Download completed: {filepath.name} ({file_size_mb:.1f}MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download {url}: {e}")
        if filepath.exists():
            filepath.unlink()
        return False

def download_models(model_dir: str = "./models", essential_only: bool = False) -> Dict[str, bool]:
    """Download AI models."""
    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    for model_key, config in WORKING_MODELS.items():
        if essential_only and not config.get("essential", False):
            logger.info(f"⏭️ Skipping non-essential model: {model_key}")
            continue
            
        filepath = model_path / config["filename"]
        
        # Check if already exists
        if filepath.exists():
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            if file_size_mb > 10:  # Reasonable minimum size
                logger.info(f"✅ Model exists: {config['filename']} ({file_size_mb:.1f}MB)")
                results[model_key] = True
                continue
            else:
                logger.warning(f"⚠️ Model file too small, re-downloading: {config['filename']}")
                filepath.unlink()
        
        # Download the model
        logger.info(f"🤖 {config['description']}")
        results[model_key] = download_file(config["url"], filepath)
    
    return results

if __name__ == "__main__":
    logger.info("🚀 Alternative Model Downloader")
    
    # Download essential models only
    results = download_models(essential_only=True)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"📊 Results: {success_count}/{total_count} models downloaded successfully")
    
    if success_count > 0:
        logger.info("🎉 Ready to start the API!")
        logger.info("🔥 Next: uvicorn main:app --reload --port 8000")
    else:
        logger.error("❌ No models downloaded. Check your internet connection.")
        exit(1)
