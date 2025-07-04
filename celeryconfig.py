import os
from kombu import Queue

# Celery Configuration
broker_url = os.getenv('REDIS_BROKER', 'redis://localhost:6379/0')
result_backend = os.getenv('REDIS_BACKEND', 'redis://localhost:6379/0')

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 50

# Queue settings
task_routes = {
    'tasks.upscale_esrgan': {'queue': 'esrgan'},
    'tasks.enhance_gfpgan': {'queue': 'gfpgan'},
}

task_default_queue = 'default'
task_queues = (
    Queue('default'),
    Queue('esrgan'),
    Queue('gfpgan'),
)

# Result settings
result_expires = 3600  # 1 hour
result_persistent = True

# Retry settings
task_default_retry_delay = 60
task_max_retries = 3

# Concurrency settings
worker_concurrency = int(os.getenv('MAX_WORKERS', 2))

# Performance optimizations
task_compression = 'gzip'
result_compression = 'gzip'
worker_disable_rate_limits = True
