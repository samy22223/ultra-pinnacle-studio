"""
Comprehensive Plugin System for Ultra Pinnacle AI Studio
"""
from typing import Dict, Any, List, Optional, Callable, Set, Union
from abc import ABC, abstractmethod
import logging
import importlib
import os
import json
import hashlib
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import inspect

logger = logging.getLogger("ultra_pinnacle")

class PluginState(Enum):
    """Plugin lifecycle states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    ENABLING = "enabling"
    ENABLED = "enabled"
    DISABLING = "disabling"
    DISABLED = "disabled"
    UNLOADING = "unloading"
    ERROR = "error"

class PluginPermission(Enum):
    """Plugin permission levels"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

@dataclass
class PluginMetadata:
    """Plugin metadata structure"""
    name: str
    version: str
    description: str
    author: str
    license: str = ""
    homepage: str = ""
    repository: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    min_core_version: str = ""
    max_core_version: str = ""
    checksum: str = ""
    created_at: str = ""
    updated_at: str = ""

@dataclass
class PluginContext:
    """Execution context for plugins"""
    plugin_id: str
    permissions: Set[PluginPermission]
    sandbox_level: str
    execution_timeout: int = 30
    memory_limit: int = 100  # MB
    cpu_limit: float = 0.5  # CPU cores

class HookPoint(Enum):
    """Available hook points in the system"""
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    PRE_MODEL_LOAD = "pre_model_load"
    POST_MODEL_LOAD = "post_model_load"
    PRE_INFERENCE = "pre_inference"
    POST_INFERENCE = "post_inference"
    PRE_DATA_PROCESS = "pre_data_process"
    POST_DATA_PROCESS = "post_data_process"
    PRE_FILE_UPLOAD = "pre_file_upload"
    POST_FILE_UPLOAD = "post_file_upload"
    PRE_USER_AUTH = "pre_user_auth"
    POST_USER_AUTH = "post_user_auth"

class PluginBase(ABC):
    """Enhanced base class for all plugins"""

    def __init__(self):
        self._metadata: Optional[PluginMetadata] = None
        self._context: Optional[PluginContext] = None
        self._state: PluginState = PluginState.UNLOADED
        self._hooks: Dict[HookPoint, List[Callable]] = {}
        self._settings: Dict[str, Any] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}

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
    def metadata(self) -> Optional[PluginMetadata]:
        """Plugin metadata"""
        return self._metadata

    @property
    def state(self) -> PluginState:
        """Current plugin state"""
        return self._state

    @property
    def context(self) -> Optional[PluginContext]:
        """Plugin execution context"""
        return self._context

    @abstractmethod
    def initialize(self, config: Dict[str, Any], context: PluginContext) -> bool:
        """Initialize the plugin with enhanced context"""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin"""
        pass

    def enable(self) -> bool:
        """Enable the plugin"""
        if self._state == PluginState.INITIALIZED:
            self._state = PluginState.ENABLING
            try:
                self.on_enable()
                self._state = PluginState.ENABLED
                return True
            except Exception as e:
                logger.error(f"Error enabling plugin {self.name}: {e}")
                self._state = PluginState.ERROR
                return False
        return False

    def disable(self) -> bool:
        """Disable the plugin"""
        if self._state == PluginState.ENABLED:
            self._state = PluginState.DISABLING
            try:
                self.on_disable()
                self._state = PluginState.DISABLED
                return True
            except Exception as e:
                logger.error(f"Error disabling plugin {self.name}: {e}")
                self._state = PluginState.ERROR
                return False
        return False

    def register_hook(self, hook_point: HookPoint, callback: Callable) -> None:
        """Register a hook callback"""
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        self._hooks[hook_point].append(callback)

    def unregister_hook(self, hook_point: HookPoint, callback: Callable) -> None:
        """Unregister a hook callback"""
        if hook_point in self._hooks:
            self._hooks[hook_point] = [cb for cb in self._hooks[hook_point] if cb != callback]

    def register_event_handler(self, event_type: str, callback: Callable) -> None:
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(callback)

    def unregister_event_handler(self, event_type: str, callback: Callable) -> None:
        """Unregister an event handler"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [cb for cb in self._event_handlers[event_type] if cb != callback]

    def emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to registered handlers"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a plugin setting"""
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set a plugin setting"""
        self._settings[key] = value

    def save_settings(self) -> None:
        """Save plugin settings (to be implemented by manager)"""
        pass

    def load_settings(self) -> None:
        """Load plugin settings (to be implemented by manager)"""
        pass

    # Lifecycle hooks for subclasses
    def on_enable(self) -> None:
        """Called when plugin is enabled"""
        pass

    def on_disable(self) -> None:
        """Called when plugin is disabled"""
        pass

    def on_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Called when plugin settings are changed"""
        pass

