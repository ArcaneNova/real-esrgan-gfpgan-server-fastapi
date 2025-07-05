#!/usr/bin/env python3
"""
Test script to verify Real-ESRGAN model architecture fix.
This script tests model loading with the correct architecture.
"""

import sys
import os
sys.path.append('/server-api')

from PIL import Image
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_realesrgan_model():
    """Test Real-ESRGAN model loading and basic inference."""
    try:
        from inference.realesrgan_inference import RealESRGANInference
        
        print("Testing Real-ESRGAN model architecture fix...")
        
        # Initialize with the problematic model
        upscaler = RealESRGANInference(model_name="realesrgan_general_x4v3")
        
        # Try to load the model
        print("Loading model...")
        if not upscaler.load_model():
            print("❌ Failed to load model")
            return False
        
        print("✅ Model loaded successfully!")
        
        # Create a small test image
        test_image = Image.fromarray(np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8))
        
        # Try upscaling
        print("Testing upscaling...")
        result = upscaler.upscale(test_image)
        
        if result is None:
            print("❌ Upscaling failed")
            return False
        
        print(f"✅ Upscaling successful! Output size: {result.size}")
        
        # Clean up
        upscaler.unload_model()
        print("✅ Model unloaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_realesrgan_model()
    if success:
        print("\n🎉 All tests passed! Real-ESRGAN architecture fix is working.")
    else:
        print("\n💥 Tests failed. Need to investigate further.")
    
    sys.exit(0 if success else 1)
