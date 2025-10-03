#!/bin/bash
# Start llama.cpp server for local LLM inference

cd "$(dirname "$0")"

# Check if llama.cpp is cloned
if [ ! -d "llama.cpp" ]; then
    echo "Cloning llama.cpp..."
    git clone https://github.com/ggerganov/llama.cpp.git
    cd llama.cpp
    make
    cd ..
fi

# Check for model files
MODEL_DIR="../models"
if [ ! -d "$MODEL_DIR" ]; then
    echo "Model directory not found. Please place your GGML model files in $MODEL_DIR"
    exit 1
fi

# Find first .bin or .gguf model file
MODEL_FILE=$(find "$MODEL_DIR" -name "*.bin" -o -name "*.gguf" | head -1)
if [ -z "$MODEL_FILE" ]; then
    echo "No model files found in $MODEL_DIR"
    echo "Please download a GGML model and place it in the models directory"
    exit 1
fi

echo "Starting llama.cpp server with model: $MODEL_FILE"

# Start the server
cd llama.cpp
./server -m "$MODEL_FILE" --host 0.0.0.0 --port 8080 -c 2048 --threads $(nproc)