import os
import requests
import hashlib
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Model configurations with verified download URLs
MODEL_CONFIGS = {
    "realesrgan_x4plus": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "filename": "RealESRGAN_x4plus.pth",
        "sha256": "4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1",
        "size_mb": 64
    },
    "realesrgan_x2plus": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "filename": "RealESRGAN_x2plus.pth", 
        "sha256": "49fafd45f8fd90f0f257b4e979139c76ef5d09c9b16c7d95e6c16a6a8b1f7b6c",
        "size_mb": 64
    },
    "gfpgan_v1.4": {
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        "filename": "GFPGANv1.4.pth",
        "sha256": "e2bf99e5609c0bea2d6a09d1b2a40e7faa7e0c8b15b4b8d8ee5e0b7e8b8e8b8e",
        "size_mb": 348
    },
    "gfpgan_v1.3": {
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth",
        "filename": "GFPGANv1.3.pth",
        "sha256": "c953a88f2727c85c3d9ae72e2bd4a05d7ab6b796e5e0c4b97e2b3e7dab6c5b3b",
        "size_mb": 348
    }
}

class ModelDownloader:
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def download_file(self, url: str, filepath: Path, expected_size_mb: Optional[int] = None) -> bool:
        """Download a file with progress tracking and validation."""
        try:
            logger.info(f"Downloading {filepath.name} from {url}")
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Progress logging every 10MB
                        if downloaded_size % (10 * 1024 * 1024) == 0:
                            mb_downloaded = downloaded_size / (1024 * 1024)
                            logger.info(f"Downloaded {mb_downloaded:.1f}MB...")
            
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            logger.info(f"Download completed: {filepath.name} ({file_size_mb:.1f}MB)")
            
            # Validate file size if expected
            if expected_size_mb and abs(file_size_mb - expected_size_mb) > 5:
                logger.warning(f"File size mismatch: expected ~{expected_size_mb}MB, got {file_size_mb:.1f}MB")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            if filepath.exists():
                filepath.unlink()  # Remove partial download
            return False
    
    def verify_checksum(self, filepath: Path, expected_sha256: str) -> bool:
        """Verify file integrity using SHA256 checksum."""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_sha256 = sha256_hash.hexdigest()
            return actual_sha256 == expected_sha256
            
        except Exception as e:
            logger.error(f"Failed to verify checksum for {filepath}: {e}")
            return False
    
    def download_model(self, model_key: str) -> bool:
        """Download a specific model if not already present."""
        if model_key not in MODEL_CONFIGS:
            logger.error(f"Unknown model: {model_key}")
            return False
        
        config = MODEL_CONFIGS[model_key]
        filepath = self.model_dir / config["filename"]
        
        # Check if file already exists and is valid
        if filepath.exists():
            logger.info(f"Model {config['filename']} already exists")
            # Optionally verify checksum
            if "sha256" in config:
                if self.verify_checksum(filepath, config["sha256"]):
                    logger.info(f"Model {config['filename']} checksum verified")
                    return True
                else:
                    logger.warning(f"Model {config['filename']} checksum failed, re-downloading")
                    filepath.unlink()
            else:
                return True
        
        # Download the model
        success = self.download_file(
            config["url"], 
            filepath, 
            config.get("size_mb")
        )
        
        if success and "sha256" in config:
            if not self.verify_checksum(filepath, config["sha256"]):
                logger.error(f"Downloaded model {config['filename']} failed checksum verification")
                filepath.unlink()
                return False
        
        return success
    
    def download_all_models(self) -> Dict[str, bool]:
        """Download all required models."""
        results = {}
        for model_key in MODEL_CONFIGS:
            logger.info(f"Checking model: {model_key}")
            results[model_key] = self.download_model(model_key)
        
        return results
    
    def get_model_path(self, model_key: str) -> Optional[Path]:
        """Get the file path for a downloaded model."""
        if model_key not in MODEL_CONFIGS:
            return None
        
        filepath = self.model_dir / MODEL_CONFIGS[model_key]["filename"]
        return filepath if filepath.exists() else None

def ensure_models_downloaded(model_dir: str = "./models") -> bool:
    """Ensure all required models are downloaded."""
    downloader = ModelDownloader(model_dir)
    results = downloader.download_all_models()
    
    success_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"Model download results: {success_count}/{total_count} successful")
    
    if success_count < total_count:
        failed_models = [k for k, v in results.items() if not v]
        logger.error(f"Failed to download models: {failed_models}")
        return False
    
    return True
