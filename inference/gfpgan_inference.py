import torch
import numpy as np
from PIL import Image
from typing import Optional, List
import logging
import gc
import cv2

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
            # Ensure model is downloaded
            downloader = ModelDownloader(settings.model_cache_dir)
            model_path = downloader.get_model_path(self.model_name)
            
            if not model_path or not model_path.exists():
                logger.info(f"Downloading {self.model_name} model...")
                if not downloader.download_model(self.model_name):
                    logger.error(f"Failed to download {self.model_name}")
                    return False
                model_path = downloader.get_model_path(self.model_name)
            
            # Initialize GFPGAN
            self.model = GFPGANer(
                model_path=str(model_path),
                upscale=2,  # 2x upscale for faces
                arch='clean',
                channel_multiplier=2,
                bg_upsampler=None,  # Don't upscale background
                device=self.device
            )
            
            self.is_loaded = True
            logger.info(f"GFPGAN model loaded successfully: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load GFPGAN model: {e}")
            return False
    
    def enhance_faces(self, image: Image.Image, only_center_face: bool = False) -> Optional[Image.Image]:
        """Enhance faces in an image using GFPGAN."""
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            # Convert PIL to numpy array (RGB)
            image_np = np.array(image)
            
            # Convert to BGR for OpenCV/GFPGAN
            if len(image_np.shape) == 3:
                if image_np.shape[2] == 4:  # RGBA
                    # Convert RGBA to RGB first
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image_np = np.array(background)
                    
                # Convert RGB to BGR
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                # Grayscale - convert to BGR
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            
            logger.info(f"Enhancing faces in image with shape: {image_bgr.shape}")
            
            # Perform face enhancement
            cropped_faces, restored_img, improved_img = self.model.enhance(
                image_bgr,
                has_aligned=False,
                only_center_face=only_center_face,
                paste_back=True,
                weight=0.5  # Balance between original and enhanced
            )
            
            # Use improved_img if available (background + enhanced faces), otherwise restored_img
            result_bgr = improved_img if improved_img is not None else restored_img
            
            # Convert BGR back to RGB
            result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            output_image = Image.fromarray(result_rgb)
            
            logger.info(f"Face enhancement completed. Found {len(cropped_faces)} faces")
            
            # Clean up GPU memory
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
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            
            # Use GFPGAN's face detection
            cropped_faces, _, _ = self.model.enhance(
                image_bgr,
                has_aligned=False,
                only_center_face=False,
                paste_back=False  # Don't paste back, just detect
            )
            
            return len(cropped_faces)
            
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
    """High-level function to enhance faces in an image."""
    instance = get_gfpgan_instance()
    return instance.enhance_faces(image, only_center_face)

def detect_faces_count(image: Image.Image) -> int:
    """High-level function to count faces in an image."""
    instance = get_gfpgan_instance()
    return instance.detect_faces(image)
