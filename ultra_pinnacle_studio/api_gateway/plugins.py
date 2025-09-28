"""
Plugin System for Ultra Pinnacle AI Studio
Allows extending functionality through modular plugins
"""

import importlib
import inspect
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PluginBase(ABC):
    """Base class for all plugins"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass

class APIPlugin(PluginBase):
    """Plugin that extends API functionality"""

    @abstractmethod
    def get_routes(self) -> List[Dict[str, Any]]:
        """Return list of routes to add to the API"""
        pass

    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """Return list of AI models provided by this plugin"""
        pass

class ProcessingPlugin(PluginBase):
    """Plugin that provides data processing capabilities"""

    @abstractmethod
    def can_process(self, data_type: str) -> bool:
        """Check if plugin can process given data type"""
        pass

    @abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """Process the given data"""
        pass

class StoragePlugin(PluginBase):
    """Plugin that provides storage capabilities"""

    @abstractmethod
    def store(self, key: str, data: Any) -> bool:
        """Store data with given key"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data for given key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data for given key"""
        pass

class PluginManager:
    """Manages plugin loading, initialization, and lifecycle"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugins_dir = Path(config.get('paths', {}).get('plugins_dir', 'plugins/'))
        self.plugins_dir.mkdir(exist_ok=True)

        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}

        # Plugin categories
        self.api_plugins: List[APIPlugin] = []
        self.processing_plugins: List[ProcessingPlugin] = []
        self.storage_plugins: List[StoragePlugin] = []

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory"""
        plugins = []

        # Look for plugin directories
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                plugin_file = item / '__init__.py'
                if plugin_file.exists():
                    plugins.append(item.name)

        # Also check for single-file plugins
        for item in self.plugins_dir.glob('*.py'):
            if not item.name.startswith('__'):
                plugins.append(item.stem)

        return plugins

    def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin"""
        try:
            # Import the plugin module
            if (self.plugins_dir / plugin_name / '__init__.py').exists():
                # Package plugin
                module = importlib.import_module(f'plugins.{plugin_name}')
            else:
                # Single-file plugin
                spec = importlib.util.spec_from_file_location(
                    plugin_name,
                    self.plugins_dir / f'{plugin_name}.py'
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # Find plugin classes
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginBase) and
                    obj != PluginBase):
                    plugin_classes.append(obj)

            if not plugin_classes:
                logger.warning(f"No plugin classes found in {plugin_name}")
                return False

            # Instantiate and initialize plugins
            for plugin_class in plugin_classes:
                plugin_instance = plugin_class()
                plugin_config = self.config.get('plugins', {}).get(plugin_name, {})

                if plugin_instance.initialize(plugin_config):
                    self.loaded_plugins[plugin_instance.name] = plugin_instance

                    # Categorize plugin
                    if isinstance(plugin_instance, APIPlugin):
                        self.api_plugins.append(plugin_instance)
                    if isinstance(plugin_instance, ProcessingPlugin):
                        self.processing_plugins.append(plugin_instance)
                    if isinstance(plugin_instance, StoragePlugin):
                        self.storage_plugins.append(plugin_instance)

                    # Store metadata
                    self.plugin_metadata[plugin_instance.name] = {
                        'version': plugin_instance.version,
                        'description': plugin_instance.description,
                        'type': type(plugin_instance).__name__,
                        'module': plugin_name
                    }

                    logger.info(f"Loaded plugin: {plugin_instance.name} v{plugin_instance.version}")
                else:
                    logger.error(f"Failed to initialize plugin: {plugin_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False

    def load_all_plugins(self) -> int:
        """Load all discovered plugins"""
        plugin_names = self.discover_plugins()
        loaded_count = 0

        for plugin_name in plugin_names:
            if self.load_plugin(plugin_name):
                loaded_count += 1

        logger.info(f"Loaded {loaded_count}/{len(plugin_names)} plugins")
        return loaded_count

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin"""
        if plugin_name not in self.loaded_plugins:
            return False

        plugin = self.loaded_plugins[plugin_name]
        try:
            plugin.cleanup()

            # Remove from categories
            if isinstance(plugin, APIPlugin):
                self.api_plugins.remove(plugin)
            if isinstance(plugin, ProcessingPlugin):
                self.processing_plugins.remove(plugin)
            if isinstance(plugin, StoragePlugin):
                self.storage_plugins.remove(plugin)

            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]
            del self.plugin_metadata[plugin_name]

            logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a loaded plugin by name"""
        return self.loaded_plugins.get(name)

    def list_plugins(self) -> Dict[str, Any]:
        """List all loaded plugins with metadata"""
        return {
            'loaded_plugins': self.plugin_metadata,
            'api_plugins': [p.name for p in self.api_plugins],
            'processing_plugins': [p.name for p in self.processing_plugins],
            'storage_plugins': [p.name for p in self.storage_plugins]
        }

    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Get all API routes from API plugins"""
        all_routes = []
        for plugin in self.api_plugins:
            try:
                routes = plugin.get_routes()
                all_routes.extend(routes)
            except Exception as e:
                logger.error(f"Error getting routes from plugin {plugin.name}: {e}")
        return all_routes

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get all AI models from API plugins"""
        all_models = []
        for plugin in self.api_plugins:
            try:
                models = plugin.get_models()
                all_models.extend(models)
            except Exception as e:
                logger.error(f"Error getting models from plugin {plugin.name}: {e}")
        return all_models

    def process_data(self, data: Any, data_type: str, **kwargs) -> Optional[Any]:
        """Process data using available processing plugins"""
        for plugin in self.processing_plugins:
            if plugin.can_process(data_type):
                try:
                    return plugin.process(data, **kwargs)
                except Exception as e:
                    logger.error(f"Error processing data with plugin {plugin.name}: {e}")
        return None

    def store_data(self, key: str, data: Any) -> bool:
        """Store data using available storage plugins"""
        for plugin in self.storage_plugins:
            try:
                if plugin.store(key, data):
                    return True
            except Exception as e:
                logger.error(f"Error storing data with plugin {plugin.name}: {e}")
        return False

    def retrieve_data(self, key: str) -> Optional[Any]:
        """Retrieve data using available storage plugins"""
        for plugin in self.storage_plugins:
            try:
                data = plugin.retrieve(key)
                if data is not None:
                    return data
            except Exception as e:
                logger.error(f"Error retrieving data with plugin {plugin.name}: {e}")
        return None

# Example plugin implementations
class ExampleAPIPlugin(APIPlugin):
    """Example API plugin implementation"""

    @property
    def name(self) -> str:
        return "example_api_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example plugin demonstrating API extension capabilities"

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Example API plugin initialized")
        return True

    def cleanup(self) -> None:
        logger.info("Example API plugin cleaned up")

    def get_routes(self) -> List[Dict[str, Any]]:
        return [
            {
                'path': '/example',
                'methods': ['GET'],
                'handler': self.example_endpoint,
                'summary': 'Example plugin endpoint'
            }
        ]

    def get_models(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'example_model',
                'type': 'example',
                'description': 'Example AI model from plugin'
            }
        ]

    async def example_endpoint(self):
        """Example endpoint implementation"""
        return {"message": "Hello from example plugin!", "plugin": self.name}

class ExampleProcessingPlugin(ProcessingPlugin):
    """Example processing plugin implementation"""

    @property
    def name(self) -> str:
        return "example_processing_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example plugin demonstrating data processing capabilities"

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Example processing plugin initialized")
        return True

    def cleanup(self) -> None:
        logger.info("Example processing plugin cleaned up")

    def can_process(self, data_type: str) -> bool:
        return data_type in ['text', 'json']

    def process(self, data: Any, **kwargs) -> Any:
        # Simple example: convert to uppercase
        if isinstance(data, str):
            return data.upper()
        elif isinstance(data, dict):
            return {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
        return data

def create_plugin_template(plugin_type: str, plugin_name: str) -> str:
    """Create a template for a new plugin"""
    if plugin_type == 'api':
        template = f'''from plugins import APIPlugin
from typing import Dict, List, Any

class {plugin_name.title()}Plugin(APIPlugin):
    """Custom API plugin"""

    @property
    def name(self) -> str:
        return "{plugin_name}"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Custom {plugin_name} plugin"

    def initialize(self, config: Dict[str, Any]) -> bool:
        # Initialize your plugin here
        return True

    def cleanup(self) -> None:
        # Cleanup resources here
        pass

    def get_routes(self) -> List[Dict[str, Any]]:
        return [
            {{
                'path': '/{plugin_name}',
                'methods': ['GET'],
                'handler': self.{plugin_name}_endpoint,
                'summary': '{plugin_name.title()} endpoint'
            }}
        ]

    def get_models(self) -> List[Dict[str, Any]]:
        return []

    async def {plugin_name}_endpoint(self):
        """Custom endpoint implementation"""
        return {{"message": "Hello from {plugin_name} plugin!"}}
'''
    elif plugin_type == 'processing':
        template = f'''from plugins import ProcessingPlugin
from typing import Any

class {plugin_name.title()}ProcessingPlugin(ProcessingPlugin):
    """Custom processing plugin"""

    @property
    def name(self) -> str:
        return "{plugin_name}_processing"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Custom {plugin_name} processing plugin"

    def initialize(self, config: Dict[str, Any]) -> bool:
        return True

    def cleanup(self) -> None:
        pass

    def can_process(self, data_type: str) -> bool:
        return data_type in ['text']  # Specify supported data types

    def process(self, data: Any, **kwargs) -> Any:
        # Implement your processing logic here
        return data
'''
    else:
        template = "# Unsupported plugin type"

    return template