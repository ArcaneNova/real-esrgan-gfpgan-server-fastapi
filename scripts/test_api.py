#!/usr/bin/env python3
"""
Test script for Image Upscaler SaaS API
"""

import requests
import time
import json
from pathlib import Path
import argparse

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        print("✅ Health check passed")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_upscale(image_path: str):
    """Test the upscale endpoint."""
    print(f"🚀 Testing upscale with {image_path}...")
    
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'format': 'webp', 'quality': 'auto'}
        
        response = requests.post(f"{API_BASE_URL}/upscale", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        task_id = result['task_id']
        print(f"✅ Upscale task created: {task_id}")
        
        # Poll for result
        return poll_result(task_id)
    else:
        print(f"❌ Upscale request failed: {response.status_code} - {response.text}")
        return False

def test_face_enhance(image_path: str):
    """Test the face enhance endpoint."""
    print(f"😀 Testing face enhance with {image_path}...")
    
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'format': 'webp', 'quality': 'auto', 'only_center_face': 'false'}
        
        response = requests.post(f"{API_BASE_URL}/face-enhance", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        task_id = result['task_id']
        print(f"✅ Face enhance task created: {task_id}")
        
        # Poll for result
        return poll_result(task_id)
    else:
        print(f"❌ Face enhance request failed: {response.status_code} - {response.text}")
        return False

def poll_result(task_id: str, max_wait: int = 120):
    """Poll for task result."""
    print(f"⏳ Polling for result of task {task_id}...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(f"{API_BASE_URL}/result/{task_id}")
        
        if response.status_code == 200:
            result = response.json()
            status = result['status']
            
            if status == 'completed':
                print(f"✅ Task completed successfully!")
                task_result = result['result']
                if task_result.get('success'):
                    print(f"🖼️  Result URL: {task_result['image_url']}")
                    print(f"⏱️  Processing time: {task_result.get('total_time', 'N/A')}s")
                    return True
                else:
                    print(f"❌ Task failed: {task_result.get('error', 'Unknown error')}")
                    return False
            elif status == 'failed':
                print(f"❌ Task failed: {result.get('error', 'Unknown error')}")
                return False
            else:
                print(f"⏳ Status: {status} - waiting...")
                time.sleep(5)
        else:
            print(f"❌ Failed to get result: {response.status_code}")
            return False
    
    print(f"⏰ Timeout waiting for result after {max_wait}s")
    return False

def test_stats():
    """Test the stats endpoint."""
    print("📊 Testing stats endpoint...")
    response = requests.get(f"{API_BASE_URL}/stats")
    if response.status_code == 200:
        stats = response.json()
        print("✅ Stats retrieved successfully")
        print(f"🧠 Memory usage: {stats['system']['memory']['percent']:.1f}%")
        print(f"💻 CPU usage: {stats['system']['cpu_percent']:.1f}%")
        print(f"🚀 CUDA available: {stats['gpu']['cuda_available']}")
        return True
    else:
        print(f"❌ Stats request failed: {response.status_code}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Image Upscaler SaaS API")
    parser.add_argument("--upscale", type=str, help="Path to image for upscale test")
    parser.add_argument("--face-enhance", type=str, help="Path to image for face enhance test")
    parser.add_argument("--all", action="store_true", help="Run all tests (requires sample images)")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    global API_BASE_URL
    API_BASE_URL = args.url
    
    print("🧪 Image Upscaler SaaS API Test Suite")
    print(f"🌐 API URL: {API_BASE_URL}")
    print("=" * 50)
    
    # Always test health first
    if not test_health():
        print("❌ API is not healthy. Exiting.")
        return
    
    print()
    
    # Test stats
    test_stats()
    print()
    
    if args.upscale:
        test_upscale(args.upscale)
        print()
    
    if args.face_enhance:
        test_face_enhance(args.face_enhance)
        print()
    
    if args.all:
        print("🔄 Running all tests...")
        # You would need to provide sample images for this
        sample_images = ["test_image.jpg", "test_face.jpg"]
        for img in sample_images:
            if Path(img).exists():
                test_upscale(img)
                test_face_enhance(img)
                print()
    
    print("✅ Test suite completed!")

if __name__ == "__main__":
    main()
