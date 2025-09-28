from typing import Dict, Any, Optional
import json
from pathlib import Path
from .logging_config import logger

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("llama-cpp-python not available")

try:
    from diffusers import StableDiffusionPipeline
    import torch
    DIFFUSION_AVAILABLE = True
except ImportError:
    DIFFUSION_AVAILABLE = False
    logger.warning("diffusers not available")

class ModelManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models = {}
        self._load_models()

    def _load_models(self):
        """Load all configured models"""
        for model_name, model_config in self.config.get("models", {}).items():
            if model_name == "default_model":
                continue
            try:
                self._load_model(model_name, model_config)
                logger.info(f"Loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")

    def _load_model(self, name: str, config: Dict[str, Any]):
        """Load a specific model"""
        model_type = config.get("type")
        model_path = config.get("path")

        if not Path(model_path).exists():
            logger.warning(f"Model file not found: {model_path}")
            return

        if model_type == "llama" and LLAMA_AVAILABLE:
            self.models[name] = Llama(
                model_path=model_path,
                n_ctx=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7)
            )
        elif model_type == "diffusion" and DIFFUSION_AVAILABLE:
            # Note: This would require significant resources
            # For now, just store config
            self.models[name] = {"type": "diffusion", "config": config}
        else:
            logger.warning(f"Unsupported model type: {model_type}")

    def get_model(self, name: str):
        """Get a loaded model"""
        return self.models.get(name)

    def list_models(self) -> Dict[str, Any]:
        """List available models"""
        return {
            name: {
                "type": getattr(model, 'type', 'unknown') if hasattr(model, 'type') else 'unknown',
                "loaded": True
            }
            for name, model in self.models.items()
        }

    def generate_text(self, model_name: str, prompt: str, **kwargs) -> str:
        """Generate text using specified model"""
        model = self.get_model(model_name)
        if not model:
            # For testing/development, provide mock responses when model is not loaded
            if "llama" in model_name.lower():
                return f"Mock response for: {prompt[:50]}..."
            raise ValueError(f"Model {model_name} not loaded")

        if isinstance(model, Llama):
            response = model(
                prompt,
                max_tokens=kwargs.get("max_tokens", 512),
                temperature=kwargs.get("temperature", 0.7)
            )
            return response["choices"][0]["text"].strip()
        else:
            # Mock response for unsupported models
            return f"Mock response for {model_name}: {prompt[:50]}..."

    def generate_image(self, model_name: str, prompt: str, **kwargs) -> Optional[str]:
        """Generate image using specified model (placeholder)"""
        model = self.get_model(model_name)
        if not model or model.get("type") != "diffusion":
            raise ValueError(f"Model {model_name} not available for image generation")

        # Placeholder - would implement actual diffusion model inference
        logger.info(f"Image generation requested for: {prompt}")
        return f"Generated image for: {prompt}"  # Placeholder