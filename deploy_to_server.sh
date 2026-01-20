#!/bin/bash

# ============================================
# ArNext-Intelligence Server Deployment Script
# ============================================
# This script automates deployment to your production server
# Server IP: 203.202.241.210
# ============================================

set -e  # Exit on any error

# Configuration
SERVER_IP="203.202.241.210"
SERVER_USER="ibos"  # Updated to use ibos user
DEPLOY_DIR="/opt/ARnext"
GITHUB_REPO="git@github.com:Shalha-Mucha18/ARnext.git"
GITHUB_REPO_HTTPS="https://github.com/Shalha-Mucha18/ARnext.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ArNext-Intelligence Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists locally
if [ ! -f ".env" ]; then
    print_error ".env file not found in current directory!"
    print_info "Please create a .env file with your configuration before deploying."
    exit 1
fi

print_info "Found .env file locally"

# Test SSH connection
print_info "Testing SSH connection to $SERVER_USER@$SERVER_IP..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    print_error "Cannot connect to server via SSH"
    print_info "Please ensure:"
    print_info "  1. You have SSH access to the server"
    print_info "  2. Your SSH key is added to the server"
    print_info "  3. The server IP is correct: $SERVER_IP"
    exit 1
fi

print_info "SSH connection successful!"

# Deploy to server
print_info "Starting deployment to server..."

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
set -e

# Colors for remote output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[REMOTE]${NC} Connected to server"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[REMOTE]${NC} Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}[REMOTE]${NC} Docker installed successfully"
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}[REMOTE]${NC} Docker Compose not found!"
    exit 1
fi

echo -e "${GREEN}[REMOTE]${NC} Docker and Docker Compose are installed"

# Create deployment directory if it doesn't exist
if [ ! -d "/opt/ARnext" ]; then
    echo -e "${GREEN}[REMOTE]${NC} Creating deployment directory..."
    mkdir -p /opt/ARnext
    cd /opt/ARnext
    
    # Try SSH clone first, fallback to HTTPS
    echo -e "${GREEN}[REMOTE]${NC} Cloning repository..."
    if ! git clone git@github.com:Shalha-Mucha18/ARnext.git .; then
        echo -e "${YELLOW}[REMOTE]${NC} SSH clone failed, trying HTTPS..."
        git clone https://github.com/Shalha-Mucha18/ARnext.git .
    fi
else
    echo -e "${GREEN}[REMOTE]${NC} Updating existing repository..."
    cd /opt/ARnext
    git fetch origin
    git pull origin main || git pull origin master
fi

echo -e "${GREEN}[REMOTE]${NC} Repository is up to date"
ENDSSH

# Copy .env file to server
print_info "Copying .env file to server..."
scp .env $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/.env

# Copy production docker-compose if it exists
if [ -f "docker-compose.production.yml" ]; then
    print_info "Copying production docker-compose configuration..."
    scp docker-compose.production.yml $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/docker-compose.yml
fi

# Deploy the application
print_info "Deploying application on server..."

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /opt/ARnext

echo -e "${GREEN}[REMOTE]${NC} Stopping existing containers..."
docker compose down || true

echo -e "${GREEN}[REMOTE]${NC} Building and starting containers..."
docker compose up -d --build

echo -e "${GREEN}[REMOTE]${NC} Cleaning up old images..."
docker image prune -f

echo -e "${GREEN}[REMOTE]${NC} Deployment complete!"
echo ""
echo -e "${GREEN}[REMOTE]${NC} Container status:"
docker compose ps

echo ""
echo -e "${GREEN}[REMOTE]${NC} Application URLs:"
echo -e "  Frontend: http://203.202.241.210:3000"
echo -e "  Backend API: http://203.202.241.210:8000"
echo -e "  API Docs: http://203.202.241.210:8000/docs"
ENDSSH

print_info "Deployment completed successfully!"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Frontend:    ${GREEN}http://$SERVER_IP:3000${NC}"
echo -e "Backend API: ${GREEN}http://$SERVER_IP:8000${NC}"
echo -e "API Docs:    ${GREEN}http://$SERVER_IP:8000/docs${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
print_info "To view logs, run:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker compose logs -f'"
