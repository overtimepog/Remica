#!/bin/bash
# run.sh - Universal deployment and interaction script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
PROJECT_NAME="real-estate-chat-agent"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Dependencies check passed!"
}

build_containers() {
    print_status "Building containers..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build --no-cache
    print_status "Containers built successfully!"
}

start_services() {
    print_status "Starting services..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Wait for PostgreSQL to be ready
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        print_status "Waiting for PostgreSQL... (attempt $((attempt + 1))/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start after $max_attempts attempts"
        exit 1
    fi
    
    print_status "All services are ready!"
}

stop_services() {
    print_status "Stopping services..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    print_status "Services stopped!"
}

cleanup() {
    print_status "Cleaning up containers and volumes..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans
    docker system prune -f
    print_status "Cleanup completed!"
}

start_cli() {
    print_status "Starting Real Estate Market Insights Chat Agent..."
    print_status "Type 'help' for available commands or 'exit' to quit."
    echo
    
    # Start interactive CLI session - use python -m src.main for module execution
    # Use -it flags for interactive terminal
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -it app python -m src.main
}

show_help() {
    echo "Real Estate Market Insights Chat Agent - Deployment Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  cli        Start the chat agent CLI (default)"
    echo "  build      Build all containers"
    echo "  start      Start all services"
    echo "  stop       Stop all services"
    echo "  restart    Restart all services"
    echo "  logs       Show service logs"
    echo "  cleanup    Stop services and remove containers/volumes"
    echo "  status     Show service status"
    echo "  test       Run the test suite"
    echo "  help       Show this help message"
    echo
    echo "Examples:"
    echo "  $0 cli          # Start the CLI interface"
    echo "  $0 build        # Build containers"
    echo "  $0 test         # Run automated tests"
}

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        print_warning "Please edit .env file and add your OpenRouter API key!"
    else
        print_error ".env file not found and no .env.example available!"
        exit 1
    fi
fi

# Main script logic
case "${1:-cli}" in
    cli)
        check_dependencies
        if ! docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps | grep -q "Up"; then
            print_status "Services not running. Starting them now..."
            start_services
        fi
        start_cli
        ;;
    build)
        check_dependencies
        build_containers
        ;;
    start)
        check_dependencies
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    logs)
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
        ;;
    cleanup)
        cleanup
        ;;
    status)
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
        ;;
    test)
        check_dependencies
        if ! docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps | grep -q "Up"; then
            start_services
        fi
        print_status "Running test suite..."
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec app python -m pytest tests/ -v || print_warning "Some tests failed"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac