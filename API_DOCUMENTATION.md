# API Documentation - Image Upscaler SaaS

## Overview

The Image Upscaler SaaS provides two main AI-powered image processing services:

1. **Real-ESRGAN Upscaling** - Enhance image resolution by 4x
2. **GFPGAN Face Enhancement** - Restore and enhance faces in images

## Base URL

- Local Development: `http://localhost:8000`
- Production: Your Railway deployment URL

## Authentication

Currently, no authentication is required. In production, you should implement:
- API key authentication
- Rate limiting
- User quotas

## Endpoints

### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "startup_complete": true,
  "timestamp": 1704461234.567,
  "version": "1.0.0"
}
```

### Image Upscaling

**POST** `/upscale`

Upscale an image using Real-ESRGAN.

**Parameters:**
- `file` (file, required): Image file (JPEG, PNG, WebP, max 50MB)
- `format` (string, optional): Output format (`webp`, `png`, `jpeg`) - default: `webp`
- `quality` (string, optional): Output quality (`auto`, `high`, `medium`, `low`) - default: `auto`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/upscale" \
  -F "file=@image.jpg" \
  -F "format=webp" \
  -F "quality=auto"
```

**Response:**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Image upscaling started",
  "image_info": {
    "filename": "image.jpg",
    "dimensions": [1024, 768],
    "mode": "RGB",
    "format": "JPEG"
  },
  "options": {
    "format": "webp",
    "quality": "auto"
  },
  "estimated_time": "2-5 seconds"
}
```

### Face Enhancement

**POST** `/face-enhance`

Enhance faces in an image using GFPGAN.

**Parameters:**
- `file` (file, required): Image file with faces (max 25MB)
- `format` (string, optional): Output format - default: `webp`
- `quality` (string, optional): Output quality - default: `auto`
- `only_center_face` (boolean, optional): Only enhance center face - default: `false`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/face-enhance" \
  -F "file=@portrait.jpg" \
  -F "format=webp" \
  -F "only_center_face=false"
```

**Response:**
```json
{
  "success": true,
  "task_id": "xyz789-abc123-def456",
  "status": "queued",
  "message": "Face enhancement started",
  "image_info": {
    "filename": "portrait.jpg",
    "dimensions": [800, 600],
    "mode": "RGB"
  },
  "estimated_time": "3-8 seconds"
}
```

### Get Task Result

**GET** `/result/{task_id}`

Get the result of a processing task.

**Example Request:**
```bash
curl "http://localhost:8000/result/abc123-def456-ghi789"
```

**Response (Processing):**
```json
{
  "success": true,
  "status": "processing",
  "task_id": "abc123-def456-ghi789",
  "message": "Task is still being processed"
}
```

**Response (Completed):**
```json
{
  "success": true,
  "status": "completed",
  "task_id": "abc123-def456-ghi789",
  "result": {
    "success": true,
    "image_url": "https://res.cloudinary.com/your-cloud/image/upload/v1704461234/realesrgan/upscaled_image.webp",
    "public_id": "realesrgan/upscaled_image",
    "original_size": [1024, 768],
    "upscaled_size": [4096, 3072],
    "scale_factor": 4.0,
    "processing_time": 3.45,
    "upload_time": 0.89,
    "total_time": 4.34,
    "format": "webp",
    "cloudinary_info": {
      "bytes": 524288,
      "format": "webp",
      "width": 4096,
      "height": 3072
    }
  }
}
```

**Response (Failed):**
```json
{
  "success": false,
  "status": "failed",
  "task_id": "abc123-def456-ghi789",
  "error": "No faces detected in the image."
}
```

### Active Tasks

**GET** `/tasks/active`

Get information about currently active tasks.

**Response:**
```json
{
  "success": true,
  "active_tasks": {
    "esrgan@worker1": [
      {
        "id": "abc123-def456-ghi789",
        "name": "tasks.upscale_esrgan",
        "time_start": 1704461234.567
      }
    ],
    "gfpgan@worker2": []
  },
  "timestamp": 1704461234.567
}
```

### System Statistics

**GET** `/stats`

Get system and queue statistics.

**Response:**
```json
{
  "success": true,
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "total": 8589934592,
      "available": 4294967296,
      "percent": 50.0
    },
    "disk": {
      "total": 107374182400,
      "free": 53687091200,
      "percent": 50.0
    }
  },
  "gpu": {
    "cuda_available": true,
    "device_count": 1,
    "memory": {
      "allocated": 1073741824,
      "cached": 2147483648
    }
  },
  "celery": {
    "active_tasks": {},
    "scheduled_tasks": {},
    "reserved_tasks": {}
  },
  "timestamp": 1704461234.567
}
```

## Error Responses

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `413` - Payload Too Large (file too big)
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limits

Default rate limits (can be configured):
- 100 requests per minute per IP
- 10 concurrent processing tasks per IP

## File Limits

- **Upscaling**: Max 50MB, up to 50 megapixels
- **Face Enhancement**: Max 25MB, up to 25 megapixels
- **Supported Formats**: JPEG, PNG, WebP
- **Output Formats**: WebP (recommended), PNG, JPEG

## Processing Times

Typical processing times on a 4-core CPU:
- **Upscaling**: 2-5 seconds for 1MP image
- **Face Enhancement**: 3-8 seconds depending on face count

## Best Practices

1. **Use WebP format** for optimal file size and quality
2. **Check task status** regularly using the result endpoint
3. **Handle timeouts** gracefully (max 2 minutes)
4. **Validate images** before upload to avoid errors
5. **Monitor system resources** using the stats endpoint

## SDKs and Examples

### Python SDK Example

```python
import requests
import time

class ImageUpscalerClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def upscale_image(self, image_path, format="webp"):
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {'format': format}
            response = requests.post(f"{self.base_url}/upscale", files=files, data=data)
        
        if response.status_code == 200:
            return response.json()['task_id']
        else:
            raise Exception(f"Upload failed: {response.text}")
    
    def get_result(self, task_id, timeout=120):
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/result/{task_id}")
            result = response.json()
            
            if result['status'] == 'completed':
                return result['result']
            elif result['status'] == 'failed':
                raise Exception(f"Processing failed: {result.get('error')}")
            
            time.sleep(5)
        
        raise Exception("Timeout waiting for result")

# Usage
client = ImageUpscalerClient()
task_id = client.upscale_image("my_image.jpg")
result = client.get_result(task_id)
print(f"Upscaled image URL: {result['image_url']}")
```

### JavaScript/Node.js Example

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

class ImageUpscalerClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async upscaleImage(imagePath, format = 'webp') {
        const form = new FormData();
        form.append('file', fs.createReadStream(imagePath));
        form.append('format', format);
        
        const response = await axios.post(`${this.baseUrl}/upscale`, form, {
            headers: form.getHeaders()
        });
        
        return response.data.task_id;
    }
    
    async getResult(taskId, timeout = 120000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            const response = await axios.get(`${this.baseUrl}/result/${taskId}`);
            const result = response.data;
            
            if (result.status === 'completed') {
                return result.result;
            } else if (result.status === 'failed') {
                throw new Error(`Processing failed: ${result.error}`);
            }
            
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
        
        throw new Error('Timeout waiting for result');
    }
}

// Usage
(async () => {
    const client = new ImageUpscalerClient();
    const taskId = await client.upscaleImage('my_image.jpg');
    const result = await client.getResult(taskId);
    console.log(`Upscaled image URL: ${result.image_url}`);
})();
```

## Interactive Documentation

Visit `/docs` for interactive API documentation powered by FastAPI's automatic OpenAPI generation.
