#!/bin/bash

# Rsync script to sync project to remote server
# Usage: ./sync.sh [user@]host:/path/to/destination

# Check if destination argument is provided
if [ -z "$1" ]; then
    echo "Usage: ./sync.sh [user@]host:/path/to/destination"
    echo "Example: ./sync.sh user@server.com:/home/user/projects/segment"
    exit 1
fi

DESTINATION=$1
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Syncing from: $SOURCE_DIR"
echo "Syncing to: $DESTINATION"
echo ""

rsync -avz --progress \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='.ruff_cache/' \
    --exclude='*.egg-info/' \
    --exclude='.git/' \
    --exclude='.DS_Store' \
    "$SOURCE_DIR/" "$DESTINATION"

echo ""
echo "Sync complete!"
