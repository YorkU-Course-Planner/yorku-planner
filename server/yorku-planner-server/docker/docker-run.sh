#!/bin/bash

# YorkU Planner Server Docker Runner
echo "🚀 Starting YorkU Planner Server with Docker..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and run with docker-compose
echo "📦 Building and starting the application..."
docker-compose up --build

echo "✅ Application started! Access it at http://localhost:8080"
echo "📊 H2 Console available at http://localhost:8080/h2-console" 