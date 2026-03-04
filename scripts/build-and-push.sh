#!/bin/bash
set -e

REGISTRY="ghcr.io/finish06"
IMAGE_NAME="rsync-viewer"
TAG=$(date +"%m%d%Y")

echo "Building ${REGISTRY}/${IMAGE_NAME}:${TAG} for amd64..."

# Create builder if it doesn't exist
docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch

# Build and push for amd64
docker buildx build \
    --platform linux/amd64 \
    --tag "${REGISTRY}/${IMAGE_NAME}:${TAG}" \
    --tag "${REGISTRY}/${IMAGE_NAME}:latest" \
    --push \
    .

echo "Successfully pushed ${REGISTRY}/${IMAGE_NAME}:${TAG} and ${REGISTRY}/${IMAGE_NAME}:latest"
