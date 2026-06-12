#!/usr/bin/env python3
"""
Simple test script to verify Celery task files exist
"""

import os
import sys

def test_celery_files():
    """Test that all Celery task files exist."""
    
    print("Testing Celery task files...")
    
    # Check if files exist
    files_to_check = [
        'backend/celery_worker.py',
        'backend/app/workers/celery_config.py',
        'backend/app/workers/analysis_tasks.py',
        'backend/app/workers/export_tasks.py',
        'backend/app/workers/notification_tasks.py',
        'backend/app/workers/plugin_tasks.py',
        'backend/app/workers/form_tasks.py',
        'backend/app/workers/sync_tasks.py',
        'backend/app/workers/maintenance_tasks.py',
        'backend/app/workers/quota_tasks.py',
        'backend/app/services/task_status_service.py',
        'docs/CELERY_TASKS.md',
        'docs/CELERY_IMPLEMENTATION_SUMMARY.md',
        'scripts/test_celery_tasks.py'
    ]
    
    missing_files = []
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n✗ Missing {len(missing_files)} files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    # Check file sizes (should be non-empty)
    print(f"\nChecking file sizes...")
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 0:
                print(f"✓ {file_path} ({size} bytes)")
            else:
                print(f"✗ {file_path} is empty")
                missing_files.append(file_path)
    
    if missing_files:
        return False
    
    print(f"\n🎉 All {len(files_to_check)} Celery task files exist and are non-empty!")
    return True

if __name__ == "__main__":
    success = test_celery_files()
    sys.exit(0 if success else 1)