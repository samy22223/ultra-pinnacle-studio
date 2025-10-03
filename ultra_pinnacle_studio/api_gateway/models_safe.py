"""
Safe model management that avoids segmentation faults
"""
from typing import Dict, Any, Optional
import json
import os
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

# API-based model imports
OPENAI_AVAILABLE = False
try:
    import openai
    OPENAI_AVAILABLE = True
    logger.info("OpenAI SDK available")
except Exception as e:
    logger.warning(f"OpenAI SDK not available: {e}")

ANTHROPIC_AVAILABLE = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
    logger.info("Anthropic SDK available")
except Exception as e:
    logger.warning(f"Anthropic SDK not available: {e}")

GOOGLE_AVAILABLE = False
try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
    logger.info("Google Generative AI SDK available")
except Exception as e:
    logger.warning(f"Google Generative AI SDK not available: {e}")

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
        self.api_clients = {}  # Cache for API clients
        self._load_model_configs()

    def _load_model_configs(self):
        """Load model configurations for lazy loading"""
        for model_name, model_config in self.config.get("models", {}).items():
            if model_name == "default_model":
                continue
            self.model_configs[model_name] = model_config
            logger.info(f"Registered model config: {model_name}")

    def _get_api_client(self, model_type: str, api_key: str):
        """Get or create API client for the specified type"""
        if model_type not in self.api_clients:
            if model_type == "openai" and OPENAI_AVAILABLE:
                client = openai.OpenAI(api_key=api_key)
                self.api_clients[model_type] = client
                logger.info("Created OpenAI client")
            elif model_type == "anthropic" and ANTHROPIC_AVAILABLE:
                client = anthropic.Anthropic(api_key=api_key)
                self.api_clients[model_type] = client
                logger.info("Created Anthropic client")
            elif model_type == "google" and GOOGLE_AVAILABLE:
                genai.configure(api_key=api_key)
                self.api_clients[model_type] = genai
                logger.info("Configured Google Generative AI")
            else:
                logger.warning(f"API client for {model_type} not available")
                return None
        return self.api_clients.get(model_type)

    def _load_model(self, name: str, config: Dict[str, Any]):
        """Load a specific model"""
        model_type = config.get("type")

        # Handle API-based models
        if model_type in ["openai", "anthropic", "google"]:
            api_key = config.get("api_key", "")
            if not api_key or api_key.startswith("${"):
                logger.warning(f"API key not configured for {name}, using mock mode")
                self.models[name] = {"type": f"mock_{model_type}", "config": config}
                return

            client = self._get_api_client(model_type, api_key)
            if client:
                self.models[name] = {"type": model_type, "client": client, "config": config}
                logger.info(f"Initialized {model_type} model: {name}")
            else:
                self.models[name] = {"type": f"mock_{model_type}", "config": config}
                logger.warning(f"Using mock {model_type} model: {name}")
            return

        # Handle local models (existing logic)
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
            logger.warning(f"Unsupported model type: {model_type}")
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

        model_type = model.get("type", "")
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)

        # Handle API-based models
        if model_type == "openai" and OPENAI_AVAILABLE:
            try:
                client = model.get("client")
                if client:
                    response = client.chat.completions.create(
                        model=model["config"]["model"],
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Error with OpenAI API: {e}")
                return f"OpenAI API error: {prompt[:50]}..."

        elif model_type == "anthropic" and ANTHROPIC_AVAILABLE:
            try:
                client = model.get("client")
                if client:
                    response = client.messages.create(
                        model=model["config"]["model"],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text.strip()
            except Exception as e:
                logger.error(f"Error with Anthropic API: {e}")
                return f"Anthropic API error: {prompt[:50]}..."

        elif model_type == "google" and GOOGLE_AVAILABLE:
            try:
                client = model.get("client")
                if client:
                    gemini_model = client.GenerativeModel(model["config"]["model"])
                    response = gemini_model.generate_content(prompt)
                    return response.text.strip()
            except Exception as e:
                logger.error(f"Error with Google API: {e}")
                return f"Google API error: {prompt[:50]}..."

        # Handle mock API models
        elif model_type in ["mock_openai", "mock_anthropic", "mock_google"]:
            logger.debug(f"Using mock API response for {model_name}")
            return f"Mock {model_type.replace('mock_', '').upper()} response to: {prompt[:100]}..."

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
        """Generate image using specified model"""
        model = self.get_model(model_name)
        if not model or model.get("type") != "diffusion":
            raise ValueError(f"Model {model_name} not available for image generation")

        if not DIFFUSION_AVAILABLE:
            logger.warning("Diffusion models not available, returning placeholder")
            return f"Image generation not available: {prompt}"

        try:
            # Enable torch/diffusion if not already enabled
            if not _enable_torch_diffusion():
                return f"Failed to initialize diffusion model: {prompt}"

            from diffusers import StableDiffusionPipeline
            import torch

            # Get model config
            model_config = model.get("config", {})
            model_path = model_config.get("path", "")

            # Use CPU by default for safety
            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda"
                logger.info("Using CUDA for image generation")
            else:
                logger.info("Using CPU for image generation (may be slow)")

            # Load pipeline (this would be cached in production)
            logger.info(f"Loading Stable Diffusion pipeline from: {model_path}")
            if model_path and Path(model_path).exists():
                pipe = StableDiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float32)
            else:
                # Use default model if path not available
                pipe = StableDiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4", torch_dtype=torch.float32)

            pipe = pipe.to(device)

            # Generate image
            width = kwargs.get("width", 512)
            height = kwargs.get("height", 512)
            steps = kwargs.get("steps", 20)
            guidance_scale = kwargs.get("guidance_scale", 7.5)
            negative_prompt = kwargs.get("negative_prompt", "")

            logger.info(f"Generating image with prompt: {prompt}")
            image = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale
            ).images[0]

            # Save image (in production, would save to proper location)
            output_dir = Path("generated_images")
            output_dir.mkdir(exist_ok=True)

            timestamp = __import__('time').time()
            image_path = output_dir / f"generated_{timestamp}.png"
            image.save(image_path)

            logger.info(f"Image generated and saved to: {image_path}")
            return str(image_path)

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return f"Image generation failed: {prompt} - Error: {str(e)}"
