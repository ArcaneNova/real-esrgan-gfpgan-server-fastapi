#!/usr/bin/env python3
"""
Monitoring and metrics script for Image Upscaler SaaS
"""

import requests
import time
import json
import psutil
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.metrics = []
    
    def check_health(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "response_time": None,
                "status_code": None
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": psutil.net_io_counters()._asdict(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API statistics."""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get stats: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """Get active tasks information."""
        try:
            response = requests.get(f"{self.api_url}/tasks/active", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get active tasks: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics."""
        metrics = {
            "health": self.check_health(),
            "system": self.get_system_metrics(),
            "api_stats": self.get_api_stats(),
            "active_tasks": self.get_active_tasks()
        }
        
        self.metrics.append(metrics)
        return metrics
    
    def run_monitoring(self, interval: int = 60, duration: int = 3600):
        """Run continuous monitoring."""
        logger.info(f"Starting monitoring for {duration}s with {interval}s intervals")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                metrics = self.collect_metrics()
                
                # Log key metrics
                health_status = metrics["health"]["status"]
                cpu_percent = metrics["system"]["cpu_percent"]
                memory_percent = metrics["system"]["memory"]["percent"]
                
                logger.info(f"Health: {health_status}, CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%")
                
                # Check for alerts
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
                
                if memory_percent > 80:
                    logger.warning(f"High memory usage: {memory_percent:.1f}%")
                
                if health_status != "healthy":
                    logger.error(f"API unhealthy: {metrics['health']}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def save_metrics(self, filename: str = None):
        """Save collected metrics to file."""
        if not filename:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        logger.info(f"Metrics saved to {filename}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Image Upscaler SaaS API")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval (seconds)")
    parser.add_argument("--duration", type=int, default=3600, help="Monitoring duration (seconds)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--save", help="Save metrics to file")
    
    args = parser.parse_args()
    
    monitor = HealthMonitor(args.url)
    
    if args.once:
        metrics = monitor.collect_metrics()
        print(json.dumps(metrics, indent=2))
    else:
        try:
            monitor.run_monitoring(args.interval, args.duration)
        finally:
            if args.save:
                monitor.save_metrics(args.save)

if __name__ == "__main__":
    main()
