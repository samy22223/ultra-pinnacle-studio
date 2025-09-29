"""
Plugin system for Ultra Pinnacle AI Studio
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging
import importlib
import os
from pathlib import Path

logger = logging.getLogger("ultra_pinnacle")

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

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin"""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin"""
        pass

class APIPlugin(PluginBase):
    """Plugin that adds API endpoints"""

    @abstractmethod
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get FastAPI routes provided by this plugin"""
        pass

class ProcessingPlugin(PluginBase):
    """Plugin that provides data processing capabilities"""

    @abstractmethod
    def process_data(self, data: Any, data_type: str) -> Any:
        """Process data of specified type"""
        pass

class StoragePlugin(PluginBase):
    """Plugin that provides storage backends"""

    @abstractmethod
    def store(self, key: str, value: Any) -> bool:
        """Store value with key"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Any:
        """Retrieve value by key"""
        pass

class PluginManager:
    """Manages plugin loading and lifecycle"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_dir = Path(__file__).parent / "plugins"
        self.plugin_dir.mkdir(exist_ok=True)

    def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin"""
        try:
            # Try to import plugin module
            module_name = f"api_gateway.plugins.{plugin_name}"
            plugin_module = importlib.import_module(module_name)

            # Find plugin class
            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr != PluginBase and
                    attr != APIPlugin and
                    attr != ProcessingPlugin and
                    attr != StoragePlugin):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No plugin class found in {plugin_name}")
                return False

            # Instantiate and initialize plugin
            plugin_instance = plugin_class()
            if plugin_instance.initialize(self.config):
                self.plugins[plugin_name] = plugin_instance
                logger.info(f"Plugin {plugin_name} loaded successfully")
                return True
            else:
                logger.error(f"Plugin {plugin_name} failed to initialize")
                return False

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False

    def load_all_plugins(self) -> int:
        """Load all available plugins"""
        loaded_count = 0

        # Look for plugin files
        for plugin_file in self.plugin_dir.glob("*.py"):
            plugin_name = plugin_file.stem
            if self.load_plugin(plugin_name):
                loaded_count += 1

        logger.info(f"Loaded {loaded_count} plugins")
        return loaded_count

    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Get all API routes from plugins"""
        routes = []
        for plugin in self.plugins.values():
            if isinstance(plugin, APIPlugin):
                routes.extend(plugin.get_routes())
        return routes

    def process_data(self, data: Any, data_type: str) -> Any:
        """Process data using available processing plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, ProcessingPlugin):
                try:
                    result = plugin.process_data(data, data_type)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"Error processing data with plugin {plugin.name}: {e}")
        return data  # Return original data if no plugin processed it

    def store_data(self, key: str, value: Any) -> bool:
        """Store data using available storage plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, StoragePlugin):
                try:
                    if plugin.store(key, value):
                        return True
                except Exception as e:
                    logger.error(f"Error storing data with plugin {plugin.name}: {e}")
        return False

    def retrieve_data(self, key: str) -> Any:
        """Retrieve data using available storage plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, StoragePlugin):
                try:
                    result = plugin.retrieve(key)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"Error retrieving data with plugin {plugin.name}: {e}")
        return None

    def shutdown_all(self) -> None:
        """Shutdown all plugins"""
        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin.name}: {e}")
        self.plugins.clear()
        logger.info("All plugins shut down")

# Example plugins (can be moved to separate files)

class ExampleAPIPlugin(APIPlugin):
    """Example API plugin"""

    @property
    def name(self) -> str:
        return "example_api"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Example API plugin initialized")
        return True

    def shutdown(self) -> None:
        logger.info("Example API plugin shut down")

    def get_routes(self) -> List[Dict[str, Any]]:
        return [{
            'path': '/api/example',
            'methods': ['GET'],
            'handler': self.example_handler,
            'summary': 'Example endpoint'
        }]

    def example_handler(self):
        return {"message": "Hello from example plugin"}

class ExampleProcessingPlugin(ProcessingPlugin):
    """Example processing plugin"""

    @property
    def name(self) -> str:
        return "example_processing"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Example processing plugin initialized")
        return True

    def shutdown(self) -> None:
        logger.info("Example processing plugin shut down")

    def process_data(self, data: Any, data_type: str) -> Any:
        if data_type == "text" and isinstance(data, str):
            return f"Processed: {data}"
        return None

class ExampleStoragePlugin(StoragePlugin):
    """Example storage plugin using in-memory storage"""

    def __init__(self):
        self.storage: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "example_storage"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Example storage plugin initialized")
        return True

    def shutdown(self) -> None:
        self.storage.clear()
        logger.info("Example storage plugin shut down")

    def store(self, key: str, value: Any) -> bool:
        self.storage[key] = value
        return True

    def retrieve(self, key: str) -> Any:
        return self.storage.get(key)

logger.info("Plugin system initialized")