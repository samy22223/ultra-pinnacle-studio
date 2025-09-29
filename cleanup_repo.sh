#!/bin/bash

# Ultra Pinnacle Studio Repository Cleanup Script
# This script cleans up the Git repository by removing large files and directories
# to reduce repository size for GitHub push

set -euo pipefail

echo "🚀 Starting Ultra Pinnacle Studio Repository Cleanup..."

# Check initial repository size
echo "📊 Initial repository size:"
du -sh .

# Remove actions-runner directory if it exists
if [ -d "actions-runner" ]; then
    echo "🗑️ Removing actions-runner directory..."
    rm -rf actions-runner
    echo "✅ actions-runner removed"
fi

# Remove large tar.gz files
if [ -f "ultra_pinnacle_studio.tar.gz" ]; then
    echo "🗑️ Removing ultra_pinnacle_studio.tar.gz..."
    rm ultra_pinnacle_studio.tar.gz
    echo "✅ ultra_pinnacle_studio.tar.gz removed"
fi

# Remove vscodium directory if it exists
if [ -d "ultra_pinnacle_studio/vscodium" ]; then
    echo "🗑️ Removing vscodium directory..."
    rm -rf ultra_pinnacle_studio/vscodium
    echo "✅ vscodium removed"
fi

# Check size after file removals
echo "📊 Size after file removals:"
du -sh .

# Git remove cached large directories
echo "🔧 Removing large directories from Git cache..."

# Remove models directory from cache if it exists
if git ls-files --error-unmatch ultra_pinnacle_studio/models/ > /dev/null 2>&1; then
    echo "🗑️ Removing models directory from Git cache..."
    git rm -r --cached ultra_pinnacle_studio/models/ 2>/dev/null || true
    echo "✅ models removed from cache"
fi

# Remove venv directory from cache if it exists
if git ls-files --error-unmatch ultra_pinnacle_studio/venv/ > /dev/null 2>&1; then
    echo "🗑️ Removing venv directory from Git cache..."
    git rm -r --cached ultra_pinnacle_studio/venv/ 2>/dev/null || true
    echo "✅ venv removed from cache"
fi

# Stage all changes
echo "📦 Staging all changes..."
git add -A

# Check Git status
echo "📋 Git status:"
git status --porcelain

# Commit changes
echo "💾 Committing cleanup changes..."
git commit -m "Clean up repository: remove large files and directories to reduce size

- Removed actions-runner directory
- Removed ultra_pinnacle_studio.tar.gz
- Removed vscodium directory
- Removed models and venv from Git cache
- Repository size reduced for GitHub compatibility"

echo "✅ Cleanup commit created"

# Check final repository size
echo "📊 Final repository size:"
du -sh .

# Check number of files
echo "📁 Number of files:"
find . -type f | wc -l

echo "🎉 Repository cleanup completed successfully!"
echo "📤 Ready for GitHub push"