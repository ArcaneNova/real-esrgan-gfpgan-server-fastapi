#!/usr/bin/env python3
"""
Quick health check script for the Image Upscaler API
"""

import requests
import time
import json

def check_api_health(base_url="http://localhost:8000"):
    """Quick health check of the API."""
    print("🏥 Checking API health...")
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ API is healthy")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Startup complete: {health_data.get('startup_complete', 'unknown')}")
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    try:
        # Test stats endpoint (simplified)
        response = requests.get(f"{base_url}/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            if stats.get("success"):
                print("✅ Stats endpoint working")
                system = stats.get("system", {})
                print(f"   CPU: {system.get('cpu_percent', 'N/A')}%")
                print(f"   Memory: {system.get('memory', {}).get('percent', 'N/A')}%")
                
                celery = stats.get("celery", {})
                print(f"   Workers online: {celery.get('workers_online', 'N/A')}")
                print(f"   Active tasks: {celery.get('active_task_count', 'N/A')}")
            else:
                print("⚠️ Stats endpoint returned error")
        else:
            print(f"⚠️ Stats check failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Stats check failed: {e}")
    
    try:
        # Test tasks endpoint
        response = requests.get(f"{base_url}/tasks/active", timeout=10)
        if response.status_code == 200:
            print("✅ Tasks endpoint working")
        else:
            print(f"⚠️ Tasks endpoint failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Tasks endpoint failed: {e}")
    
    print(f"\n🌐 API URL: {base_url}")
    print(f"📚 API Docs: {base_url}/docs")
    return True

if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("🔍 Image Upscaler API Health Check")
    print("=" * 40)
    
    if check_api_health(base_url):
        print("\n🎉 API is ready for use!")
    else:
        print("\n💥 API has issues. Check the logs.")
        sys.exit(1)
