import cloudinary
import cloudinary.uploader
from io import BytesIO
from PIL import Image
from typing import Optional, Dict, Any
import logging
from config import settings

logger = logging.getLogger(__name__)

class CloudinaryManager:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True
        )
    
    def upload_image(self, 
                    image: Image.Image, 
                    filename: str,
                    folder: str = "upscaled",
                    quality: str = "auto",
                    format: str = "webp") -> Optional[Dict[str, Any]]:
        """Upload an image to Cloudinary and return the result."""
        try:
            # Convert PIL Image to bytes
            buffer = BytesIO()
            
            # Normalize format and set save parameters
            format_lower = format.lower()
            if format_lower in ["jpg", "jpeg"]:
                save_format = "JPEG"
                cloudinary_format = "jpg"
                save_kwargs = {"format": "JPEG", "quality": 95, "optimize": True}
            elif format_lower == "png":
                save_format = "PNG"
                cloudinary_format = "png"
                save_kwargs = {"format": "PNG", "optimize": True}
            else:
                save_format = "WEBP"
                cloudinary_format = "webp"
                save_kwargs = {"format": "WEBP", "quality": 90, "method": 6}
            
            # Ensure image is in correct mode for the format
            if save_format == "JPEG":
                # JPEG doesn't support transparency
                if image.mode in ["RGBA", "LA", "P"]:
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    if image.mode in ["RGBA", "LA"]:
                        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                    image = background
                elif image.mode not in ["RGB", "L"]:
                    image = image.convert("RGB")
            elif save_format == "PNG":
                # PNG supports transparency
                if image.mode not in ["RGB", "RGBA", "L", "LA", "P"]:
                    image = image.convert("RGBA")
            else:  # WEBP
                # WEBP supports transparency
                if image.mode not in ["RGB", "RGBA"]:
                    image = image.convert("RGB")
                
            # Save image to buffer
            image.save(buffer, **save_kwargs)
            buffer.seek(0)
            
            # Generate clean public_id
            base_name = filename.split('.')[0] if '.' in filename else filename
            # Remove any problematic characters
            safe_base_name = "".join(c for c in base_name if c.isalnum() or c in "._-")
            public_id = f"{folder}/{safe_base_name}"
            
            # Upload to Cloudinary with explicit format
            upload_result = cloudinary.uploader.upload(
                buffer,
                public_id=public_id,
                folder=folder,
                resource_type="image",
                format=cloudinary_format,
                overwrite=True,
                quality="auto:good",
                use_filename=False,  # Don't use original filename
                unique_filename=True  # Generate unique name
            )
            
            logger.info(f"Successfully uploaded {filename} to Cloudinary as {save_format}")
            return upload_result
            
        except Exception as e:
            logger.error(f"Failed to upload {filename} to Cloudinary: {e}")
            return None
    
    def get_optimized_url(self, 
                         public_id: str, 
                         width: Optional[int] = None,
                         height: Optional[int] = None,
                         quality: str = "auto:good") -> str:
        """Get an optimized URL for an uploaded image."""
        try:
            transformations = [{"quality": quality, "fetch_format": "auto"}]
            
            if width or height:
                resize_params = {}
                if width:
                    resize_params["width"] = width
                if height:
                    resize_params["height"] = height
                resize_params["crop"] = "scale"
                transformations.append(resize_params)
            
            url = cloudinary.CloudinaryImage(public_id).build_url(
                transformation=transformations
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate optimized URL for {public_id}: {e}")
            return ""
    
    def delete_image(self, public_id: str) -> bool:
        """Delete an image from Cloudinary."""
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Failed to delete {public_id} from Cloudinary: {e}")
            return False

# Global instance
cloudinary_manager = CloudinaryManager()
