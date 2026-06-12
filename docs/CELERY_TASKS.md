# Celery Tasks Documentation

This document describes all Celery background tasks implemented for the Form Builder Platform.

## Overview

The Celery task system handles all background processing including:
- Analysis execution with error isolation
- Export generation (CSV, Excel, PDF)
- Notification delivery with retry logic
- Plugin subprocess management
- Form versioning operations
- Scheduled analysis runs
- Maintenance tasks (cleanup, optimization)

## Task Categories

### 1. Analysis Tasks (`analysis_tasks.py`)

#### `run_analysis_graph_task`
- **Purpose**: Execute an analysis pipeline graph with error isolation
- **Parameters**: `analysis_run_id` (string)
- **Retry**: Yes, up to 3 times with exponential backoff
- **Error Handling**: Failing nodes don't stop other nodes (error isolation)
- **Status Tracking**: Updates `analysis_runs` and `analysis_results` collections

#### `run_scheduled_analyses_task`
- **Purpose**: Run all analyses that are scheduled for execution
- **Parameters**: None
- **Schedule**: Every minute (configured in celery_worker.py)
- **Trigger**: Finds analyses with `scheduled` execution mode and checks if they should run

### 2. Export Tasks (`export_tasks.py`)

#### `generate_csv_export_task`
- **Purpose**: Generate CSV export from analysis results
- **Parameters**: `analysis_id`, `node_ids`, `export_id`, `org_id`, `created_by`
- **Retry**: Yes, up to 3 times with exponential backoff
- **Output**: CSV file stored in uploads directory

#### `generate_excel_export_task`
- **Purpose**: Generate Excel export with multiple sheets from analysis results
- **Parameters**: `analysis_id`, `node_ids`, `export_id`, `org_id`, `created_by`
- **Retry**: Yes, up to 3 times with exponential backoff
- **Output**: Excel file with each node's data in separate sheets

#### `generate_pdf_export_task`
- **Purpose**: Generate PDF export from analysis results using WeasyPrint
- **Parameters**: `analysis_id`, `node_ids`, `export_id`, `org_id`, `created_by`, `template_data`
- **Retry**: Yes, up to 3 times with exponential backoff
- **Output**: PDF file with formatted data and branding

### 3. Notification Tasks (`notification_tasks.py`)

#### `send_email_task`
- **Purpose**: Send email notifications via AIIMS email API
- **Parameters**: `log_id`, `recipient_email`, `subject`, `body_html`, `body_text`
- **Retry**: Yes, automatic retry on failure with 60-second backoff
- **Error Handling**: Logs delivery attempts and notifies admins on non-retriable errors

#### `send_sms_task`
- **Purpose**: Send SMS notifications via AIIMS SMS API
- **Parameters**: `log_id`, `recipient_phone`, `message`
- **Retry**: Yes, automatic retry on failure with 60-second backoff
- **Error Handling**: Handles specific error codes (INVALID_NUMBER, BLACKLISTED, etc.)

### 4. Plugin Tasks (`plugin_tasks.py`)

#### `execute_plugin_task`
- **Purpose**: Execute a plugin component in a secure subprocess
- **Parameters**: `plugin_id`, `plugin_version`, `component_type`, `input_data`, `execution_context`
- **Security**: Runs in isolated subprocess with restricted environment
- **Timeout**: 30 seconds (configurable via `PLUGIN_TIMEOUT` env var)
- **Retry**: Yes, up to 2 times with 30-second backoff

#### `install_plugin_task`
- **Purpose**: Install a plugin from uploaded file
- **Parameters**: `plugin_id`, `plugin_file_path`, `installed_by`, `org_id`
- **Process**: Validates manifest, registers components, copies files to permanent location
- **Database Updates**: Creates plugin, version, and component schema records

#### `uninstall_plugin_task`
- **Purpose**: Uninstall a plugin and clean up its records
- **Parameters**: `plugin_id`, `uninstalled_by`
- **Process**: Marks plugin and components as deleted (soft delete)
- **Safety**: Doesn't delete files immediately (handled by maintenance tasks)

### 5. Form Tasks (`form_tasks.py`)

#### `process_form_response_task`
- **Purpose**: Process a submitted form response including calculations and validations
- **Parameters**: `response_id`
- **Processing**: Executes calculations, validates answers, triggers webhooks
- **Retry**: Yes, up to 3 times with exponential backoff

