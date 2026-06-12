#!/bin/bash
# Infrastructure Monitoring Script
# This script monitors the health and performance of all services

set -e

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker/docker-compose.${ENVIRONMENT}.yml"
ALERT_EMAIL=${ALERT_EMAIL:-admin@example.com}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/var/log/form-builder-monitor.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to send alert
send_alert() {
    local message="$1"
    local subject="Form Builder Alert: $ENVIRONMENT"
    
    log "ALERT: $message"
    
    # Send email alert (if configured)
    if command -v mail &> /dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
    fi
    
    # Send Slack alert (if configured)
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$subject\n$message\"}" \
            "$SLACK_WEBHOOK"
    fi
}

# Function to check service health
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local expected_code="${3:-200}"
    
    if [ -z "$health_url" ]; then
        return 0
    fi
    
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" || echo "000")
    
    if [ "$response_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} $service_name: Healthy ($response_code)"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name: Unhealthy ($response_code)"
        send_alert "$service_name is unhealthy. Status code: $response_code"
        return 1
    fi
}

# Function to check Docker service
check_docker_service() {
    local service="$1"
    
    if ! docker-compose -f "$COMPOSE_FILE" ps -q "$service" | grep -q .; then
        echo -e "${RED}✗${NC} $service: Not running"
        send_alert "$service is not running"
        return 1
    fi
    
    local status=$(docker-compose -f "$COMPOSE_FILE" ps --services --filter "status=running" | grep "^$service$" || echo "")
    if [ -n "$status" ]; then
        echo -e "${GREEN}✓${NC} $service: Running"
        return 0
    else
        echo -e "${RED}✗${NC} $service: Not running"
        send_alert "$service is not running"
        return 1
    fi
}

# Function to check resource usage
check_resource_usage() {
    local service="$1"
    local max_cpu="${2:-80}"
    local max_memory="${3:-80}"
    
    if ! docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -q "$service"; then
        return 0
    fi
    
    local stats=$(docker stats --no-stream --format "{{.CPUPerc}}\t{{.MemPerc}}" "$service" 2>/dev/null || echo "")
    if [ -z "$stats" ]; then
        return 0
    fi
    
    local cpu_percent=$(echo "$stats" | cut -f1 | tr -d '%')
    local memory_percent=$(echo "$stats" | cut -f2 | tr -d '%')
    
    # Remove decimal part for comparison
    cpu_percent=${cpu_percent%.*}
    memory_percent=${memory_percent%.*}
    
    if [ "$cpu_percent" -gt "$max_cpu" ]; then
        echo -e "${YELLOW}!${NC} $service: High CPU usage (${cpu_percent}%)"
        send_alert "$service has high CPU usage: ${cpu_percent}%"
    fi
    
    if [ "$memory_percent" -gt "$max_memory" ]; then
        echo -e "${YELLOW}!${NC} $service: High memory usage (${memory_percent}%)"
        send_alert "$service has high memory usage: ${memory_percent}%"
    fi
    
    if [ "$cpu_percent" -le "$max_cpu" ] && [ "$memory_percent" -le "$max_memory" ]; then
        echo -e "${GREEN}✓${NC} $service: Resource usage normal (CPU: ${cpu_percent}%, Memory: ${memory_percent}%)"
    fi
}

# Function to check disk space
check_disk_space() {
    local path="$1"
    local threshold="${2:-80}"
    
    if [ ! -d "$path" ]; then
        return 0
    fi
    
    local usage=$(df "$path" | awk 'NR==2 {print $5}' | tr -d '%')
    
    if [ "$usage" -gt "$threshold" ]; then
        echo -e "${RED}✗${NC} Disk space $path: ${usage}% used"
        send_alert "Disk space $path is ${usage}% used"
        return 1
    else
        echo -e "${GREEN}✓${NC} Disk space $path: ${usage}% used"
        return 0
    fi
}

