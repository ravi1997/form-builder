#!/bin/bash
# Form Builder Platform Setup Script
# This script sets up the entire platform infrastructure

set -e

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.$ENVIRONMENT.yml"
ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Git
    if ! command_exists git; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    # Check system memory
    local total_memory=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ "$total_memory" -lt 7000 ]; then
        print_warning "System has less than 8GB of RAM ($total_memory MB). Performance may be affected."
    fi
    
    # Check available disk space
    local available_space=$(df "$PROJECT_ROOT" | awk 'NR==2{printf "%.0f", $4/1024/1024}')
    if [ "$available_space" -lt 10 ]; then
        print_error "Insufficient disk space. At least 10GB is required."
        exit 1
    fi
    
    print_success "System requirements check passed"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$PROJECT_ROOT/uploads"
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/backups"
    mkdir -p "$PROJECT_ROOT/docker/nginx/certs"
    mkdir -p "$PROJECT_ROOT/docker/mongodb"
    mkdir -p "$PROJECT_ROOT/docker/redis"
    mkdir -p "$PROJECT_ROOT/docker/elasticsearch"
    mkdir -p "$PROJECT_ROOT/docker/clamav"
    mkdir -p "$PROJECT_ROOT/scripts"
    
    # Set proper permissions
    chmod 755 "$PROJECT_ROOT/uploads"
    chmod 755 "$PROJECT_ROOT/logs"
    chmod 755 "$PROJECT_ROOT/backups"
    
    print_success "Directories created successfully"
}

# Function to setup environment configuration
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_status "Please copy .env.example to .env.$ENVIRONMENT and configure it properly."
        exit 1
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_status "Creating .env file from $ENV_FILE"
        cp "$ENV_FILE" "$PROJECT_ROOT/.env"
        print_warning "Please review and update the .env file with your actual configuration"
    fi
    
    # Check for required environment variables
    local required_vars=("SECRET_KEY" "JWT_SECRET_KEY" "MONGO_URI" "REDIS_URL" "ELASTICSEARCH_URL")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$PROJECT_ROOT/.env"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing required environment variables: ${missing_vars[*]}"
        print_status "Please add these variables to your .env file"
        exit 1
    fi
    
    print_success "Environment configuration completed"
}

# Function to generate SSL certificates
setup_ssl() {
    print_status "Setting up SSL certificates..."
    
    local cert_dir="$PROJECT_ROOT/docker/nginx/certs"
    local cert_file="$cert_dir/cert.pem"
    local key_file="$cert_dir/key.pem"
    
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        print_status "Generating self-signed SSL certificate..."
        
        # Create a temporary OpenSSL config file
        cat > /tmp/openssl.conf << EOF
[req]
default_bits = 2048
prompt = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Organizational Unit
CN = localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
IP.1 = 127.0.0.1
EOF
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$key_file" \
            -out "$cert_file" \
            -config /tmp/openssl.conf
        
        rm -f /tmp/openssl.conf
        
        print_success "Self-signed SSL certificate generated"
        print_warning "For production, replace with proper SSL certificates from Let's Encrypt or your CA"
    else
        print_success "SSL certificates already exist"
    fi
}

# Function to setup Docker networks
setup_networks() {
    print_status "Setting up Docker networks..."
    
    # Create custom network if it doesn't exist
    if ! docker network ls | grep -q formbuilder_network; then
        docker network create formbuilder_network
        print_success "Docker network created"
    else
        print_success "Docker network already exists"
    fi
}

# Function to pull Docker images
pull_images() {
    print_status "Pulling Docker images..."
    
    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" pull
        print_success "Docker images pulled successfully"
    else
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
}

# Function to build custom images
build_images() {
    print_status "Building custom Docker images..."
    
    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" build --pull
        print_success "Custom Docker images built successfully"
    else
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" up -d
        
        # Wait for services to be ready
        print_status "Waiting for services to be ready..."
        sleep 30
        
        print_success "Services started successfully"
    else
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
}

