#!/bin/bash
# Start AUTOMATIC1111 Stable Diffusion WebUI

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if not already installed
if [ ! -f "installed.flag" ]; then
    echo "Installing AUTOMATIC1111..."
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git .
    pip install -r requirements.txt
    touch installed.flag
fi

# Start the web UI
echo "Starting Stable Diffusion WebUI on http://localhost:7860"
python launch.py --listen --port 7860 --enable-insecure-extension-access