class APIPlugin(PluginBase):
    """Plugin that adds API endpoints"""

    @abstractmethod
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get FastAPI routes provided by this plugin"""
        pass

    def register_api_hooks(self) -> None:
        """Register API-related hooks"""
        self.register_hook(HookPoint.PRE_REQUEST, self.on_pre_request)
        self.register_hook(HookPoint.POST_REQUEST, self.on_post_request)

    def on_pre_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pre-request processing"""
        return request_data

    def on_post_request(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle post-request processing"""
        return response_data

class ProcessingPlugin(PluginBase):
    """Plugin that provides data processing capabilities"""

    @abstractmethod
    def process_data(self, data: Any, data_type: str, **kwargs) -> Any:
        """Process data of specified type"""
        pass

    def register_processing_hooks(self) -> None:
        """Register processing-related hooks"""
        self.register_hook(HookPoint.PRE_DATA_PROCESS, self.on_pre_process)
        self.register_hook(HookPoint.POST_DATA_PROCESS, self.on_post_process)

    def on_pre_process(self, data: Any, data_type: str) -> Any:
        """Pre-process data"""
        return data

    def on_post_process(self, data: Any, data_type: str) -> Any:
        """Post-process data"""
        return data

class StoragePlugin(PluginBase):
    """Plugin that provides storage backends"""

    @abstractmethod
    def store(self, key: str, value: Any, **kwargs) -> bool:
        """Store value with key"""
        pass

    @abstractmethod
    def retrieve(self, key: str, **kwargs) -> Any:
        """Retrieve value by key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value by key"""
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix"""
        pass

class UIPlugin(PluginBase):
    """Plugin that provides UI components"""

    @abstractmethod
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get UI components provided by this plugin"""
        pass

    @abstractmethod
    def get_ui_routes(self) -> List[Dict[str, Any]]:
        """Get UI routes provided by this plugin"""
        pass

class AIModelPlugin(PluginBase):
    """Plugin that provides AI model integrations"""

    @abstractmethod
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """Get list of supported AI models"""
        pass

    @abstractmethod
    def load_model(self, model_name: str, **kwargs) -> Any:
        """Load an AI model"""
        pass

    @abstractmethod
    def generate(self, model_name: str, prompt: str, **kwargs) -> str:
        """Generate text using a model"""
        pass

    def register_ai_hooks(self) -> None:
        """Register AI-related hooks"""
        self.register_hook(HookPoint.PRE_MODEL_LOAD, self.on_pre_model_load)
        self.register_hook(HookPoint.POST_MODEL_LOAD, self.on_post_model_load)
        self.register_hook(HookPoint.PRE_INFERENCE, self.on_pre_inference)
        self.register_hook(HookPoint.POST_INFERENCE, self.on_post_inference)

    def on_pre_model_load(self, model_name: str) -> str:
        """Pre-model load processing"""
        return model_name

    def on_post_model_load(self, model_name: str, model: Any) -> Any:
        """Post-model load processing"""
        return model

    def on_pre_inference(self, model_name: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Pre-inference processing"""
        return {"model_name": model_name, "prompt": prompt, **kwargs}

    def on_post_inference(self, model_name: str, result: str, **kwargs) -> str:
        """Post-inference processing"""
        return result

class DataSourcePlugin(PluginBase):
    """Plugin that provides external data source integrations"""

    @abstractmethod
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get available data sources"""
        pass

    @abstractmethod
    def connect(self, source_id: str, config: Dict[str, Any]) -> bool:
        """Connect to a data source"""
        pass

    @abstractmethod
    def query(self, source_id: str, query: str, **kwargs) -> Any:
        """Query a data source"""
        pass

    @abstractmethod
    def disconnect(self, source_id: str) -> bool:
        """Disconnect from a data source"""
        pass

class WorkflowPlugin(PluginBase):
    """Plugin that provides custom workflow automation"""

    @abstractmethod
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get available workflows"""
        pass

    @abstractmethod
    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow"""
        pass

    @abstractmethod
    def create_workflow(self, config: Dict[str, Any]) -> str:
        """Create a new workflow"""
        pass

class PluginSandbox:
    """Plugin execution sandbox"""

    def __init__(self, context: PluginContext):
        self.context = context
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"plugin-{context.plugin_id}")
        self._lock = threading.Lock()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function in the sandbox"""
        with self._lock:
            try:
                # Check permissions
                if not self._check_permissions(func):
                    raise PermissionError(f"Function {func.__name__} not allowed in current permission level")

                # Execute with timeout
                future = self.executor.submit(func, *args, **kwargs)
                return future.result(timeout=self.context.execution_timeout)
            except Exception as e:
                logger.error(f"Sandbox execution error for plugin {self.context.plugin_id}: {e}")
                raise

    def _check_permissions(self, func: Callable) -> bool:
        """Check if function execution is allowed"""
        # Basic permission checking - can be extended
        func_name = func.__name__
        if self.context.permissions == {PluginPermission.ADMIN}:
            return True
        elif self.context.permissions == {PluginPermission.EXECUTE}:
            # Allow basic execution but restrict dangerous operations
            dangerous_funcs = ['exec', 'eval', 'open', 'system', 'subprocess']
            return not any(df in func_name for df in dangerous_funcs)
        elif self.context.permissions == {PluginPermission.WRITE}:
            # Allow read/write but no execution
            return func_name not in ['exec', 'eval', 'system', 'subprocess']
        elif self.context.permissions == {PluginPermission.READ}:
            # Read-only operations
            read_only_funcs = ['get', 'read', 'list', 'find', 'search']
            return any(rof in func_name for rof in read_only_funcs)
        return False

class PluginEventBus:
    """Event-driven communication system for plugins"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to an event"""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event"""
        with self._lock:
            if event_type in self._listeners:
                self._listeners[event_type] = [cb for cb in self._listeners[event_type] if cb != callback]

    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event"""
        with self._lock:
            if event_type in self._listeners:
                for callback in self._listeners[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(data))
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"Error in event listener for {event_type}: {e}")

