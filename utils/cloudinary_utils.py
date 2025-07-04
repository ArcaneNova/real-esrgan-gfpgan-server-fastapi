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
            
            # Optimize format based on image content
            if format == "auto":
                format = "webp" if image.mode in ["RGB", "RGBA"] else "png"
            
            # Save with optimization
            save_kwargs = {"format": format.upper()}
            if format.lower() in ["jpeg", "jpg"]:
                save_kwargs["quality"] = 95
                save_kwargs["optimize"] = True
            elif format.lower() == "webp":
                save_kwargs["quality"] = 90
                save_kwargs["method"] = 6
            elif format.lower() == "png":
                save_kwargs["optimize"] = True
                
            image.save(buffer, **save_kwargs)
            buffer.seek(0)
            
            # Generate public_id
            public_id = f"{folder}/{filename.split('.')[0]}"
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                buffer,
                public_id=public_id,
                folder=folder,
                resource_type="image",
                quality=quality,
                format=format,
                overwrite=True,
                transformation=[
                    {"quality": "auto:good"},
                    {"fetch_format": "auto"}
                ]
            )
            
            logger.info(f"Successfully uploaded {filename} to Cloudinary")
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
