from .realesrgan_inference import (
    RealESRGANInference,
    get_realesrgan_instance,
    upscale_image
)
from .gfpgan_inference import (
    GFPGANInference, 
    get_gfpgan_instance,
    enhance_faces,
    detect_faces_count
)

__all__ = [
    "RealESRGANInference",
    "get_realesrgan_instance", 
    "upscale_image",
    "GFPGANInference",
    "get_gfpgan_instance",
    "enhance_faces",
    "detect_faces_count"
]