class PluginHookSystem:
    """Hook system for extending core functionality"""

    def __init__(self):
        self._hooks: Dict[HookPoint, List[Callable]] = {}
        self._lock = threading.Lock()

    def register_hook(self, hook_point: HookPoint, callback: Callable, priority: int = 0) -> None:
        """Register a hook callback"""
        with self._lock:
            if hook_point not in self._hooks:
                self._hooks[hook_point] = []
            # Insert based on priority (higher priority = executed first)
            self._hooks[hook_point].append((priority, callback))
            self._hooks[hook_point].sort(key=lambda x: x[0], reverse=True)

    def unregister_hook(self, hook_point: HookPoint, callback: Callable) -> None:
        """Unregister a hook callback"""
        with self._lock:
            if hook_point in self._hooks:
                self._hooks[hook_point] = [(p, cb) for p, cb in self._hooks[hook_point] if cb != callback]

    def execute_hooks(self, hook_point: HookPoint, *args, **kwargs) -> Any:
        """Execute all hooks for a point"""
        with self._lock:
            if hook_point not in self._hooks:
                return args[0] if args else None

            result = args[0] if args else None
            for _, callback in self._hooks[hook_point]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # For async hooks, we need to handle differently
                        result = asyncio.run(callback(result, *args[1:], **kwargs))
                    else:
                        result = callback(result, *args[1:], **kwargs)
                except Exception as e:
                    logger.error(f"Error executing hook {hook_point.value}: {e}")
            return result

