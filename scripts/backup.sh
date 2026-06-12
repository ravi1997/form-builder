#!/bin/bash
# Form Builder Platform Backup Script
# This script creates comprehensive backups of the entire platform

set -e

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.$ENVIRONMENT.yml"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
COMPRESSION=${BACKUP_COMPRESSION:-true}
UPLOAD_TO_S3=${BACKUP_UPLOAD_TO_S3:-false}
S3_BUCKET=${BACKUP_S3_BUCKET:-}
S3_PREFIX=${BACKUP_S3_PREFIX:-form-builder}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create backup directory
create_backup_dir() {
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# Function to backup MongoDB
backup_mongodb() {
    local backup_path="$1"
    local mongo_backup_dir="$backup_path/mongodb"
    
    print_status "Backing up MongoDB..."
    
    mkdir -p "$mongo_backup_dir"
    
    # Create MongoDB backup
    if docker-compose -f "$COMPOSE_FILE" exec -T mongodb mongodump \
        --archive \
        --gzip \
        --out "$mongo_backup_dir" > /dev/null 2>&1; then
        
        print_success "MongoDB backup completed"
    else
        print_error "MongoDB backup failed"
        return 1
    fi
}

# Function to backup Redis
backup_redis() {
    local backup_path="$1"
    local redis_backup_file="$backup_path/redis.rdb"
    
    print_status "Backing up Redis..."
    
    # Save Redis data
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli SAVE > /dev/null 2>&1; then
        # Copy Redis dump file
        if docker cp $(docker-compose -f "$COMPOSE_FILE" ps -q redis):/data/dump.rdb "$redis_backup_file" 2>/dev/null; then
            print_success "Redis backup completed"
        else
            print_error "Redis backup failed"
            return 1
        fi
    else
        print_error "Redis SAVE command failed"
        return 1
    fi
}

# Function to backup Elasticsearch
backup_elasticsearch() {
    local backup_path="$1"
    local es_backup_dir="$backup_path/elasticsearch"
    
    print_status "Backing up Elasticsearch..."
    
    mkdir -p "$es_backup_dir"
    
    # Create Elasticsearch snapshot repository
    local snapshot_name="backup_$TIMESTAMP"
    
    # Create snapshot repository
    curl -s -X PUT "localhost:9200/_snapshot/backup" -H 'Content-Type: application/json' -d'
    {
        "type": "fs",
        "settings": {
            "location": "'"$es_backup_dir"'",
            "compress": true
        }
    }
    ' > /dev/null
    
    # Create snapshot
    if curl -s -X PUT "localhost:9200/_snapshot/backup/$snapshot_name?wait_for_completion=true" > /dev/null; then
        print_success "Elasticsearch backup completed"
    else
        print_error "Elasticsearch backup failed"
        return 1
    fi
}

# Function to backup file uploads
backup_uploads() {
    local backup_path="$1"
    local uploads_backup_dir="$backup_path/uploads"
    
    print_status "Backing up file uploads..."
    
    # Copy uploads directory
    if docker cp $(docker-compose -f "$COMPOSE_FILE" ps -q backend):/app/uploads "$uploads_backup_dir" 2>/dev/null; then
        print_success "File uploads backup completed"
    else
        print_error "File uploads backup failed"
        return 1
    fi
}

# Function to backup configuration files
backup_config() {
    local backup_path="$1"
    local config_backup_dir="$backup_path/config"
    
    print_status "Backing up configuration files..."
    
    mkdir -p "$config_backup_dir"
    
    # Copy environment files
    cp "$PROJECT_ROOT/.env"* "$config_backup_dir/" 2>/dev/null || true
    cp "$PROJECT_ROOT/.kilo"* "$config_backup_dir/" 2>/dev/null || true
    
    # Copy Docker configuration
    cp -r "$PROJECT_ROOT/docker" "$config_backup_dir/" 2>/dev/null || true
    
    # Copy scripts
    cp -r "$PROJECT_ROOT/scripts" "$config_backup_dir/" 2>/dev/null || true
    
    print_success "Configuration files backup completed"
}

# Function to backup logs
backup_logs() {
    local backup_path="$1"
    local logs_backup_dir="$backup_path/logs"
    
    print_status "Backing up logs..."
    
    mkdir -p "$logs_backup_dir"
    
    # Copy application logs
    if [ -d "$PROJECT_ROOT/logs" ]; then
        cp -r "$PROJECT_ROOT/logs"/* "$logs_backup_dir/" 2>/dev/null || true
    fi
    
    # Copy Docker logs
    docker-compose -f "$COMPOSE_FILE" logs --no-color > "$logs_backup_dir/docker-compose.log" 2>/dev/null || true
    
    print_success "Logs backup completed"
}

# Function to compress backup
compress_backup() {
    local backup_path="$1"
    local backup_name="form-builder-backup-$TIMESTAMP"
    
    if [ "$COMPRESSION" = true ]; then
        print_status "Compressing backup..."
        
        cd "$BACKUP_DIR"
        if tar -czf "$backup_name.tar.gz" "$TIMESTAMP" 2>/dev/null; then
            rm -rf "$backup_path"
            backup_path="$BACKUP_DIR/$backup_name.tar.gz"
            print_success "Backup compressed successfully"
        else
            print_error "Backup compression failed"
            return 1
        fi
    fi
    
    echo "$backup_path"
}

# Function to upload to S3
upload_to_s3() {
    local backup_file="$1"
    
    if [ "$UPLOAD_TO_S3" = true ] && [ -n "$S3_BUCKET" ]; then
        print_status "Uploading backup to S3..."
        
        if command -v aws &> /dev/null; then
            local s3_key="$S3_PREFIX/$(basename "$backup_file")"
            
            if aws s3 cp "$backup_file" "s3://$S3_BUCKET/$s3_key" 2>/dev/null; then
                print_success "Backup uploaded to S3: s3://$S3_BUCKET/$s3_key"
            else
                print_error "S3 upload failed"
                return 1
            fi
        else
            print_warning "AWS CLI not found. Skipping S3 upload."
        fi
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    print_status "Cleaning up old backups..."
    
    if [ -d "$BACKUP_DIR" ]; then
        # Remove backups older than RETENTION_DAYS
        find "$BACKUP_DIR" -name "form-builder-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
        find "$BACKUP_DIR" -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
        
        print_success "Old backups cleaned up"
    fi
}

# Function to verify backup
verify_backup() {
    local backup_file="$1"
    
    print_status "Verifying backup..."
    
    if [ -f "$backup_file" ]; then
        local file_size=$(du -h "$backup_file" | cut -f1)
        print_success "Backup verified. Size: $file_size"
        return 0
    else
        print_error "Backup verification failed. File not found: $backup_file"
        return 1
    fi
}

# Function to show backup summary
show_summary() {
    local backup_file="$1"
    local backup_size=$(du -h "$backup_file" | cut -f1)
    local backup_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo ""
    echo "=========================================="
    echo "Backup Summary"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $backup_time"
    echo "Backup File: $backup_file"
    echo "File Size: $backup_size"
    echo "Retention: $RETENTION_DAYS days"
    echo ""
    
    if [ "$UPLOAD_TO_S3" = true ] && [ -n "$S3_BUCKET" ]; then
        echo "S3 Upload: Enabled"
        echo "S3 Bucket: $S3_BUCKET"
        echo "S3 Prefix: $S3_PREFIX"
    else
        echo "S3 Upload: Disabled"
    fi
    
    echo ""
    echo "To restore backup, use:"
    echo "  $PROJECT_ROOT/scripts/restore.sh $ENVIRONMENT $backup_file"
    echo ""
}

# Function to send backup notification
send_notification() {
    local status="$1"
    local backup_file="$2"
    local backup_size=$(du -h "$backup_file" | cut -f1)
    
    local subject="Form Builder Backup: $status - $ENVIRONMENT"
    local message="Backup Status: $status\nEnvironment: $ENVIRONMENT\nBackup File: $backup_file\nFile Size: $backup_size\nTimestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Send email if configured
    if [ -n "$BACKUP_NOTIFY_EMAIL" ] && command -v mail &> /dev/null; then
        echo -e "$message" | mail -s "$subject" "$BACKUP_NOTIFY_EMAIL"
    fi
    
    # Send Slack notification if configured
    if [ -n "$BACKUP_SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$subject\n$message\"}" \
            "$BACKUP_SLACK_WEBHOOK"
    fi
}

# Main backup function
main() {
    echo "=========================================="
    echo "Form Builder Platform Backup"
    echo "Environment: $ENVIRONMENT"
    echo "=========================================="
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [ENVIRONMENT] [OPTIONS]"
                echo ""
                echo "Arguments:"
                echo "  ENVIRONMENT     Environment to backup (development|testing|production)"
                echo ""
                echo "Options:"
                echo "  -e, --environment ENVIRONMENT  Specify environment"
                echo "  --no-compress                  Skip compression"
                echo "  --upload-s3                    Upload to S3"
                echo "  --retention-days DAYS         Set retention period"
                echo "  -h, --help                    Show this help message"
                echo ""
                exit 0
                ;;
            --no-compress)
                COMPRESSION=false
                shift
                ;;
            --upload-s3)
                UPLOAD_TO_S3=true
                shift
                ;;
            --retention-days)
                RETENTION_DAYS="$2"
                shift
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Update compose file path
    COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.$ENVIRONMENT.yml"
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Create backup directory
    local backup_path=$(create_backup_dir)
    
    # Perform backups
    backup_mongodb "$backup_path"
    backup_redis "$backup_path"
    backup_elasticsearch "$backup_path"
    backup_uploads "$backup_path"
    backup_config "$backup_path"
    backup_logs "$backup_path"
    
    # Compress backup
    local backup_file=$(compress_backup "$backup_path")
    
    # Upload to S3 if enabled
    upload_to_s3 "$backup_file"
    
    # Verify backup
    verify_backup "$backup_file"
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Show summary
    show_summary "$backup_file"
    
    # Send notification
    send_notification "SUCCESS" "$backup_file"
    
    print_success "Backup completed successfully!"
}

# Run main function
main "$@"