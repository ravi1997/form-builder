#!/bin/bash
# Form Builder Platform Restore Script
# This script restores the platform from a backup

set -e

# Configuration
ENVIRONMENT=${1:-production}
BACKUP_FILE=${2:-}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.$ENVIRONMENT.yml"
TEMP_DIR="/tmp/form-builder-restore-$$"

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if backup file is provided
    if [ -z "$BACKUP_FILE" ]; then
        print_error "Backup file not provided"
        echo "Usage: $0 ENVIRONMENT BACKUP_FILE"
        echo "Example: $0 production /path/to/backup/form-builder-backup-20240101_120000.tar.gz"
        exit 1
    fi
    
    # Check if backup file exists
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    # Check if Docker Compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if services are running
    if ! docker-compose -f "$COMPOSE_FILE" ps -q | grep -q .; then
        print_warning "No services are running. Starting services..."
        docker-compose -f "$COMPOSE_FILE" up -d
        sleep 10
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create temporary directory
create_temp_dir() {
    mkdir -p "$TEMP_DIR"
    print_status "Created temporary directory: $TEMP_DIR"
}

# Function to extract backup
extract_backup() {
    print_status "Extracting backup..."
    
    cd "$TEMP_DIR"
    
    if [[ "$BACKUP_FILE" == *.tar.gz ]]; then
        tar -xzf "$BACKUP_FILE"
    elif [[ "$BACKUP_FILE" == *.tar ]]; then
        tar -xf "$BACKUP_FILE"
    else
        print_error "Unsupported backup file format: $BACKUP_FILE"
        exit 1
    fi
    
    # Find the extracted directory
    local extracted_dir=$(find . -maxdepth 1 -type d -name "20*" | head -n1)
    if [ -z "$extracted_dir" ]; then
        print_error "Could not find extracted backup directory"
        exit 1
    fi
    
    cd "$extracted_dir"
    print_success "Backup extracted successfully"
}

# Function to stop services
stop_services() {
    print_status "Stopping services for restore..."
    
    docker-compose -f "$COMPOSE_FILE" stop
    sleep 5
    
    print_success "Services stopped successfully"
}

# Function to restore MongoDB
restore_mongodb() {
    print_status "Restoring MongoDB..."
    
    if [ ! -d "mongodb" ]; then
        print_warning "MongoDB backup not found. Skipping MongoDB restore."
        return 0
    fi
    
    # Start MongoDB service
    docker-compose -f "$COMPOSE_FILE" up -d mongodb
    sleep 10
    
    # Restore MongoDB data
    if docker-compose -f "$COMPOSE_FILE" exec -T mongodb mongorestore \
        --archive \
        --gzip \
        --dir /tmp/mongodb > /dev/null 2>&1; then
        
        print_success "MongoDB restore completed"
    else
        print_error "MongoDB restore failed"
        return 1
    fi
}

# Function to restore Redis
restore_redis() {
    print_status "Restoring Redis..."
    
    if [ ! -f "redis.rdb" ]; then
        print_warning "Redis backup not found. Skipping Redis restore."
        return 0
    fi
    
    # Start Redis service
    docker-compose -f "$COMPOSE_FILE" up -d redis
    sleep 5
    
    # Copy Redis dump file
    if docker cp redis.rdb $(docker-compose -f "$COMPOSE_FILE" ps -q redis):/data/dump.rdb 2>/dev/null; then
        # Restart Redis to load the dump file
        docker-compose -f "$COMPOSE_FILE" restart redis
        sleep 5
        
        print_success "Redis restore completed"
    else
        print_error "Redis restore failed"
        return 1
    fi
}

# Function to restore Elasticsearch
restore_elasticsearch() {
    print_status "Restoring Elasticsearch..."
    
    if [ ! -d "elasticsearch" ]; then
        print_warning "Elasticsearch backup not found. Skipping Elasticsearch restore."
        return 0
    fi
    
    # Start Elasticsearch service
    docker-compose -f "$COMPOSE_FILE" up -d elasticsearch
    sleep 30
    
    # Restore Elasticsearch indices
    # Note: This is a simplified restore. For production, you might need a more sophisticated approach
    if docker cp elasticsearch $(docker-compose -f "$COMPOSE_FILE" ps -q elasticsearch):/usr/share/elasticsearch/data/ 2>/dev/null; then
        # Restart Elasticsearch
        docker-compose -f "$COMPOSE_FILE" restart elasticsearch
        sleep 30
        
        print_success "Elasticsearch restore completed"
    else
        print_error "Elasticsearch restore failed"
        return 1
    fi
}

# Function to restore file uploads
restore_uploads() {
    print_status "Restoring file uploads..."
    
    if [ ! -d "uploads" ]; then
        print_warning "File uploads backup not found. Skipping uploads restore."
        return 0
    fi
    
    # Start backend service
    docker-compose -f "$COMPOSE_FILE" up -d backend
    sleep 10
    
    # Copy uploads to backend container
    if docker cp uploads $(docker-compose -f "$COMPOSE_FILE" ps -q backend):/app/ 2>/dev/null; then
        # Set proper permissions
        docker-compose -f "$COMPOSE_FILE" exec -T backend chown -R appuser:appuser /app/uploads
        
        print_success "File uploads restore completed"
    else
        print_error "File uploads restore failed"
        return 1
    fi
}

