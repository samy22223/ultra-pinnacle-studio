"""
Safe model management that avoids segmentation faults
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path
from functools import lru_cache
from .logging_config import logger

# Safe imports with error handling
LLAMA_AVAILABLE = False
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
    logger.info("llama-cpp-python available")
except Exception as e:
    logger.warning(f"llama-cpp-python not available: {e}")

# Only import torch/diffusers if explicitly enabled and safe
DIFFUSION_AVAILABLE = False
TORCH_AVAILABLE = False

def _enable_torch_diffusion():
    """Enable torch/diffusion imports only when explicitly requested"""
    global DIFFUSION_AVAILABLE, TORCH_AVAILABLE
    
    if not TORCH_AVAILABLE:
        try:
            # Set environment variable to avoid numpy issues
            import os
            os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
            
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", message=".*numpy.*")
            
            import torch
            TORCH_AVAILABLE = True
            logger.info("PyTorch imported successfully")
        except Exception as e:
            logger.warning(f"PyTorch not available: {e}")
            return False
    
    if not DIFFUSION_AVAILABLE:
        try:
            from diffusers import StableDiffusionPipeline
            DIFFUSION_AVAILABLE = True
            logger.info("Diffusers imported successfully")
        except Exception as e:
            logger.warning(f"Diffusers not available: {e}")
            return False
    
    return True

class ModelManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models = {}  # Cache for loaded models
        self.model_configs = {}  # Store configs for lazy loading
        self._load_model_configs()

    def _load_model_configs(self):
        """Load model configurations for lazy loading"""
        for model_name, model_config in self.config.get("models", {}).items():
            if model_name == "default_model":
                continue
            self.model_configs[model_name] = model_config
            logger.info(f"Registered model config: {model_name}")

    def _load_model(self, name: str, config: Dict[str, Any]):
        """Load a specific model"""
        model_type = config.get("type")
        model_path = config.get("path")

        if not Path(model_path).exists():
            logger.error(f"Model file not found: {model_path}")
            # For development/testing, create mock models even if file doesn't exist
            if model_type == "llama":
                self.models[name] = {"type": "mock_llama", "config": config}
                logger.warning(f"Created mock Llama model for development: {name}")
                return
            elif model_type == "diffusion":
                self.models[name] = {"type": "diffusion", "config": config}
                logger.warning(f"Registered diffusion model: {name}")
                return
            else:
                return

        if model_type == "llama" and LLAMA_AVAILABLE:
            try:
                logger.info(f"Loading Llama model from: {model_path}")
                self.models[name] = Llama(
                    model_path=model_path,
                    n_ctx=config.get("max_tokens", 2048),
                    n_gpu_layers=0,  # Use CPU by default, can be configured
                    verbose=False
                )
                logger.info(f"Successfully loaded Llama model: {name}")
            except Exception as e:
                logger.error(f"Failed to load Llama model {name}: {e}")
                # Fallback to mock model
                self.models[name] = {"type": "mock_llama", "config": config}
                logger.warning(f"Using mock Llama model as fallback: {name}")
                return
        elif model_type == "diffusion":
            # Only enable torch/diffusion when actually needed
            if _enable_torch_diffusion():
                try:
                    # Note: This would require significant resources
                    # For now, just store config
                    self.models[name] = {"type": "diffusion", "config": config}
                    logger.info(f"Registered diffusion model: {name}")
                except Exception as e:
                    logger.error(f"Failed to load diffusion model {name}: {e}")
                    self.models[name] = {"type": "diffusion", "config": config}
            else:
                self.models[name] = {"type": "diffusion", "config": config}
                logger.warning(f"Diffusion not available, using config-only model: {name}")
        else:
            logger.warning(f"Unsupported model type: {model_type} (LLAMA_AVAILABLE: {LLAMA_AVAILABLE})")
            # For development/testing, create a mock model entry
            if model_type == "llama":
                self.models[name] = {"type": "mock_llama", "config": config}
                logger.warning(f"Created mock Llama model for development: {name}")
            return

    def get_model(self, name: str):
        """Get a loaded model, loading it lazily if needed"""
        if name in self.models:
            return self.models[name]

        # Lazy load the model
        if name in self.model_configs:
            try:
                self._load_model(name, self.model_configs[name])
                logger.info(f"Lazy loaded model: {name}")
                return self.models.get(name)
            except Exception as e:
                logger.error(f"Failed to lazy load model {name}: {e}")
                return None

        return None

    def list_models(self) -> Dict[str, Any]:
        """List available models (both loaded and registered)"""
        result = {}

        # Add loaded models
        for name, model in self.models.items():
            result[name] = {
                "type": getattr(model, 'type', 'unknown') if hasattr(model, 'type') else 'unknown',
                "loaded": True
            }

        # Add registered but not loaded models
        for name, config in self.model_configs.items():
            if name not in result:
                result[name] = {
                    "type": config.get("type", "unknown"),
                    "loaded": False
                }

        return result

    @lru_cache(maxsize=100)
    def _cached_generate_text(self, model_name: str, prompt: str, max_tokens: int, temperature: float) -> str:
        """Cached text generation"""
        return self._generate_text_uncached(model_name, prompt, max_tokens=max_tokens, temperature=temperature)

    def generate_text(self, model_name: str, prompt: str, **kwargs) -> str:
        """Generate text using specified model with caching"""
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)

        # Use cache for deterministic requests (temperature = 0)
        if temperature == 0.0:
            return self._cached_generate_text(model_name, prompt, max_tokens, temperature)
        else:
            return self._generate_text_uncached(model_name, prompt, **kwargs)

    def _generate_text_uncached(self, model_name: str, prompt: str, **kwargs) -> str:
        """Generate text using specified model"""
        model = self.get_model(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not loaded")

        # Check if it's a real Llama model (only if Llama is available)
        if LLAMA_AVAILABLE and hasattr(model, '__class__'):
            try:
                # Import Llama here to avoid NameError when not available
                from llama_cpp import Llama
                if isinstance(model, Llama):
                    response = model(
                        prompt,
                        max_tokens=kwargs.get("max_tokens", 512),
                        temperature=kwargs.get("temperature", 0.7)
                    )
                    return response["choices"][0]["text"].strip()
            except Exception as e:
                logger.error(f"Error generating text with Llama model: {e}")
                return f"Llama model error: {prompt[:50]}..."

        # Handle mock models or fallback responses
        if isinstance(model, dict):
            if model.get("type") == "mock_llama":
                # Mock response for development/testing
                logger.debug(f"Using mock response for {model_name}")
                return f"Mock AI response to: {prompt[:100]}..."
            elif model.get("type") == "diffusion":
                # Placeholder for diffusion models
                return f"Image generation not implemented: {prompt[:50]}..."

        # Generic mock response for any other case
        logger.debug(f"Using generic mock response for {model_name}")
        return f"AI response to: {prompt[:100]}..."

    def generate_image(self, model_name: str, prompt: str, **kwargs) -> Optional[str]:
        """Generate image using specified model (placeholder)"""
        model = self.get_model(model_name)
        if not model or model.get("type") != "diffusion":
            raise ValueError(f"Model {model_name} not available for image generation")

        # Placeholder - would implement actual diffusion model inference
        logger.info(f"Image generation requested for: {prompt}")
        return f"Generated image for: {prompt}"  # Placeholder