#### `create_form_commit_task`
- **Purpose**: Create a new form commit
- **Parameters**: `form_id`, `schema`, `author_id`, `message`, `branch`
- **Process**: Generates commit ID, stores schema, updates form branches

#### `publish_form_task`
- **Purpose**: Publish a form branch to production
- **Parameters**: `form_id`, `branch`, `published_by`
- **Process**: Updates production branch, logs audit event

#### `merge_form_branch_task`
- **Purpose**: Merge form branches with conflict resolution
- **Parameters**: `form_id`, `source_branch`, `target_branch`, `merger_id`, `merge_message`
- **Process**: Performs three-way merge, creates pending merge record on conflicts

#### `cleanup_old_response_drafts_task`
- **Purpose**: Clean up expired response drafts (older than 30 days)
- **Parameters**: None
- **Schedule**: Can be run manually or scheduled

### 6. Sync Tasks (`sync_tasks.py`)

#### `process_offline_sync_task`
- **Purpose**: Process offline synchronization data from client
- **Parameters**: `user_id`, `sync_data`
- **Conflict Resolution**: Detects version conflicts and provides resolution options
- **Retry**: Yes, up to 3 times with exponential backoff

#### `generate_sync_data_task`
- **Purpose**: Generate sync data for a user since their last sync
- **Parameters**: `user_id`, `last_sync_version`
- **Output**: Includes form schemas, user responses, and drafts

#### `resolve_sync_conflict_task`
- **Purpose**: Resolve a sync conflict with user-provided resolution
- **Parameters**: `user_id`, `conflict_id`, `resolution`
- **Resolution Types**: `use_client`, `use_server`, `merge`

### 7. Maintenance Tasks (`maintenance_tasks.py`)

#### `nightly_maintenance_task`
- **Purpose**: Run nightly maintenance tasks including cleanup and optimization
- **Schedule**: Daily (configured in celery_worker.py)
- **Sub-tasks**: 
  - Clean up expired exports
  - Clean up expired drafts
  - Archive old audit logs
  - Clean up orphaned files
  - Update all organization quotas

#### `cleanup_expired_exports_task`
- **Purpose**: Clean up expired export files (older than 7 days)
- **Parameters**: None
- **Process**: Deletes files and marks exports as expired

#### `cleanup_expired_drafts_task`
- **Purpose**: Clean up expired response drafts (older than 30 days)
- **Parameters**: None
- **Process**: Bulk delete expired drafts

#### `archive_old_audit_logs_task`
- **Purpose**: Archive audit logs older than 90 days
- **Parameters**: None
- **Process**: Marks logs as archived (in production, would move to cold storage)

#### `cleanup_orphaned_files_task`
- **Purpose**: Clean up orphaned files not referenced in database
- **Parameters**: None
- **Process**: Scans uploads directory and deletes unreferenced files older than 1 day

#### `calculate_all_quotas_task`
- **Purpose**: Calculate storage quotas for all organizations
- **Schedule**: Every 6 hours (configured in celery_worker.py)
- **Process**: Iterates through all active organizations and updates their quotas

#### `cleanup_old_sessions_task`
- **Purpose**: Clean up expired user sessions
- **Parameters**: None
- **Process**: Removes expired sessions from database

#### `cleanup_failed_tasks_task`
- **Purpose**: Clean up old failed Celery task results
- **Parameters**: None
- **Process**: Archives failed analysis runs older than 7 days

#### `optimize_database_indexes_task`
- **Purpose**: Optimize database indexes and analyze query performance
- **Parameters**: None
- **Note**: Placeholder for MongoDB-specific optimizations

#### `backup_system_data_task`
- **Purpose**: Create backup of critical system data
- **Parameters**: None
- **Note**: Placeholder for backup functionality

#### `check_system_health_task`
- **Purpose**: Check overall system health and report issues
- **Parameters**: None
- **Checks**: Database connection, Redis connection, storage space
- **Output**: Stores health status in `system_health` collection

### 8. Quota Tasks (`quota_tasks.py`)

#### `calculate_organization_quota_task`
- **Purpose**: Calculate storage quota for a specific organization
- **Parameters**: `org_id`
- **Process**: Calculates file storage, database size, and audit log usage

## Task Configuration

### Celery Worker Configuration

The main Celery worker is configured in `celery_worker.py` with:

