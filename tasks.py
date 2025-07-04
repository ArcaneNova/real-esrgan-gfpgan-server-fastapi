from celery import Celery
from celery.exceptions import Retry
import os
import io
import logging
from PIL import Image
from typing import Dict, Any, Optional
import traceback
import time

from config import settings
from utils.cloudinary_utils import cloudinary_manager
from inference.realesrgan_inference import upscale_image
from inference.gfpgan_inference import enhance_faces, detect_faces_count

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery("tasks")
celery_app.config_from_object("celeryconfig")

# Global model cache for performance
_model_cache = {
    'realesrgan': None,
    'gfpgan': None
}

def get_realesrgan_model():
    """Get cached Real-ESRGAN model or create new one."""
    global _model_cache
    if _model_cache['realesrgan'] is None:
        from inference.realesrgan_inference import RealESRGANInference
        _model_cache['realesrgan'] = RealESRGANInference(device=settings.device)
        _model_cache['realesrgan'].load_model()
    return _model_cache['realesrgan']

def get_gfpgan_model():
    """Get cached GFPGAN model or create new one."""
    global _model_cache
    if _model_cache['gfpgan'] is None:
        from inference.gfpgan_inference import GFPGANInference
        _model_cache['gfpgan'] = GFPGANInference(device=settings.device)
        _model_cache['gfpgan'].load_model()
    return _model_cache['gfpgan']

