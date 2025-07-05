import torch
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import logging
import gc
from pathlib import Path

try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    try:
        from basicsr.archs.srvgg_arch import SRVGGNetCompact
        SRVGG_AVAILABLE = True
    except ImportError:
        SRVGG_AVAILABLE = False
        logging.warning("SRVGGNetCompact not available. Using RRDBNet for all models.")
    from realesrgan import RealESRGANer
    REALESRGAN_AVAILABLE = True
except ImportError:
    REALESRGAN_AVAILABLE = False
    SRVGG_AVAILABLE = False
    logging.warning("Real-ESRGAN not available. Install with: pip install realesrgan")

from utils.model_downloader import ModelDownloader
from config import settings

logger = logging.getLogger(__name__)

class RealESRGANInference:
    def __init__(self, model_name: str = "realesrgan_general_x4v3", device: Optional[str] = None):
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
            if "general" in self.model_name and SRVGG_AVAILABLE:
                # realesr-general-x4v3 - uses SRVGGNetCompact architecture
                scale = 4
                model_arch = SRVGGNetCompact(
                    num_in_ch=3, 
                    num_out_ch=3, 
                    num_feat=64,
                    num_conv=32,
                    upscale=4,
                    act_type='prelu'
                )
                logger.info("Using SRVGGNetCompact architecture for general model")
            elif "general" in self.model_name and not SRVGG_AVAILABLE:
                # Fallback to RRDBNet for general model if SRVGGNetCompact not available
                scale = 4
                model_arch = RRDBNet(
                    num_in_ch=3, 
                    num_out_ch=3, 
                    num_feat=64, 
                    num_block=6,  # Smaller for speed
                    num_grow_ch=32, 
                    scale=4
                )
                logger.warning("SRVGGNetCompact not available. Using RRDBNet fallback for general model")
            elif "x4plus" in self.model_name:
                # Legacy x4plus model - uses RRDBNet architecture
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
                # Default to SRVGGNetCompact for modern models, fallback to RRDBNet
                scale = 4
                if SRVGG_AVAILABLE:
                    model_arch = SRVGGNetCompact(
                        num_in_ch=3, 
                        num_out_ch=3, 
                        num_feat=64,
                        num_conv=32,
                        upscale=4,
                        act_type='prelu'
                    )
                else:
                    model_arch = RRDBNet(
                        num_in_ch=3, 
                        num_out_ch=3, 
                        num_feat=64, 
                        num_block=6, 
                        num_grow_ch=32, 
                        scale=4
                    )
            
            # Initialize the upscaler with performance optimizations
            try:
                self.model = RealESRGANer(
                    scale=scale,
                    model_path=str(model_path),
                    model=model_arch,
                    tile=512,  # Enable tiling for memory efficiency and speed
                    tile_pad=10,
                    pre_pad=0,
                    half=True if self.device == 'cuda' else False,  # Use half precision on GPU
                    device=self.device
                )
            except Exception as arch_error:
                logger.warning(f"Architecture mismatch with {model_arch.__class__.__name__}: {arch_error}")
                # Fallback to RRDBNet with minimal configuration
                if not isinstance(model_arch, RRDBNet):
                    logger.info("Trying RRDBNet fallback architecture...")
                    model_arch = RRDBNet(
                        num_in_ch=3, 
                        num_out_ch=3, 
                        num_feat=64, 
                        num_block=6, 
                        num_grow_ch=32, 
                        scale=scale
                    )
                    self.model = RealESRGANer(
                        scale=scale,
                        model_path=str(model_path),
                        model=model_arch,
                        tile=512,
                        tile_pad=10,
                        pre_pad=0,
                        half=True if self.device == 'cuda' else False,
                        device=self.device
                    )
                else:
                    raise arch_error
            
            # Optimize for inference
            if hasattr(self.model.model, 'eval'):
                self.model.model.eval()
            
            # Enable GPU optimizations if available
            if self.device == 'cuda' and torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
            
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
            # Pre-process image for optimal inference
            image_np = np.array(image)
            
            # Ensure RGB format and optimize dimensions
            if len(image_np.shape) == 3 and image_np.shape[2] == 4:  # RGBA
                # Convert RGBA to RGB efficiently
                rgb = image_np[:, :, :3]
                alpha = image_np[:, :, 3:4] / 255.0
                image_np = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
            elif len(image_np.shape) == 2:  # Grayscale
                image_np = np.stack([image_np] * 3, axis=2)
            
            # Optimize input size - resize if too large for speed
            h, w = image_np.shape[:2]
            max_size = 2048  # Maximum input dimension for speed
            if max(h, w) > max_size:
                ratio = max_size / max(h, w)
                new_h, new_w = int(h * ratio), int(w * ratio)
                image_resized = Image.fromarray(image_np).resize((new_w, new_h), Image.Resampling.LANCZOS)
                image_np = np.array(image_resized)
                logger.info(f"Resized input from {(w, h)} to {(new_w, new_h)} for faster processing")
            
            # Perform enhancement with optimizations
            logger.info(f"Upscaling image with shape: {image_np.shape}")
            
            with torch.no_grad():  # Disable gradient computation for speed
                output_np, _ = self.model.enhance(image_np, outscale=None)
            
            # Convert back to PIL Image
            output_image = Image.fromarray(output_np)
            
            logger.info(f"Upscaling completed. Output shape: {output_np.shape}")
            
            # Aggressive memory cleanup for high concurrency
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
