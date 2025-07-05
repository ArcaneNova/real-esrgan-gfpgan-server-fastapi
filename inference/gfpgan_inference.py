import torch
import numpy as np
from PIL import Image
from typing import Optional, List
import logging
import gc
import cv2
from pathlib import Path

try:
    from gfpgan import GFPGANer
    GFPGAN_AVAILABLE = True
except ImportError:
    GFPGAN_AVAILABLE = False
    logging.warning("GFPGAN not available. Install with: pip install gfpgan")

from utils.model_downloader import ModelDownloader
from config import settings

logger = logging.getLogger(__name__)

class GFPGANInference:
    def __init__(self, model_name: str = "gfpgan_v1.4", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.is_loaded = False
        
        logger.info(f"Initializing GFPGAN with device: {self.device}")
        
    def load_model(self) -> bool:
        """Load the GFPGAN model."""
        if not GFPGAN_AVAILABLE:
            logger.error("GFPGAN is not available")
            return False
            
        try:
            # Try to use model downloader first
            downloader = ModelDownloader(settings.model_cache_dir)
            model_path = downloader.get_model_path("gfpgan_v1.4")
            
            if not model_path or not model_path.exists():
                logger.info("Downloading GFPGAN v1.4 model...")
                if not downloader.download_model("gfpgan_v1.4"):
                    logger.error("Failed to download GFPGAN model")
                    # Fallback: look for existing model files
                    model_dir = Path(settings.model_cache_dir)
                    for model_file in ["GFPGANv1.4.pth", "GFPGANv1.3.pth"]:
                        potential_path = model_dir / model_file
                        if potential_path.exists() and potential_path.stat().st_size > 100 * 1024 * 1024:  # At least 100MB
                            model_path = potential_path
                            logger.info(f"Found existing GFPGAN model: {model_path}")
                            break
                    
                    if not model_path:
                        logger.warning("No valid GFPGAN model found, GFPGAN features will use fallback")
                        return False
                else:
                    model_path = downloader.get_model_path("gfpgan_v1.4")
            
            # Initialize GFPGAN with speed optimizations
            self.model = GFPGANer(
                model_path=str(model_path),
                upscale=1,  # No upscaling for speed (just enhancement)
                arch='clean',
                channel_multiplier=2,
                bg_upsampler=None,  # Don't upscale background for speed
                device=self.device
            )
            
            # Enable inference optimizations
            if hasattr(self.model.gfpgan, 'eval'):
                self.model.gfpgan.eval()
            
            # GPU optimizations
            if self.device == 'cuda' and torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
            
            self.is_loaded = True
            logger.info(f"GFPGAN model loaded successfully: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load GFPGAN model: {e}")
            return False
    
    def enhance_faces(self, image: Image.Image, only_center_face: bool = False) -> Optional[Image.Image]:
        """Enhance faces in an image using GFPGAN with speed optimizations."""
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            # Aggressive size optimization for speed
            original_size = image.size
            max_dimension = 1024  # Much smaller for speed
            
            if max(original_size) > max_dimension:
                # Calculate new size maintaining aspect ratio
                ratio = max_dimension / max(original_size)
                new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {original_size} to {new_size} for faster processing")
            
            # Convert PIL to numpy array (RGB)
            image_np = np.array(image)
            
            # Convert to BGR for OpenCV/GFPGAN efficiently
            if len(image_np.shape) == 3:
                if image_np.shape[2] == 4:  # RGBA
                    # Quick RGBA to RGB conversion
                    rgb = image_np[:, :, :3]
                    alpha = image_np[:, :, 3:4] / 255.0
                    image_np = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
                    
                # Convert RGB to BGR
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                # Grayscale - convert to BGR
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            
            logger.info(f"Enhancing faces in image with shape: {image_bgr.shape}")
            
            # Fast enhancement with minimal quality loss
            with torch.no_grad():  # Disable gradients for speed
                cropped_faces, restored_img, improved_img = self.model.enhance(
                    image_bgr,
                    has_aligned=False,
                    only_center_face=True,  # Process only center face for speed
                    paste_back=True,
                    weight=0.7  # Higher weight for less processing
                )
            
            # Use improved_img if available, otherwise restored_img
            result_bgr = improved_img if improved_img is not None else restored_img
            
            # Convert BGR back to RGB
            result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            output_image = Image.fromarray(result_rgb)
            
            # Resize back to original size if we resized earlier
            if max(original_size) > max_dimension:
                output_image = output_image.resize(original_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized result back to original size: {original_size}")
            
            logger.info(f"Face enhancement completed. Found {len(cropped_faces)} faces")
            
            # Aggressive memory cleanup for concurrency
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
            return output_image
            
        except Exception as e:
            logger.error(f"Failed to enhance faces: {e}")
            # Clean up on error
            if self.device == 'cuda':
                torch.cuda.empty_cache()
                gc.collect()
            return None
    
    def detect_faces(self, image: Image.Image) -> int:
        """Detect the number of faces in an image."""
        if not self.is_loaded:
            if not self.load_model():
                return 0
        
        try:
            # Convert PIL to numpy array and then to BGR
            image_np = np.array(image)
            
            # Resize large images for faster face detection
            original_size = image.size
            max_dimension = 1024  # Reasonable size for face detection
            
            if max(original_size) > max_dimension:
                ratio = max_dimension / max(original_size)
                new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                image_np = np.array(image)
            
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            
            # Use GFPGAN's face detection with basic timeout protection
            try:
                cropped_faces, _, _ = self.model.enhance(
                    image_bgr,
                    has_aligned=False,
                    only_center_face=False,
                    paste_back=False  # Don't paste back, just detect
                )
                return len(cropped_faces)
            except Exception as enhance_error:
                logger.warning(f"Face detection failed: {enhance_error}")
                return 0
            
        except Exception as e:
            logger.error(f"Failed to detect faces: {e}")
            return 0
    
    def unload_model(self):
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info("GFPGAN model unloaded")

# Global instance - will be initialized when first used
_gfpgan_instance = None

def get_gfpgan_instance() -> GFPGANInference:
    """Get or create the global GFPGAN instance."""
    global _gfpgan_instance
    if _gfpgan_instance is None:
        _gfpgan_instance = GFPGANInference()
    return _gfpgan_instance

def enhance_faces(image: Image.Image, only_center_face: bool = False) -> Optional[Image.Image]:
    """High-level function to enhance faces in an image with fallback."""
    try:
        instance = get_gfpgan_instance()
        result = instance.enhance_faces(image, only_center_face)
        
        if result is not None:
            return result
        else:
            logger.warning("GFPGAN enhancement failed, using basic image enhancement")
            return _basic_image_enhancement(image)
            
    except Exception as e:
        logger.error(f"GFPGAN enhancement error: {e}")
        logger.info("Falling back to basic image enhancement")
        return _basic_image_enhancement(image)

def _basic_image_enhancement(image: Image.Image) -> Image.Image:
    """Basic image enhancement as fallback when GFPGAN fails."""
    try:
        from PIL import ImageEnhance, ImageFilter
        
        # Apply basic enhancements
        enhanced = image
        
        # Slightly sharpen the image
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
        
        # Enhance contrast slightly
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.1)
        
        # Enhance color slightly
        enhancer = ImageEnhance.Color(enhanced)
        enhanced = enhancer.enhance(1.05)
        
        logger.info("Applied basic image enhancement")
        return enhanced
        
    except Exception as e:
        logger.error(f"Basic enhancement failed: {e}")
        return image  # Return original if everything fails

def detect_faces_count(image: Image.Image) -> int:
    """High-level function to count faces in an image with fallback."""
    try:
        instance = get_gfpgan_instance()
        count = instance.detect_faces(image)
        return count if count > 0 else 1  # Assume at least 1 face if detection fails
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return 1  # Assume at least 1 face if detection completely fails
