#!/usr/bin/env python3
"""
Celery Worker Entry Point
Main entry point for all Celery background tasks.
"""

import os
from celery import Celery
from app.config import get_config

# Get configuration
config = get_config()

# Create Celery app
celery_app = Celery(
    'form_builder',
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=[
        'app.workers.analysis_tasks',
        'app.workers.export_tasks', 
        'app.workers.notification_tasks',
        'app.workers.plugin_tasks',
        'app.workers.form_tasks',
        'app.workers.sync_tasks',
        'app.workers.maintenance_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task configuration
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Result backend configuration
    result_expires=3600,  # 1 hour
    
    # Beat scheduler configuration
    beat_schedule={
        'nightly-maintenance': {
            'task': 'app.workers.maintenance_tasks.nightly_maintenance_task',
            'schedule': 3600.0 * 24,  # Daily
        },
        'quota-calculation': {
            'task': 'app.workers.maintenance_tasks.calculate_all_quotas_task', 
            'schedule': 3600.0 * 6,  # Every 6 hours
        },
        'scheduled-analyses': {
            'task': 'app.workers.analysis_tasks.run_scheduled_analyses_task',
            'schedule': 60.0,  # Every minute
        },
        'cleanup-expired-exports': {
            'task': 'app.workers.maintenance_tasks.cleanup_expired_exports_task',
            'schedule': 3600.0 * 12,  # Every 12 hours
        },
        'cleanup-expired-drafts': {
            'task': 'app.workers.maintenance_tasks.cleanup_expired_drafts_task',
            'schedule': 3600.0 * 24,  # Daily
        }
    },
    beat_max_loop_interval=300,  # 5 minutes
    
    # Routing configuration (for future scaling)
    task_routes={
        'app.workers.analysis_tasks.*': {'queue': 'analysis'},
        'app.workers.export_tasks.*': {'queue': 'exports'},
        'app.workers.notification_tasks.*': {'queue': 'notifications'},
        'app.workers.plugin_tasks.*': {'queue': 'plugins'},
        'app.workers.form_tasks.*': {'queue': 'forms'},
        'app.workers.sync_tasks.*': {'queue': 'sync'},
        'app.workers.maintenance_tasks.*': {'queue': 'maintenance'},
    },
    
    # Concurrency configuration
    worker_concurrency=os.environ.get('CELERY_CONCURRENCY', 4),
)

if __name__ == '__main__':
    celery_app.start()