# Function to check database connectivity
check_database_connectivity() {
    local service="$1"
    local check_command="$2"
    
    if ! docker-compose -f "$COMPOSE_FILE" exec -T "$service" sh -c "$check_command" >/dev/null 2>&1; then
        echo -e "${RED}✗${NC} $service: Connection failed"
        send_alert "$service connection failed"
        return 1
    else
        echo -e "${GREEN}✓${NC} $service: Connection OK"
        return 0
    fi
}

# Main monitoring function
main() {
    log "Starting infrastructure monitoring for $ENVIRONMENT environment"
    
    echo "=========================================="
    echo "Form Builder Infrastructure Monitoring"
    echo "Environment: $ENVIRONMENT"
    echo "=========================================="
    
    local overall_health=0
    
    # Check Docker Compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}✗${NC} Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Check core services
    echo -e "\n${YELLOW}=== Core Services ===${NC}"
    
    check_docker_service "nginx" || overall_health=1
    check_docker_service "backend" || overall_health=1
    check_docker_service "mongodb" || overall_health=1
    check_docker_service "redis" || overall_health=1
    check_docker_service "elasticsearch" || overall_health=1
    check_docker_service "clamav" || overall_health=1
    
    # Check worker services
    echo -e "\n${YELLOW}=== Worker Services ===${NC}"
    
    check_docker_service "celery_worker" || overall_health=1
    check_docker_service "celery_beat" || overall_health=1
    
    # Check monitoring services
    echo -e "\n${YELLOW}=== Monitoring Services ===${NC}"
    
    check_docker_service "flower" || overall_health=1
    
    # Check health endpoints
    echo -e "\n${YELLOW}=== Health Endpoints ===${NC}"
    
    # Get backend container port mapping
    local backend_port=$(docker-compose -f "$COMPOSE_FILE" port backend 5000 | cut -d: -f2 | cut -d- -f1)
    if [ -n "$backend_port" ]; then
        check_service_health "Backend API" "http://localhost:$backend_port/api/health" || overall_health=1
    fi
    
    # Check resource usage
    echo -e "\n${YELLOW}=== Resource Usage ===${NC}"
    
    check_resource_usage "backend" 80 80
    check_resource_usage "mongodb" 70 80
    check_resource_usage "elasticsearch" 80 90
    check_resource_usage "redis" 70 80
    
    # Check disk space
    echo -e "\n${YELLOW}=== Disk Space ===${NC}"
    
    check_disk_space "/var/lib/docker" 80 || overall_health=1
    check_disk_space "/var/log" 80 || overall_health=1
    
    # Check database connectivity
    echo -e "\n${YELLOW}=== Database Connectivity ===${NC}"
    
    check_database_connectivity "mongodb" "mongo --eval 'db.runCommand({ping: 1})'" || overall_health=1
    check_database_connectivity "redis" "redis-cli ping" || overall_health=1
    check_database_connectivity "elasticsearch" "curl -s http://localhost:9200/_cluster/health | grep -q 'green'" || overall_health=1
    
    # Check application-specific metrics
    echo -e "\n${YELLOW}=== Application Metrics ===${NC}"
    
    # Check if backend is accessible and get basic metrics
    if [ -n "$backend_port" ]; then
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' "http://localhost:$backend_port/api/health" || echo "0")
        response_time=$(echo "$response_time * 1000" | bc -l 2>/dev/null || echo "0")
        response_time=${response_time%.*}
        
        if [ "$response_time" -gt 5000 ]; then
            echo -e "${RED}✗${NC} Backend response time: ${response_time}ms (slow)"
            send_alert "Backend response time is slow: ${response_time}ms"
            overall_health=1
        else
            echo -e "${GREEN}✓${NC} Backend response time: ${response_time}ms"
        fi
    fi
    
    # Summary
    echo -e "\n${YELLOW}=== Summary ===${NC}"
    
    if [ "$overall_health" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} All services are healthy"
        log "All services are healthy"
        exit 0
    else
        echo -e "${RED}✗${NC} Some services have issues"
        log "Some services have issues detected"
        exit 1
    fi
}

# Run main function
main "$@"