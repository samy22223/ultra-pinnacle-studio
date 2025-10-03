# AI Runtimes

This directory contains scripts and configurations for running local AI models offline.

## Stable Diffusion (AUTOMATIC1111)

To run Stable Diffusion locally:

1. Place your model files in `ai_runtimes/models/`
2. Run the start script:
   ```bash
   cd ai_runtimes/sd_automatic
   chmod +x start_auto1111.sh
   ./start_auto1111.sh
   ```
3. Access the web UI at http://localhost:7860

## Llama.cpp (LLM Inference)

To run local LLM inference:

1. Download a GGML model (e.g., from Hugging Face)
2. Place the model file (.bin or .gguf) in `ai_runtimes/models/`
3. Run the start script:
   ```bash
   cd ai_runtimes/llama_service
   chmod +x start_llama_service.sh
   ./start_llama_service.sh
   ```
4. The API will be available at http://localhost:8080

## Model Acquisition

**Important:** Models must be downloaded separately due to licensing. Place them in the appropriate directories:

- Stable Diffusion models: `ai_runtimes/models/sd/`
- LLM models: `ai_runtimes/models/llm/`

Legal sources:
- Hugging Face (GGUF models)
- Civitai (Stable Diffusion models)
- Official model repositories

## Integration

These runtimes integrate with the main Ultra Pinnacle Studio API for:
- AI-assisted prompt enhancement
- Pattern generation
- Chat functionality
- Image generation for fashion design