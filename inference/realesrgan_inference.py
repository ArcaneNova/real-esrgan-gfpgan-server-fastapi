import torch
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import logging
import gc
from pathlib import Path

try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer
    REALESRGAN_AVAILABLE = True
except ImportError:
    REALESRGAN_AVAILABLE = False
    logging.warning("Real-ESRGAN not available. Install with: pip install realesrgan")

from utils.model_downloader import ModelDownloader
from config import settings

logger = logging.getLogger(__name__)

class RealESRGANInference:
    def __init__(self, model_name: str = "realesrgan_x4plus", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.is_loaded = False
        
        logger.info(f"Initializing Real-ESRGAN with device: {self.device}")
        
    def load_model(self) -> bool:
        """Load the Real-ESRGAN model."""
        if not REALESRGAN_AVAILABLE:
            logger.error("Real-ESRGAN is not available")
            return False
            
        try:
            # Ensure model is downloaded
            downloader = ModelDownloader(settings.model_cache_dir)
            model_path = downloader.get_model_path(self.model_name)
            
            if not model_path or not model_path.exists():
                logger.info(f"Downloading {self.model_name} model...")
                if not downloader.download_model(self.model_name):
                    logger.error(f"Failed to download {self.model_name}")
                    return False
                model_path = downloader.get_model_path(self.model_name)
            
            # Configure model parameters based on model type
            if "x4plus" in self.model_name:
                scale = 4
                model_arch = RRDBNet(
                    num_in_ch=3, 
                    num_out_ch=3, 
                    num_feat=64, 
                    num_block=23, 
                    num_grow_ch=32, 
                    scale=4
                )
            elif "x2plus" in self.model_name:
                scale = 2
                model_arch = RRDBNet(
                    num_in_ch=3, 
                    num_out_ch=3, 
                    num_feat=64, 
                    num_block=23, 
                    num_grow_ch=32, 
                    scale=2
                )
            else:
                scale = 4
                model_arch = RRDBNet(
                    num_in_ch=3, 
                    num_out_ch=3, 
                    num_feat=64, 
                    num_block=23, 
                    num_grow_ch=32, 
                    scale=4
                )
            
            # Initialize the upscaler
            self.model = RealESRGANer(
                scale=scale,
                model_path=str(model_path),
                model=model_arch,
                tile=0,  # Disable tiling for speed
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False,
                device=self.device
            )
            
            self.is_loaded = True
            logger.info(f"Real-ESRGAN model loaded successfully: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Real-ESRGAN model: {e}")
            return False
    
    def upscale(self, image: Image.Image) -> Optional[Image.Image]:
        """Upscale an image using Real-ESRGAN."""
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            # Convert PIL to numpy array
            image_np = np.array(image)
            
            # Ensure RGB format
            if len(image_np.shape) == 3 and image_np.shape[2] == 4:  # RGBA
                # Convert RGBA to RGB
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image_np = np.array(background)
            elif len(image_np.shape) == 2:  # Grayscale
                image_np = np.stack([image_np] * 3, axis=2)
            
            # Perform enhancement
            logger.info(f"Upscaling image with shape: {image_np.shape}")
            output_np, _ = self.model.enhance(image_np, outscale=None)
            
            # Convert back to PIL Image
            output_image = Image.fromarray(output_np)
            
            logger.info(f"Upscaling completed. Output shape: {output_np.shape}")
            
            # Clean up GPU memory
            if self.device == 'cuda':
                torch.cuda.empty_cache()
                gc.collect()
            
            return output_image
            
        except Exception as e:
            logger.error(f"Failed to upscale image: {e}")
            # Clean up on error
            if self.device == 'cuda':
                torch.cuda.empty_cache()
                gc.collect()
            return None
    
    def unload_model(self):
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info("Real-ESRGAN model unloaded")

# Global instance - will be initialized when first used
_realesrgan_instance = None

def get_realesrgan_instance() -> RealESRGANInference:
    """Get or create the global Real-ESRGAN instance."""
    global _realesrgan_instance
    if _realesrgan_instance is None:
        _realesrgan_instance = RealESRGANInference()
    return _realesrgan_instance

def upscale_image(image: Image.Image) -> Optional[Image.Image]:
    """High-level function to upscale an image."""
    instance = get_realesrgan_instance()
    return instance.upscale(image)
