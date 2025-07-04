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

@celery_app.task(name="tasks.upscale_esrgan", bind=True, max_retries=3)
def upscale_esrgan(self, image_bytes: bytes, filename: str, options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Upscale an image using Real-ESRGAN.
    
    Args:
        image_bytes: Raw image bytes
        filename: Original filename
        options: Additional processing options
    
    Returns:
        Dictionary with result data
    """
    start_time = time.time()
    task_id = self.request.id
    
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
            return {
                "success": False,
                "error": f"Invalid image format: {str(e)}",
                "task_id": task_id
            }
        
        # Validate image size (prevent memory issues)
        max_pixels = 5 * 1024 * 1024  # 50MP limit
        if image.size[0] * image.size[1] > max_pixels:
            return {
                "success": False,
                "error": "Image too large. Maximum 5 megapixels allowed.",
                "task_id": task_id
            }
        
        # Perform upscaling
        processing_start = time.time()
        upscaled_image = upscale_image(image)
        processing_time = time.time() - processing_start
        
        if upscaled_image is None:
            logger.error(f"Task {task_id}: Upscaling failed")
            return {
                "success": False,
                "error": "Upscaling failed. Please try again.",
                "task_id": task_id
            }
        
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
            return {
                "success": False,
                "error": "Failed to upload result. Please try again.",
                "task_id": task_id
            }
        
        total_time = time.time() - start_time
        
        result = {
            "success": True,
            "task_id": task_id,
            "image_url": upload_result["secure_url"],
            "public_id": upload_result["public_id"],
            "original_size": image.size,
            "upscaled_size": upscaled_image.size,
            "scale_factor": upscaled_image.size[0] / image.size[0],
            "processing_time": round(processing_time, 2),
            "upload_time": round(upload_time, 2),
            "total_time": round(total_time, 2),
            "format": output_format,
            "cloudinary_info": {
                "bytes": upload_result.get("bytes"),
                "format": upload_result.get("format"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height")
            }
        }
        
        logger.info(f"Task {task_id}: Completed successfully in {total_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Task {task_id}: Unexpected error: {e}")
        logger.error(f"Task {task_id}: Traceback: {traceback.format_exc()}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Task {task_id}: Retrying in 60 seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        
        return {
            "success": False,
            "error": f"Processing failed after {self.max_retries} retries: {str(e)}",
            "task_id": task_id
        }

@celery_app.task(name="tasks.enhance_gfpgan", bind=True, max_retries=3)
def enhance_gfpgan(self, image_bytes: bytes, filename: str, options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Enhance faces in an image using GFPGAN.
    
    Args:
        image_bytes: Raw image bytes
        filename: Original filename  
        options: Additional processing options
    
    Returns:
        Dictionary with result data
    """
    start_time = time.time()
    task_id = self.request.id
    
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
            return {
                "success": False,
                "error": f"Invalid image format: {str(e)}",
                "task_id": task_id
            }
        
        # Validate image size
        max_pixels = 25 * 1024 * 1024  # 25MP limit for face processing
        if image.size[0] * image.size[1] > max_pixels:
            return {
                "success": False,
                "error": "Image too large for face processing. Maximum 25 megapixels allowed.",
                "task_id": task_id
            }
        
        # Detect faces first
        face_detection_start = time.time()
        face_count = detect_faces_count(image)
        face_detection_time = time.time() - face_detection_start
        
        logger.info(f"Task {task_id}: Detected {face_count} faces in {face_detection_time:.2f}s")
        
        if face_count == 0:
            return {
                "success": False,
                "error": "No faces detected in the image.",
                "task_id": task_id,
                "face_count": 0
            }
        
        # Perform face enhancement
        processing_start = time.time()
        enhanced_image = enhance_faces(image, only_center_face=only_center_face)
        processing_time = time.time() - processing_start
        
        if enhanced_image is None:
            logger.error(f"Task {task_id}: Face enhancement failed")
            return {
                "success": False,
                "error": "Face enhancement failed. Please try again.",
                "task_id": task_id,
                "face_count": face_count
            }
        
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
            return {
                "success": False,
                "error": "Failed to upload result. Please try again.",
                "task_id": task_id,
                "face_count": face_count
            }
        
        total_time = time.time() - start_time
        
        result = {
            "success": True,
            "task_id": task_id,
            "image_url": upload_result["secure_url"],
            "public_id": upload_result["public_id"],
            "original_size": image.size,
            "enhanced_size": enhanced_image.size,
            "face_count": face_count,
            "only_center_face": only_center_face,
            "face_detection_time": round(face_detection_time, 2),
            "processing_time": round(processing_time, 2),
            "upload_time": round(upload_time, 2),
            "total_time": round(total_time, 2),
            "format": output_format,
            "cloudinary_info": {
                "bytes": upload_result.get("bytes"),
                "format": upload_result.get("format"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height")
            }
        }
        
        logger.info(f"Task {task_id}: Completed successfully in {total_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Task {task_id}: Unexpected error: {e}")
        logger.error(f"Task {task_id}: Traceback: {traceback.format_exc()}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Task {task_id}: Retrying in 60 seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        
        return {
            "success": False,
            "error": f"Processing failed after {self.max_retries} retries: {str(e)}",
            "task_id": task_id,
            "face_count": 0
        }

@celery_app.task(name="tasks.health_check")
def health_check() -> Dict[str, Any]:
    """Health check task for monitoring."""
    import torch
    import psutil
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system_info": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
    }