- **Broker**: Redis (configurable via `REDIS_URL` environment variable)
- **Backend**: Redis (same as broker)
- **Concurrency**: Configurable via `CELERY_CONCURRENCY` environment variable (default: 4)
- **Task Queues**: Separate queues for different task types:
  - `analysis` - Analysis execution tasks
  - `exports` - Export generation tasks
  - `notifications` - Notification delivery tasks
  - `plugins` - Plugin execution tasks
  - `forms` - Form processing tasks
  - `sync` - Synchronization tasks
  - `maintenance` - Maintenance tasks

### Scheduled Tasks

The following tasks are scheduled via Celery Beat:

- **nightly-maintenance**: Daily at midnight
- **quota-calculation**: Every 6 hours
- **scheduled-analyses**: Every minute
- **cleanup-expired-exports**: Every 12 hours
- **cleanup-expired-drafts**: Daily

### Error Handling and Retry Logic

All tasks implement consistent error handling:

1. **Retry Strategy**: Exponential backoff with configurable max retries
2. **Error Logging**: Errors are logged to database and/or console
3. **Status Tracking**: Task status is updated in database records
4. **Graceful Degradation**: Errors in one part don't stop entire process

### Monitoring and Logging

Tasks provide comprehensive monitoring:

- **Status Updates**: Real-time status updates in database
- **Error Tracking**: Detailed error information stored
- **Performance Metrics**: Execution time and resource usage tracked
- **Audit Logging**: All important actions logged to audit_logs collection

## Running the Celery Worker

### Development

```bash
# Start Celery worker with all queues
celery -A backend.celery_worker worker --loglevel=info

# Start with specific queue
celery -A backend.celery_worker worker -Q analysis --loglevel=info

# Start with beat scheduler
celery -A backend.celery_worker beat --loglevel=info
```

### Production

```bash
# Start worker with concurrency
celery -A backend.celery_worker worker --loglevel=info --concurrency=4

# Start beat scheduler
celery -A backend.celery_worker beat --loglevel=info --scheduler=redis
```

### Docker

The Celery worker is included in the Docker Compose configuration:

```yaml
services:
  celery_worker:
    build: ./backend
    command: celery -A backend.celery_worker worker --loglevel=info
    depends_on:
      - redis
      - mongodb
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGODB_URI=mongodb://mongodb:27017/formbuilder

  celery_beat:
    build: ./backend
    command: celery -A backend.celery_worker beat --loglevel=info
    depends_on:
      - redis
      - mongodb
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGODB_URI=mongodb://mongodb:27017/formbuilder
```

## Task Dependencies

The task system depends on:

- **Redis**: For message broker and result backend
- **MongoDB**: For data storage and task state
- **File System**: For export files and plugin storage
- **External APIs**: Email/SMS delivery (AIIMS APIs)

## Security Considerations

1. **Plugin Isolation**: Plugins run in separate subprocesses with restricted environments
2. **Permission Validation**: All tasks validate user permissions before execution
3. **Data Sanitization**: Input data is validated and sanitized
4. **Secure File Storage**: Files are stored outside web root with proper access controls
5. **Audit Logging**: All task executions are logged for security auditing

## Performance Optimization

1. **Queue Separation**: Different task types use separate queues for better resource management
2. **Concurrency Control**: Configurable worker concurrency based on server resources
3. **Retry Logic**: Exponential backoff prevents overwhelming the system
4. **Bulk Operations**: Maintenance tasks use bulk database operations for efficiency
5. **Caching**: Analysis results are cached to avoid redundant computations

## Troubleshooting

### Common Issues

1. **Task Not Running**: Check if Celery worker is running and queue is properly configured
2. **Task Failing**: Check task logs and error messages in database
3. **Memory Issues**: Reduce worker concurrency or increase system memory
4. **Database Connection**: Ensure MongoDB and Redis are running and accessible

### Debug Commands

```bash
# Check active tasks
celery -A backend.celery_worker inspect active

# Check scheduled tasks
celery -A backend.celery_worker inspect scheduled

# Check task stats
celery -A backend.celery_worker inspect stats

# Purge all tasks
celery -A backend.celery_worker purge
```

### Monitoring

Use Flower for Celery monitoring:

```bash
pip install flower
celery -A backend.celery_worker flower
```

Access Flower UI at: http://localhost:5555