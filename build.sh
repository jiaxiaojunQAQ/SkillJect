#!/bin/bash
# Build Claude Code Test Image

set -e

IMAGE_NAME="claude_code"
IMAGE_TAG="${1:-v5}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "========================================="
echo "  Building Claude Code Test Image"
echo "========================================="
echo ""
echo "Image: ${FULL_IMAGE}"
echo ""

# Build image
echo "Starting build..."
docker build -f Dockerfile.claude -t ${FULL_IMAGE} .

echo ""
echo "========================================="
echo "  Build Complete!"
echo "========================================="
echo ""
echo "Image: ${FULL_IMAGE}"
echo ""