# Function to verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check if services are running
    local services=("nginx" "backend" "mongodb" "redis" "elasticsearch" "clamav")
    local all_running=true
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps -q "$service" | grep -q .; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        print_error "Some services failed to start"
        exit 1
    fi
    
    # Check health endpoints
    print_status "Checking health endpoints..."
    
    # Get backend port
    local backend_port=$(docker-compose -f "$COMPOSE_FILE" port backend 5000 | cut -d: -f2 | cut -d- -f1)
    
    if [ -n "$backend_port" ]; then
        if curl -s "http://localhost:$backend_port/api/health" > /dev/null; then
            print_success "Backend API is healthy"
        else
            print_error "Backend API is not responding"
            all_running=false
        fi
    fi
    
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
        print_error "Setup verification failed"
        exit 1
    fi
    
    print_success "Setup verification completed successfully"
}

# Function to show access information
show_access_info() {
    print_status "Access Information:"
    echo "=========================================="
    echo "Form Builder Platform - $ENVIRONMENT Environment"
    echo "=========================================="
    echo ""
    echo "🌐 Web Application:"
    echo "   URL: https://localhost"
    echo "   (Use self-signed certificate for development)"
    echo ""
    echo "📊 Monitoring Services:"
    echo "   Flower (Celery): http://localhost:5555"
    echo "   Redis Commander: http://localhost:8081"
    echo "   Mongo Express: http://localhost:8082"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "   Stop services: docker-compose -f $COMPOSE_FILE down"
    echo "   Restart services: docker-compose -f $COMPOSE_FILE restart"
    echo "   Monitor health: $PROJECT_ROOT/scripts/monitor.sh $ENVIRONMENT"
    echo ""
    echo "📁 Important Directories:"
    echo "   Uploads: $PROJECT_ROOT/uploads"
    echo "   Logs: $PROJECT_ROOT/logs"
    echo "   Backups: $PROJECT_ROOT/backups"
    echo ""
    echo "📖 Documentation:"
    echo "   Deployment Guide: $PROJECT_ROOT/docs/DEPLOYMENT.md"
    echo "   API Documentation: https://localhost/api/docs"
    echo ""
    echo "⚠️  Important Notes:"
    echo "   - Update .env file with your actual configuration"
    echo "   - Replace self-signed SSL certificates in production"
    echo "   - Set up proper monitoring and alerting"
    echo "   - Configure regular backups"
    echo "   - Review security settings"
    echo ""
}

# Function to create systemd service (optional)
create_systemd_service() {
    if [ "$EUID" -ne 0 ]; then
        print_warning "Run as root to create systemd service"
        return 0
    fi
    
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/form-builder.service << EOF
[Unit]
Description=Form Builder Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/docker-compose -f $COMPOSE_FILE up -d
ExecStop=/usr/bin/docker-compose -f $COMPOSE_FILE down
TimeoutStartSec=0
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable form-builder.service
    
    print_success "Systemd service created and enabled"
    print_status "Use: systemctl start|stop|status form-builder"
}

# Main setup function
main() {
    echo "=========================================="
    echo "Form Builder Platform Setup"
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
                echo "  ENVIRONMENT     Environment to setup (development|testing|production)"
                echo ""
                echo "Options:"
                echo "  -e, --environment ENVIRONMENT  Specify environment"
                echo "  --systemd                     Create systemd service (requires root)"
                echo "  -h, --help                    Show this help message"
                echo ""
                exit 0
                ;;
            --systemd)
                CREATE_SYSTEMD=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Update compose file and env file paths
    COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.$ENVIRONMENT.yml"
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    
    # Run setup steps
    check_requirements
    create_directories
    setup_environment
    setup_ssl
    setup_networks
    pull_images
    build_images
    start_services
    verify_setup
    
    if [ "$CREATE_SYSTEMD" = true ]; then
        create_systemd_service
    fi
    
    show_access_info
    
    print_success "Form Builder Platform setup completed successfully!"
    print_status "Platform is now ready to use"
}

# Run main function
main "$@"