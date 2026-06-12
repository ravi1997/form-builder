#!/usr/bin/env python3
"""
Test script to verify Celery task configuration
"""

import os
import sys

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def test_celery_tasks():
    """Test that all Celery tasks can be imported and configured."""
    
    print("Testing Celery task configuration...")
    
    try:
        # Test importing Celery app
        from backend.app.workers.celery_config import get_celery_app
        celery_app = get_celery_app()
        print("✓ Celery app configured successfully")
        
        # Test importing all task modules
        task_modules = [
            'backend.app.workers.analysis_tasks',
            'backend.app.workers.export_tasks',
            'backend.app.workers.notification_tasks',
            'backend.app.workers.plugin_tasks',
            'backend.app.workers.form_tasks',
            'backend.app.workers.sync_tasks',
            'backend.app.workers.maintenance_tasks',
            'backend.app.workers.quota_tasks'
        ]
        
        for module_name in task_modules:
            try:
                __import__(module_name)
                print(f"✓ {module_name} imported successfully")
            except ImportError as e:
                print(f"✗ Failed to import {module_name}: {e}")
                return False
        
        # Test that tasks are registered
        tasks = celery_app.tasks
        expected_tasks = [
            'app.workers.analysis_tasks.run_analysis_graph_task',
            'app.workers.analysis_tasks.run_scheduled_analyses_task',
            'app.workers.export_tasks.generate_csv_export_task',
            'app.workers.export_tasks.generate_excel_export_task',
            'app.workers.export_tasks.generate_pdf_export_task',
            'app.workers.notification_tasks.send_email_task',
            'app.workers.notification_tasks.send_sms_task',
            'app.workers.plugin_tasks.execute_plugin_task',
            'app.workers.plugin_tasks.install_plugin_task',
            'app.workers.plugin_tasks.uninstall_plugin_task',
            'app.workers.form_tasks.process_form_response_task',
            'app.workers.form_tasks.create_form_commit_task',
            'app.workers.form_tasks.publish_form_task',
            'app.workers.form_tasks.merge_form_branch_task',
            'app.workers.sync_tasks.process_offline_sync_task',
            'app.workers.sync_tasks.generate_sync_data_task',
            'app.workers.sync_tasks.resolve_sync_conflict_task',
            'app.workers.maintenance_tasks.nightly_maintenance_task',
            'app.workers.maintenance_tasks.cleanup_expired_exports_task',
            'app.workers.maintenance_tasks.cleanup_expired_drafts_task',
            'app.workers.maintenance_tasks.calculate_all_quotas_task',
            'app.workers.quota_tasks.calculate_organization_quota_task'
        ]
        
        missing_tasks = []
        for task_name in expected_tasks:
            if task_name not in tasks:
                missing_tasks.append(task_name)
        
        if missing_tasks:
            print(f"✗ Missing tasks: {missing_tasks}")
            return False
        else:
            print(f"✓ All {len(expected_tasks)} tasks registered successfully")
        
        # Test worker configuration
        from backend.celery_worker import celery_app as worker_app
        print("✓ Celery worker configured successfully")
        
        # Test beat schedule
        beat_schedule = worker_app.conf.beat_schedule
        expected_schedules = [
            'nightly-maintenance',
            'quota-calculation',
            'scheduled-analyses',
            'cleanup-expired-exports',
            'cleanup-expired-drafts'
        ]
        
        missing_schedules = []
        for schedule_name in expected_schedules:
            if schedule_name not in beat_schedule:
                missing_schedules.append(schedule_name)
        
        if missing_schedules:
            print(f"✗ Missing beat schedules: {missing_schedules}")
            return False
        else:
            print(f"✓ All {len(expected_schedules)} beat schedules configured")
        
        print("\n🎉 All Celery task configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing Celery configuration: {e}")
        return False

if __name__ == "__main__":
    success = test_celery_tasks()
    sys.exit(0 if success else 1)