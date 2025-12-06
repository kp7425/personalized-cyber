#!/bin/bash
set -e

IMAGE_NAME="security-training-app"
TAG="latest"

echo "🐳 Building Docker image: $IMAGE_NAME:$TAG"
docker build -t $IMAGE_NAME:$TAG .

# Check if we are running in a Kind user setup or just Docker Desktop
# For Docker Desktop K8s, local images are usually available immediately 
# if you DON'T use a registry prefix or if imagePullPolicy is specific.
echo "✅ Image built."
echo "ℹ️  Note: Ensure your Helm values.yaml has 'imagePullPolicy: IfNotPresent' or 'Never'"
