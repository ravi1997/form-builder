"""
Celery Configuration
Shared Celery app configuration for all task modules.
"""

import os
from celery import Celery

# Global Celery app instance
_celery_app = None


def get_celery_app():
    """
    Get the global Celery app instance.
    Creates it if it doesn't exist.
    """
    global _celery_app
    
    if _celery_app is None:
        redis_uri = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
        _celery_app = Celery("form_builder_tasks", broker=redis_uri, backend=redis_uri)
        
        # Configure the app
        _celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            
            # Task configuration
            task_default_retry_delay=60,
            task_max_retries=3,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
            
            # Result backend
            result_expires=3600,
        )
    
    return _celery_app


def get_celery_worker_config():
    """
    Get Celery worker configuration.
    """
    return {
        "broker_url": os.environ.get("REDIS_URI", "redis://localhost:6379/0"),
        "result_backend": os.environ.get("REDIS_URI", "redis://localhost:6379/0"),
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_default_retry_delay": 60,
        "task_max_retries": 3,
        "task_acks_late": True,
        "worker_prefetch_multiplier": 1,
        "result_expires": 3600,
        "worker_concurrency": int(os.environ.get("CELERY_CONCURRENCY", 4)),
    }