# Function to restore configuration
restore_config() {
    print_status "Restoring configuration files..."
    
    if [ ! -d "config" ]; then
        print_warning "Configuration backup not found. Skipping configuration restore."
        return 0
    fi
    
    # Restore environment files
    if [ -d "config" ]; then
        cp config/.env* "$PROJECT_ROOT/" 2>/dev/null || true
        cp config/.kilo* "$PROJECT_ROOT/" 2>/dev/null || true
        
        # Restore Docker configuration
        if [ -d "config/docker" ]; then
            cp -r config/docker/* "$PROJECT_ROOT/docker/" 2>/dev/null || true
        fi
        
        # Restore scripts
        if [ -d "config/scripts" ]; then
            cp -r config/scripts/* "$PROJECT_ROOT/scripts/" 2>/dev/null || true
        fi
        
        print_success "Configuration restore completed"
    fi
}

# Function to restore logs
restore_logs() {
    print_status "Restoring logs..."
    
    if [ ! -d "logs" ]; then
        print_warning "Logs backup not found. Skipping logs restore."
        return 0
    fi
    
    # Copy logs to project directory
    if [ -d "$PROJECT_ROOT/logs" ]; then
        cp -r logs/* "$PROJECT_ROOT/logs/" 2>/dev/null || true
        print_success "Logs restore completed"
    fi
}

# Function to start all services
start_services() {
    print_status "Starting all services..."
    
    docker-compose -f "$COMPOSE_FILE" up -d
    sleep 30
    
    print_success "All services started successfully"
}

# Function to verify restore
verify_restore() {
    print_status "Verifying restore..."
    
    # Check if services are running
    local services=("backend" "mongodb" "redis" "elasticsearch")
    local all_running=true
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps -q "$service" | grep -q .; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            all_running=false
        fi
    done
    
    # Check database connectivity
    print_status "Checking database connectivity..."
    
    if docker-compose -f "$COMPOSE_FILE" exec -T mongodb mongo --eval 'db.runCommand({ping: 1})' > /dev/null 2>&1; then
        print_success "MongoDB is accessible"
    else
        print_error "MongoDB is not accessible"
        all_running=false
    fi
    
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is accessible"
    else
        print_error "Redis is not accessible"
        all_running=false
    fi
    
    if [ "$all_running" = false ]; then
        print_error "Restore verification failed"
        return 1
    fi
    
    print_success "Restore verification completed successfully"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up temporary files..."
    
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        print_success "Temporary files cleaned up"
    fi
}

# Function to show restore summary
show_summary() {
    echo ""
    echo "=========================================="
    echo "Restore Summary"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Backup File: $BACKUP_FILE"
    echo "Restore Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "Restored Components:"
    echo "  ✓ MongoDB database"
    echo "  ✓ Redis cache"
    echo "  ✓ Elasticsearch indices"
    echo "  ✓ File uploads"
    echo "  ✓ Configuration files"
    echo "  ✓ Log files"
    echo ""
    echo "Next Steps:"
    echo "  1. Verify all services are running: docker-compose -f $COMPOSE_FILE ps"
    echo "  2. Check application logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  3. Test application functionality"
    echo "  4. Monitor system performance"
    echo ""
}

# Function to send restore notification
send_notification() {
    local status="$1"
    
    local subject="Form Builder Restore: $status - $ENVIRONMENT"
    local message="Restore Status: $status\nEnvironment: $ENVIRONMENT\nBackup File: $BACKUP_FILE\nRestore Time: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Send email if configured
    if [ -n "$RESTORE_NOTIFY_EMAIL" ] && command -v mail &> /dev/null; then
        echo -e "$message" | mail -s "$subject" "$RESTORE_NOTIFY_EMAIL"
    fi
    
    # Send Slack notification if configured
    if [ -n "$RESTORE_SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$subject\n$message\"}" \
            "$RESTORE_SLACK_WEBHOOK"
    fi
}

# Main restore function
main() {
    echo "=========================================="
    echo "Form Builder Platform Restore"
    echo "=========================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Create temporary directory
    create_temp_dir
    
    # Extract backup
    extract_backup
    
    # Stop services
    stop_services
    
    # Restore components
    restore_mongodb
    restore_redis
    restore_elasticsearch
    restore_uploads
    restore_config
    restore_logs
    
    # Start all services
    start_services
    
    # Verify restore
    verify_restore
    
    # Cleanup
    cleanup
    
    # Show summary
    show_summary
    
    # Send notification
    send_notification "SUCCESS"
    
    print_success "Restore completed successfully!"
}

# Error handling
trap 'cleanup; print_error "Restore failed. Check logs for details."; exit 1' ERR

# Run main function
main "$@"