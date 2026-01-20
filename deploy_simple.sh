#!/bin/bash

# Simple deployment script using password authentication
# Server: 203.202.241.210
# User: ibos

set -e

SERVER="ibos@203.202.241.210"
DEPLOY_DIR="/home/ibos/ARnext"

echo "========================================="
echo "Deploying to Server"
echo "========================================="
echo ""

echo "[1/6] Testing SSH connection..."
ssh -o StrictHostKeyChecking=no $SERVER "echo 'Connection successful!'"

echo ""
echo "[2/6] Creating deployment directory..."
ssh $SERVER "mkdir -p $DEPLOY_DIR"

echo ""
echo "[3/6] Cloning/Updating repository..."
ssh $SERVER << 'ENDSSH'
cd /home/ibos/ARnext

if [ -d ".git" ]; then
    echo "Repository exists, pulling latest changes..."
    git pull origin main || git pull origin master
else
    echo "Cloning repository..."
    git clone https://github.com/Shalha-Mucha18/ARnext.git .
fi
ENDSSH

echo ""
echo "[4/6] Copying .env file to server..."
scp .env $SERVER:$DEPLOY_DIR/.env

echo ""
echo "[5/6] Checking Docker installation..."
ssh $SERVER << 'ENDSSH'
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
fi

if ! docker compose version &> /dev/null; then
    echo "Docker Compose not found!"
    exit 1
fi

echo "Docker is ready!"
ENDSSH

echo ""
echo "[6/6] Deploying application..."
ssh $SERVER << 'ENDSSH'
cd /home/ibos/ARnext

echo "Stopping existing containers..."
docker compose down || true

echo "Building and starting containers..."
docker compose up -d --build

echo "Cleaning up old images..."
docker image prune -f

echo ""
echo "Deployment complete!"
echo ""
echo "Container status:"
docker compose ps

echo ""
echo "========================================="
echo "Application URLs:"
echo "  Frontend: http://203.202.241.210:3000"
echo "  Backend API: http://203.202.241.210:8000"
echo "  API Docs: http://203.202.241.210:8000/docs"
echo "========================================="
ENDSSH

echo ""
echo "✅ Deployment completed successfully!"
