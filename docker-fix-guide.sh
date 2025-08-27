#!/bin/bash
# Fix for libgl1-mesa-glx Docker package issue
# 
# If you're still seeing the error about libgl1-mesa-glx not being available,
# it's because this package has been replaced in newer Debian versions.
#
# Replace the problematic package with one of these alternatives:

echo "=== Docker Package Fix Options ==="
echo ""
echo "Option 1: Remove OpenGL dependencies entirely (if not needed for your image processing)"
echo "Replace: libgl1-mesa-glx"
echo "With: # libgl1-mesa-glx (commented out)"
echo ""
echo "Option 2: Use modern package names"
echo "Replace: libgl1-mesa-glx"
echo "With: libgl1-mesa-dri libglx-mesa0"
echo ""
echo "Option 3: Use minimal OpenGL support"
echo "Replace: libgl1-mesa-glx"
echo "With: libgl1"
echo ""
echo "Option 4: Use Ubuntu base instead of Debian"
echo "Change FROM line to: FROM python:3.9-slim-bullseye"
echo ""
echo "=== Current Status ==="
echo "✅ Main Dockerfile has been updated with compatible packages"
echo "✅ Alternative minimal Dockerfile created (Dockerfile.minimal)"
echo "✅ Base image pinned to bullseye for stability"
echo ""
echo "To build with the fixed Dockerfile:"
echo "docker build --no-cache -t image-upscaler-api ."
echo ""
echo "To build with the minimal Dockerfile:"
echo "docker build -f Dockerfile.minimal -t image-upscaler-api ."