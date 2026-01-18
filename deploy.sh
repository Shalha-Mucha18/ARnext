#!/bin/bash

echo "🚀 Starting Deployment..."

# 1. Pull latest images (if you were using a registry, but here we build locally)
# echo "Pulling latest images..."
# docker compose pull

# 2. Stop existing containers
echo "🛑 Stopping current containers..."
docker compose down

# 3. Rebuild and Start
echo "🏗️ Building and Starting..."
docker compose up -d --build

# 4. Cleanup unused images (optional, saves space)
echo "🧹 Cleaning up..."
docker image prune -f

echo "✅ Deployment Complete!"
docker compose ps
