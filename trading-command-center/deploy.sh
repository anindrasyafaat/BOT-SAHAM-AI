#!/bin/bash

# Trading Command Center - Deployment Script
# Script untuk deploy Trading Command Center dengan satu klik

set -e  # Exit on error

echo "🚀 Trading Command Center Deployment Script"
echo "=========================================="

# Colors untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function untuk print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "All prerequisites satisfied!"
}

# Setup environment
setup_environment() {
    print_info "Setting up environment..."
    
    # Create .env file if not exists
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Created .env file from .env.example. Please configure your API keys."
        else
            print_error ".env.example file not found. Please create .env file manually."
            exit 1
        fi
    else
        print_success ".env file already exists."
    fi
    
    # Create necessary directories
    mkdir -p backend/data
    mkdir -p backend/logs
    mkdir -p frontend/dist
    
    print_success "Environment setup completed!"
}

# Build and deploy
deploy() {
    print_info "Building and deploying Trading Command Center..."
    
    # Pull latest images
    print_info "Pulling latest Docker images..."
    docker-compose pull
    
    # Build images
    print_info "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    print_info "Starting services..."
    docker-compose up -d
    
    print_success "Trading Command Center deployed successfully!"
}

# Health check
health_check() {
    print_info "Performing health check..."
    
    # Wait for services to start
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services are running!"
    else
        print_error "Some services are not running. Please check the logs."
        docker-compose logs
        exit 1
    fi
    
    # Test API endpoint
    print_info "Testing API endpoint..."
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_success "API is responding!"
    else
        print_warning "API might not be ready yet. Please wait a few more seconds."
    fi
}

# Show access URLs
show_access_urls() {
    print_info "Access URLs:"
    echo "  🌐 Frontend: http://localhost:3000"
    echo "  🔌 API: http://localhost:8000"
    echo "  📚 API Docs: http://localhost:8000/docs"
    echo "  🔍 Health Check: http://localhost:8000/health"
    echo ""
    print_success "Trading Command Center is ready to use!"
}

# Main deployment flow
main() {
    echo ""
    print_info "Starting Trading Command Center deployment..."
    echo ""
    
    # Step 1: Check prerequisites
    check_prerequisites
    echo ""
    
    # Step 2: Setup environment
    setup_environment
    echo ""
    
    # Step 3: Deploy
    deploy
    echo ""
    
    # Step 4: Health check
    health_check
    echo ""
    
    # Step 5: Show access URLs
    show_access_urls
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    stop)
        print_info "Stopping Trading Command Center..."
        docker-compose down
        print_success "Trading Command Center stopped!"
        ;;
    restart)
        print_info "Restarting Trading Command Center..."
        docker-compose restart
        print_success "Trading Command Center restarted!"
        ;;
    logs)
        print_info "Showing logs..."
        docker-compose logs -f
        ;;
    update)
        print_info "Updating Trading Command Center..."
        docker-compose pull
        docker-compose up -d
        print_success "Trading Command Center updated!"
        ;;
    clean)
        print_warning "This will remove all containers and volumes. Are you sure? (y/N)"
        read -r confirm
        if [[ $confirm == [yY] ]]; then
            print_info "Cleaning up..."
            docker-compose down -v --remove-orphans
            docker system prune -f
            print_success "Cleanup completed!"
        else
            print_info "Cleanup cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|update|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy Trading Command Center (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show logs"
        echo "  update  - Update to latest version"
        echo "  clean   - Clean up containers and volumes"
        exit 1
        ;;
esac