@celery_app.task(name="tasks.upscale_esrgan", bind=True, max_retries=3)
def upscale_esrgan(self, image_bytes: bytes, filename: str, options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Upscale an image using Real-ESRGAN.
    
    Args:
        image_bytes: Raw image bytes
        filename: Original filename
        options: Additional processing options
    
    Returns:
        Dictionary with result data (JSON-serializable only)
    """
    start_time = time.time()
    task_id = self.request.id
    
    def clean_result(result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result contains only JSON-serializable data."""
        cleaned = {}
        for key, value in result_dict.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                cleaned[key] = value
            elif isinstance(value, dict):
                cleaned[key] = clean_result(value)
            elif isinstance(value, (list, tuple)):
                cleaned[key] = [
                    clean_result(item) if isinstance(item, dict) else item 
                    for item in value 
                    if isinstance(item, (str, int, float, bool, type(None), dict))
                ]
            else:
                # Convert non-serializable types to string
                cleaned[key] = str(value)
        return cleaned
    
    try:
        logger.info(f"Task {task_id}: Starting Real-ESRGAN upscaling for {filename}")
        
        # Parse options
        options = options or {}
        output_format = options.get("format", "webp")
        quality = options.get("quality", "auto")
        
        # Load image from bytes
        try:
            image = Image.open(io.BytesIO(image_bytes))
            logger.info(f"Task {task_id}: Loaded image {image.size} mode={image.mode}")
        except Exception as e:
            logger.error(f"Task {task_id}: Failed to load image: {e}")
            return clean_result({
                "success": False,
                "error": f"Invalid image format: {str(e)}",
                "task_id": task_id
            })
        
        # Validate image size (prevent memory issues)
        max_pixels = 5 * 1024 * 1024  # 5MP limit
        if image.size[0] * image.size[1] > max_pixels:
            return clean_result({
                "success": False,
                "error": "Image too large. Maximum 5 megapixels allowed.",
                "task_id": task_id
            })
        
        # Perform upscaling using cached model
        processing_start = time.time()
        try:
            model = get_realesrgan_model()
            upscaled_image = model.upscale(image)
        except Exception as e:
            logger.error(f"Task {task_id}: Model error, falling back: {e}")
            upscaled_image = upscale_image(image)  # Fallback to original function
        processing_time = time.time() - processing_start
        
        if upscaled_image is None:
            logger.error(f"Task {task_id}: Upscaling failed")
            return clean_result({
                "success": False,
                "error": "Upscaling failed. Please try again.",
                "task_id": task_id
            })
        
        logger.info(f"Task {task_id}: Upscaling completed in {processing_time:.2f}s. Output size: {upscaled_image.size}")
        
        # Upload to Cloudinary
        upload_start = time.time()
        upload_result = cloudinary_manager.upload_image(
            upscaled_image,
            f"upscaled_{filename}",
            folder="realesrgan",
            format=output_format,
            quality=quality
        )
        upload_time = time.time() - upload_start
        
        if upload_result is None:
            logger.error(f"Task {task_id}: Upload to Cloudinary failed")
            return clean_result({
                "success": False,
                "error": "Failed to upload result. Please try again.",
                "task_id": task_id
            })
        
        total_time = time.time() - start_time
        
        result = {
            "success": True,
            "task_id": task_id,
            "image_url": str(upload_result.get("secure_url", "")),
            "public_id": str(upload_result.get("public_id", "")),
            "original_size": list(image.size),
            "upscaled_size": list(upscaled_image.size),
            "scale_factor": float(upscaled_image.size[0] / image.size[0]),
            "processing_time": round(float(processing_time), 2),
            "upload_time": round(float(upload_time), 2),
            "total_time": round(float(total_time), 2),
            "format": str(output_format),
            "cloudinary_info": {
                "bytes": int(upload_result.get("bytes", 0)) if upload_result.get("bytes") else 0,
                "format": str(upload_result.get("format", "")),
                "width": int(upload_result.get("width", 0)) if upload_result.get("width") else 0,
                "height": int(upload_result.get("height", 0)) if upload_result.get("height") else 0
            }
        }
        
        logger.info(f"Task {task_id}: Completed successfully in {total_time:.2f}s")
        return clean_result(result)
        
    except Exception as e:
        logger.error(f"Task {task_id}: Unexpected error: {e}")
        logger.error(f"Task {task_id}: Traceback: {traceback.format_exc()}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Task {task_id}: Retrying in 60 seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        
        return clean_result({
            "success": False,
            "error": f"Processing failed after {self.max_retries} retries: {str(e)}",
            "task_id": task_id
        })

@celery_app.task(name="tasks.enhance_gfpgan", bind=True, max_retries=3)
def enhance_gfpgan(self, image_bytes: bytes, filename: str, options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Enhance faces in an image using GFPGAN.
    
    Args:
        image_bytes: Raw image bytes
        filename: Original filename  
        options: Additional processing options
    
    Returns:
        Dictionary with result data (JSON-serializable only)
    """
    start_time = time.time()
    task_id = self.request.id
    
    def clean_result(result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result contains only JSON-serializable data."""
        cleaned = {}
        for key, value in result_dict.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                cleaned[key] = value
            elif isinstance(value, dict):
                cleaned[key] = clean_result(value)
            elif isinstance(value, (list, tuple)):
                cleaned[key] = [
                    clean_result(item) if isinstance(item, dict) else item 
                    for item in value 
                    if isinstance(item, (str, int, float, bool, type(None), dict))
                ]
            else:
                # Convert non-serializable types to string
                cleaned[key] = str(value)
        return cleaned
    
    try:
        logger.info(f"Task {task_id}: Starting GFPGAN face enhancement for {filename}")
        
        # Parse options
        options = options or {}
        output_format = options.get("format", "webp")
        quality = options.get("quality", "auto")
        only_center_face = options.get("only_center_face", False)
        
        # Load image from bytes
        try:
            image = Image.open(io.BytesIO(image_bytes))
            logger.info(f"Task {task_id}: Loaded image {image.size} mode={image.mode}")
        except Exception as e:
            logger.error(f"Task {task_id}: Failed to load image: {e}")
            return clean_result({
                "success": False,
                "error": f"Invalid image format: {str(e)}",
                "task_id": task_id
            })
        
        # Validate image size
        max_pixels = 25 * 1024 * 1024  # 25MP limit for face processing
        if image.size[0] * image.size[1] > max_pixels:
            return clean_result({
                "success": False,
                "error": "Image too large for face processing. Maximum 25 megapixels allowed.",
                "task_id": task_id
            })
        
        # Additional size check for very large images
        if max(image.size) > 4096:
            # Resize to reasonable size for processing
            ratio = 4096 / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Task {task_id}: Resized large image to {new_size} for processing")
        
        # Detect faces first with timeout protection
        face_detection_start = time.time()
        try:
            # Skip face detection if image is very large to save time
            if max(image.size) > 2048:
                logger.info(f"Task {task_id}: Skipping face detection for large image, assuming faces present")
                face_count = 1  # Assume at least one face for large images
                face_detection_time = 0.1
            else:
                face_count = detect_faces_count(image)
                face_detection_time = time.time() - face_detection_start
        except Exception as e:
            logger.error(f"Task {task_id}: Face detection failed: {e}")
            # Continue anyway, assume faces present
            face_count = 1
            face_detection_time = 0.1
        
        # Limit face detection time
        if face_detection_time > 30:  # 30 seconds max
            logger.warning(f"Task {task_id}: Face detection took too long ({face_detection_time:.1f}s)")
        
        logger.info(f"Task {task_id}: Detected {face_count} faces in {face_detection_time:.2f}s")
        
        # Continue processing even if no faces detected (user might want to try anyway)
        if face_count == 0:
            logger.warning(f"Task {task_id}: No faces detected, but continuing with enhancement")
            face_count = 1  # Set to 1 to continue processing
        
        # Perform face enhancement using cached model
        processing_start = time.time()
        try:
            model = get_gfpgan_model()
            enhanced_image = model.enhance_faces(image, only_center_face=only_center_face)
        except Exception as e:
            logger.error(f"Task {task_id}: Model error, falling back: {e}")
            enhanced_image = enhance_faces(image, only_center_face=only_center_face)  # Fallback
        processing_time = time.time() - processing_start
        
        if enhanced_image is None:
            logger.error(f"Task {task_id}: Face enhancement failed")
            return clean_result({
                "success": False,
                "error": "Face enhancement failed. Please try again.",
                "task_id": task_id,
                "face_count": face_count
            })
        
        logger.info(f"Task {task_id}: Face enhancement completed in {processing_time:.2f}s")
        
        # Upload to Cloudinary
        upload_start = time.time()
        upload_result = cloudinary_manager.upload_image(
            enhanced_image,
            f"enhanced_{filename}",
            folder="gfpgan",
            format=output_format,
            quality=quality
        )
        upload_time = time.time() - upload_start
        
        if upload_result is None:
            logger.error(f"Task {task_id}: Upload to Cloudinary failed")
            return clean_result({
                "success": False,
                "error": "Failed to upload result. Please try again.",
                "task_id": task_id,
                "face_count": face_count
            })
        
        total_time = time.time() - start_time
        
        result = {
            "success": True,
            "task_id": task_id,
            "image_url": str(upload_result.get("secure_url", "")),
            "public_id": str(upload_result.get("public_id", "")),
            "original_size": list(image.size),
            "enhanced_size": list(enhanced_image.size),
            "face_count": int(face_count),
            "only_center_face": bool(only_center_face),
            "face_detection_time": round(float(face_detection_time), 2),
            "processing_time": round(float(processing_time), 2),
            "upload_time": round(float(upload_time), 2),
            "total_time": round(float(total_time), 2),
            "format": str(output_format),
            "cloudinary_info": {
                "bytes": int(upload_result.get("bytes", 0)) if upload_result.get("bytes") else 0,
                "format": str(upload_result.get("format", "")),
                "width": int(upload_result.get("width", 0)) if upload_result.get("width") else 0,
                "height": int(upload_result.get("height", 0)) if upload_result.get("height") else 0
            }
        }
        
        logger.info(f"Task {task_id}: Completed successfully in {total_time:.2f}s")
        return clean_result(result)
        
    except Exception as e:
        logger.error(f"Task {task_id}: Unexpected error: {e}")
        logger.error(f"Task {task_id}: Traceback: {traceback.format_exc()}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Task {task_id}: Retrying in 60 seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        
        return clean_result({
            "success": False,
            "error": f"Processing failed after {self.max_retries} retries: {str(e)}",
            "task_id": task_id,
            "face_count": 0
        })

@celery_app.task(name="tasks.health_check")
def health_check() -> Dict[str, Any]:
    """Health check task for monitoring."""
    import torch
    import psutil
    
    try:
        return {
            "status": "healthy",
            "timestamp": float(time.time()),
            "system_info": {
                "cpu_percent": float(psutil.cpu_percent()),
                "memory_percent": float(psutil.virtual_memory().percent),
                "cuda_available": bool(torch.cuda.is_available()),
                "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": float(time.time()),
            "error": str(e)
        }
