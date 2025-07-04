#!/usr/bin/env python3
"""
Model downloader for optimized production models
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Download models for production use."""
    try:
        # Set environment
        os.environ['MODEL_CACHE_DIR'] = '/app/models'
        
        # Import after setting environment
        from utils import ensure_models_downloaded
        
        logger.info("� Starting optimized model download...")
        success = ensure_models_downloaded('/app/models')
        
        if success:
            logger.info("✅ All optimized models downloaded successfully!")
        else:
            logger.warning("⚠️ Some models failed to download, but continuing...")
            logger.info("Models will be downloaded on first run")
            
    except Exception as e:
        logger.error(f"❌ Model download failed: {e}")
        logger.info("Models will be downloaded on first run")
        # Don't fail the build, just continue
        
if __name__ == "__main__":
    main()
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
