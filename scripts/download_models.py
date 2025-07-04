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
        
        logger.info("🚀 Starting optimized model download...")
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