class PluginManager:
    """Comprehensive plugin management system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_states: Dict[str, PluginState] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.plugin_settings: Dict[str, Dict[str, Any]] = {}
        self.sandboxes: Dict[str, PluginSandbox] = {}
        self.plugin_dir = Path(__file__).parent / "plugins"
        self.installed_dir = Path(__file__).parent / "installed_plugins"
        self.settings_dir = Path(__file__).parent / "plugin_settings"

        # Create directories
        for dir_path in [self.plugin_dir, self.installed_dir, self.settings_dir]:
            dir_path.mkdir(exist_ok=True)

        # Initialize subsystems
        self.event_bus = PluginEventBus()
        self.hook_system = PluginHookSystem()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin-manager")

        # Plugin marketplace/repository
        self.marketplace_url = config.get("plugins", {}).get("marketplace_url", "https://api.ultra-pinnacle.ai/plugins")
        self.available_plugins: Dict[str, Dict[str, Any]] = {}

        logger.info("Plugin manager initialized")

    def discover_plugins(self) -> List[str]:
        """Discover available plugins"""
        plugins = []

        # Local plugins
        for plugin_file in self.plugin_dir.glob("*.py"):
            plugins.append(f"local:{plugin_file.stem}")

        # Installed plugins
        for plugin_dir in self.installed_dir.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                plugins.append(f"installed:{plugin_dir.name}")

        return plugins

    def load_plugin(self, plugin_id: str, enable_after_load: bool = True) -> bool:
        """Load a specific plugin"""
        try:
            self.plugin_states[plugin_id] = PluginState.LOADING

            # Parse plugin identifier
            if ":" in plugin_id:
                source, name = plugin_id.split(":", 1)
            else:
                source, name = "local", plugin_id

            # Load plugin module
            if source == "local":
                module_name = f"api_gateway.plugins.{name}"
                plugin_module = importlib.import_module(module_name)
                plugin_path = self.plugin_dir / f"{name}.py"
            elif source == "installed":
                module_name = f"installed_plugins.{name}"
                plugin_module = importlib.import_module(module_name)
                plugin_path = self.installed_dir / name / "__init__.py"
            else:
                raise ValueError(f"Unknown plugin source: {source}")

            # Find plugin class
            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr != PluginBase and
                    not any(issubclass(attr, cls) for cls in [APIPlugin, ProcessingPlugin, StoragePlugin, UIPlugin, AIModelPlugin, DataSourcePlugin, WorkflowPlugin])):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No plugin class found in {plugin_id}")
                self.plugin_states[plugin_id] = PluginState.ERROR
                return False

            # Load metadata
            metadata = self._load_plugin_metadata(plugin_path)
            if not metadata:
                logger.warning(f"No metadata found for plugin {plugin_id}, using defaults")
                metadata = PluginMetadata(
                    name=name,
                    version="1.0.0",
                    description=f"Plugin {name}",
                    author="Unknown",
                    checksum=self._calculate_checksum(plugin_path)
                )

            # Create plugin context
            context = PluginContext(
                plugin_id=plugin_id,
                permissions=self._parse_permissions(metadata.permissions),
                sandbox_level="standard"
            )

            # Create sandbox
            sandbox = PluginSandbox(context)
            self.sandboxes[plugin_id] = sandbox

            # Instantiate plugin
            plugin_instance = plugin_class()
            plugin_instance._metadata = metadata
            plugin_instance._context = context

            self.plugin_states[plugin_id] = PluginState.INITIALIZING

            # Initialize plugin
            if plugin_instance.initialize(self.config, context):
                self.plugins[plugin_id] = plugin_instance
                self.plugin_metadata[plugin_id] = metadata
                self.plugin_states[plugin_id] = PluginState.INITIALIZED

                # Load settings
                self._load_plugin_settings(plugin_id, plugin_instance)

                # Register hooks and event handlers
                self._register_plugin_hooks(plugin_instance)

                if enable_after_load and plugin_instance.enable():
                    logger.info(f"Plugin {plugin_id} loaded and enabled successfully")
                else:
                    logger.info(f"Plugin {plugin_id} loaded successfully (disabled)")
                return True
            else:
                logger.error(f"Plugin {plugin_id} failed to initialize")
                self.plugin_states[plugin_id] = PluginState.ERROR
                return False

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_id}: {e}")
            self.plugin_states[plugin_id] = PluginState.ERROR
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin"""
        try:
            if plugin_id not in self.plugins:
                return False

            plugin = self.plugins[plugin_id]
            self.plugin_states[plugin_id] = PluginState.UNLOADING

            # Disable first
            if plugin.state == PluginState.ENABLED:
                plugin.disable()

            # Shutdown
            plugin.shutdown()

            # Save settings
            self._save_plugin_settings(plugin_id, plugin)

            # Clean up
            if plugin_id in self.sandboxes:
                self.sandboxes[plugin_id].executor.shutdown(wait=True)
                del self.sandboxes[plugin_id]

            del self.plugins[plugin_id]
            del self.plugin_states[plugin_id]

            logger.info(f"Plugin {plugin_id} unloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].enable()
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].disable()
        return False

    def get_plugin_state(self, plugin_id: str) -> PluginState:
        """Get plugin state"""
        return self.plugin_states.get(plugin_id, PluginState.UNLOADED)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins"""
        result = []
        for plugin_id, plugin in self.plugins.items():
            result.append({
                "id": plugin_id,
                "name": plugin.name,
                "version": plugin.version,
                "state": plugin.state.value,
                "description": plugin.metadata.description if plugin.metadata else "",
                "author": plugin.metadata.author if plugin.metadata else "Unknown"
            })
        return result

    def execute_hook(self, hook_point: HookPoint, *args, **kwargs) -> Any:
        """Execute hooks for a specific point"""
        return self.hook_system.execute_hooks(hook_point, *args, **kwargs)

    def publish_event(self, event_type: str, data: Any) -> None:
        """Publish an event to all plugins"""
        self.event_bus.publish(event_type, data)

    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Get all API routes from plugins"""
        routes = []
        for plugin in self.plugins.values():
            if isinstance(plugin, APIPlugin) and plugin.state == PluginState.ENABLED:
                try:
                    plugin_routes = plugin.get_routes()
                    routes.extend(plugin_routes)
                except Exception as e:
                    logger.error(f"Error getting routes from plugin {plugin.name}: {e}")
        return routes

    def process_data(self, data: Any, data_type: str, **kwargs) -> Any:
        """Process data using available processing plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, ProcessingPlugin) and plugin.state == PluginState.ENABLED:
                try:
                    result = plugin.process_data(data, data_type, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"Error processing data with plugin {plugin.name}: {e}")
        return data

    def store_data(self, key: str, value: Any, **kwargs) -> bool:
        """Store data using available storage plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, StoragePlugin) and plugin.state == PluginState.ENABLED:
                try:
                    if plugin.store(key, value, **kwargs):
                        return True
                except Exception as e:
                    logger.error(f"Error storing data with plugin {plugin.name}: {e}")
        return False

    def retrieve_data(self, key: str, **kwargs) -> Any:
        """Retrieve data using available storage plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, StoragePlugin) and plugin.state == PluginState.ENABLED:
                try:
                    result = plugin.retrieve(key, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"Error retrieving data with plugin {plugin.name}: {e}")
        return None

    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get UI components from plugins"""
        components = []
        for plugin in self.plugins.values():
            if isinstance(plugin, UIPlugin) and plugin.state == PluginState.ENABLED:
                try:
                    plugin_components = plugin.get_ui_components()
                    components.extend(plugin_components)
                except Exception as e:
                    logger.error(f"Error getting UI components from plugin {plugin.name}: {e}")
        return components

    def get_ui_routes(self) -> List[Dict[str, Any]]:
        """Get UI routes from plugins"""
        routes = []
        for plugin in self.plugins.values():
            if isinstance(plugin, UIPlugin) and plugin.state == PluginState.ENABLED:
                try:
                    plugin_routes = plugin.get_ui_routes()
                    routes.extend(plugin_routes)
                except Exception as e:
                    logger.error(f"Error getting UI routes from plugin {plugin.name}: {e}")
        return routes

    def shutdown_all(self) -> None:
        """Shutdown all plugins"""
        for plugin_id in list(self.plugins.keys()):
            self.unload_plugin(plugin_id)

        self.executor.shutdown(wait=True)
        logger.info("All plugins shut down")

    def _load_plugin_metadata(self, plugin_path: Path) -> Optional[PluginMetadata]:
        """Load plugin metadata from plugin.json"""
        metadata_file = plugin_path.parent / "plugin.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                return PluginMetadata(**data)
            except Exception as e:
                logger.error(f"Error loading metadata for {plugin_path}: {e}")
        return None

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of plugin file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _parse_permissions(self, permissions: List[str]) -> Set[PluginPermission]:
        """Parse permission strings into Permission enum set"""
        result = set()
        for perm in permissions:
            try:
                result.add(PluginPermission(perm.lower()))
            except ValueError:
                logger.warning(f"Unknown permission: {perm}")
        return result if result else {PluginPermission.NONE}

    def _register_plugin_hooks(self, plugin: PluginBase) -> None:
        """Register plugin hooks and event handlers"""
        # Register hooks
        for hook_point, callbacks in plugin._hooks.items():
            for callback in callbacks:
                self.hook_system.register_hook(hook_point, callback)

        # Register event handlers
        for event_type, handlers in plugin._event_handlers.items():
            for handler in handlers:
                self.event_bus.subscribe(event_type, handler)

    def _load_plugin_settings(self, plugin_id: str, plugin: PluginBase) -> None:
        """Load plugin settings"""
        settings_file = self.settings_dir / f"{plugin_id}.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                plugin._settings.update(settings)
            except Exception as e:
                logger.error(f"Error loading settings for plugin {plugin_id}: {e}")

    def _save_plugin_settings(self, plugin_id: str, plugin: PluginBase) -> None:
        """Save plugin settings"""
        settings_file = self.settings_dir / f"{plugin_id}.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(plugin._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings for plugin {plugin_id}: {e}")

    # Plugin Marketplace and Repository Features

    def fetch_available_plugins(self) -> Dict[str, Any]:
        """Fetch available plugins from marketplace"""
        try:
            # In a real implementation, this would make HTTP requests
            # For now, return mock data
            self.available_plugins = {
                "ai-models": {
                    "name": "AI Models Extension",
                    "version": "1.0.0",
                    "description": "Additional AI model integrations",
                    "author": "Ultra Pinnacle",
                    "downloads": 1250,
                    "rating": 4.5,
                    "tags": ["ai", "models", "integration"]
                },
                "data-connectors": {
                    "name": "Data Connectors",
                    "version": "1.2.0",
                    "description": "Connect to external data sources",
                    "author": "Ultra Pinnacle",
                    "downloads": 890,
                    "rating": 4.2,
                    "tags": ["data", "connectors", "integration"]
                },
                "workflow-automation": {
                    "name": "Workflow Automation",
                    "version": "0.9.0",
                    "description": "Automate complex workflows",
                    "author": "Community",
                    "downloads": 567,
                    "rating": 4.0,
                    "tags": ["workflow", "automation", "productivity"]
                }
            }
            return self.available_plugins
        except Exception as e:
            logger.error(f"Error fetching available plugins: {e}")
            return {}

    def install_plugin(self, plugin_name: str, version: str = "latest") -> bool:
        """Install a plugin from marketplace"""
        try:
            if plugin_name not in self.available_plugins:
                logger.error(f"Plugin {plugin_name} not found in marketplace")
                return False

            # Create plugin directory
            plugin_dir = self.installed_dir / plugin_name
            plugin_dir.mkdir(exist_ok=True)

            # In a real implementation, download and extract plugin
            # For now, create a basic plugin structure
            self._create_mock_plugin(plugin_dir, plugin_name)

            logger.info(f"Plugin {plugin_name} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Error installing plugin {plugin_name}: {e}")
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Uninstall a plugin"""
        try:
            # First unload if loaded
            plugin_id = f"installed:{plugin_name}"
            if plugin_id in self.plugins:
                self.unload_plugin(plugin_id)

            # Remove plugin directory
            plugin_dir = self.installed_dir / plugin_name
            if plugin_dir.exists():
                import shutil
                shutil.rmtree(plugin_dir)

            # Remove settings
            settings_file = self.settings_dir / f"{plugin_id}.json"
            if settings_file.exists():
                settings_file.unlink()

            logger.info(f"Plugin {plugin_name} uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_name}: {e}")
            return False

    def update_plugin(self, plugin_name: str) -> bool:
        """Update a plugin to latest version"""
        try:
            # Check if update is available
            # In a real implementation, check version against marketplace
            current_version = self._get_installed_plugin_version(plugin_name)
            latest_version = self.available_plugins.get(plugin_name, {}).get("version", current_version)

            if current_version == latest_version:
                logger.info(f"Plugin {plugin_name} is already up to date")
                return True

            # Backup current plugin
            self._backup_plugin(plugin_name)

            # Uninstall old version
            if not self.uninstall_plugin(plugin_name):
                return False

            # Install new version
            if not self.install_plugin(plugin_name, latest_version):
                # Restore backup on failure
                self._restore_plugin_backup(plugin_name)
                return False

            logger.info(f"Plugin {plugin_name} updated to version {latest_version}")
            return True

        except Exception as e:
            logger.error(f"Error updating plugin {plugin_name}: {e}")
            return False

    def check_plugin_updates(self) -> Dict[str, Any]:
        """Check for available plugin updates"""
        updates = {}
        try:
            for plugin_id, metadata in self.plugin_metadata.items():
                if ":" in plugin_id:
                    source, name = plugin_id.split(":", 1)
                    if source == "installed" and name in self.available_plugins:
                        current_version = metadata.version
                        latest_version = self.available_plugins[name]["version"]
                        if current_version != latest_version:
                            updates[name] = {
                                "current_version": current_version,
                                "latest_version": latest_version,
                                "description": self.available_plugins[name]["description"]
                            }
        except Exception as e:
            logger.error(f"Error checking plugin updates: {e}")

        return updates

    def _create_mock_plugin(self, plugin_dir: Path, plugin_name: str) -> None:
        """Create a mock plugin for testing (replace with real download logic)"""
        # Create __init__.py
        init_content = f'''
from ..plugins import APIPlugin

class {plugin_name.replace("-", "").title()}Plugin(APIPlugin):
    """Mock plugin for {plugin_name}"""

    @property
    def name(self) -> str:
        return "{plugin_name}"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config, context):
        print(f"{plugin_name} plugin initialized")
        return True

    def shutdown(self):
        print(f"{plugin_name} plugin shut down")

    def get_routes(self):
        return [{{
            'path': '/api/{plugin_name}',
            'methods': ['GET'],
            'handler': self.handle_request,
            'summary': '{plugin_name} endpoint'
        }}]

    def handle_request(self):
        return {{"message": "Hello from {plugin_name} plugin"}}
'''
        (plugin_dir / "__init__.py").write_text(init_content)

        # Create plugin.json
        metadata = {
            "name": plugin_name,
            "version": "1.0.0",
            "description": f"Mock plugin for {plugin_name}",
            "author": "Ultra Pinnacle",
            "license": "MIT",
            "permissions": ["read"],
            "tags": ["mock", "test"]
        }
        with open(plugin_dir / "plugin.json", 'w') as f:
            json.dump(metadata, f, indent=2)

    def _get_installed_plugin_version(self, plugin_name: str) -> str:
        """Get version of installed plugin"""
        plugin_id = f"installed:{plugin_name}"
        if plugin_id in self.plugin_metadata:
            return self.plugin_metadata[plugin_id].version
        return "0.0.0"

    def _backup_plugin(self, plugin_name: str) -> None:
        """Backup plugin before update"""
        plugin_dir = self.installed_dir / plugin_name
        backup_dir = self.installed_dir / f"{plugin_name}.backup"
        if plugin_dir.exists():
            import shutil
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(plugin_dir, backup_dir)

    def _restore_plugin_backup(self, plugin_name: str) -> None:
        """Restore plugin from backup"""
        plugin_dir = self.installed_dir / plugin_name
        backup_dir = self.installed_dir / f"{plugin_name}.backup"
        if backup_dir.exists():
            import shutil
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            shutil.copytree(backup_dir, plugin_dir)
            shutil.rmtree(backup_dir)

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