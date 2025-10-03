"""
Plugin Manager for Ultra Pinnacle AI Studio
"""
from typing import Dict, Any, List, Optional, Callable, Set, Union
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
import threading
import asyncio
import json
import hashlib
import importlib
import logging
from concurrent.futures import ThreadPoolExecutor
import inspect

logger = logging.getLogger("ultra_pinnacle")

@dataclass
class PluginMetadata:
    """Plugin metadata structure"""
    name: str
    version: str
    description: str = ""
    author: str = ""
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
    permissions: Set['PluginPermission']
    sandbox_level: str = "standard"
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

class PluginBase:
    """Enhanced base class for all plugins"""

    def __init__(self):
        self._metadata = None
        self._context = None
        self._state = PluginState.UNLOADED
        self._hooks = {}
        self._settings = {}
        self._event_handlers = {}

    @property
    def name(self) -> str:
        """Plugin name"""
        return getattr(self, '_name', 'Unknown Plugin')

    @property
    def version(self) -> str:
        """Plugin version"""
        return getattr(self, '_version', '0.0.0')

    @property
    def metadata(self):
        """Plugin metadata"""
        return self._metadata

    @property
    def state(self):
        """Current plugin state"""
        return self._state

    @property
    def context(self):
        """Plugin execution context"""
        return self._context

    def initialize(self, config, context):
        """Initialize the plugin with enhanced context"""
        return True

    def shutdown(self):
        """Shutdown the plugin"""
        pass

    def enable(self):
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

    def disable(self):
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

    def register_hook(self, hook_point, callback):
        """Register a hook callback"""
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        self._hooks[hook_point].append(callback)

    def unregister_hook(self, hook_point, callback):
        """Unregister a hook callback"""
        if hook_point in self._hooks:
            self._hooks[hook_point] = [cb for cb in self._hooks[hook_point] if cb != callback]

    def register_event_handler(self, event_type, callback):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(callback)

    def unregister_event_handler(self, event_type, callback):
        """Unregister an event handler"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [cb for cb in self._event_handlers[event_type] if cb != callback]

    def emit_event(self, event_type, data):
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

    def get_setting(self, key, default=None):
        """Get a plugin setting"""
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        """Set a plugin setting"""
        self._settings[key] = value

    def save_settings(self):
        """Save plugin settings (to be implemented by manager)"""
        pass

    def load_settings(self):
        """Load plugin settings (to be implemented by manager)"""
        pass

    # Lifecycle hooks for subclasses
    def on_enable(self):
        """Called when plugin is enabled"""
        pass

    def on_disable(self):
        """Called when plugin is disabled"""
        pass

    def on_settings_changed(self, settings):
        """Called when plugin settings are changed"""
        pass

class APIPlugin(PluginBase):
    """Plugin that adds API endpoints"""

    def get_routes(self):
        """Get FastAPI routes provided by this plugin"""
        return []

class ProcessingPlugin(PluginBase):
    """Plugin that provides data processing capabilities"""

    def process_data(self, data, data_type, **kwargs):
        """Process data of specified type"""
        return data

class StoragePlugin(PluginBase):
    """Plugin that provides storage backends"""

    def store(self, key, value, **kwargs):
        """Store value with key"""
        return False

    def retrieve(self, key, **kwargs):
        """Retrieve value by key"""
        return None

    def delete(self, key):
        """Delete value by key"""
        return False

    def list_keys(self, prefix=""):
        """List all keys with optional prefix"""
        return []

class UIPlugin(PluginBase):
    """Plugin that provides UI components"""

    def get_ui_components(self):
        """Get UI components provided by this plugin"""
        return []

    def get_ui_routes(self):
        """Get UI routes provided by this plugin"""
        return []

class AIModelPlugin(PluginBase):
    """Plugin that provides AI model integrations"""

    def get_supported_models(self):
        """Get list of supported AI models"""
        return []

    def load_model(self, model_name, **kwargs):
        """Load an AI model"""
        return None

    def generate(self, model_name, prompt, **kwargs):
        """Generate text using a model"""
        return ""

class DataSourcePlugin(PluginBase):
    """Plugin that provides external data source integrations"""

    def get_data_sources(self):
        """Get available data sources"""
        return []

    def connect(self, source_id, config):
        """Connect to a data source"""
        return False

    def query(self, source_id, query, **kwargs):
        """Query a data source"""
        return None

    def disconnect(self, source_id):
        """Disconnect from a data source"""
        return False

class WorkflowPlugin(PluginBase):
    """Plugin that provides custom workflow automation"""

    def get_workflows(self):
        """Get available workflows"""
        return []

    def execute_workflow(self, workflow_id, inputs):
        """Execute a workflow"""
        return {}

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

class PluginSandbox:
    """Enhanced plugin execution sandbox with security controls"""

    def __init__(self, context):
        self.context = context
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"plugin-{context.plugin_id}")
        self._lock = threading.Lock()
        self._resource_monitor = ResourceMonitor(context.memory_limit, context.cpu_limit)

        # Security: Track dangerous imports and operations
        self._dangerous_modules = {
            'os', 'subprocess', 'sys', 'builtins', 'importlib', 'inspect',
            'pickle', 'marshal', 'shelve', 'dbm', 'sqlite3', 'socket',
            'http', 'urllib', 'ftplib', 'poplib', 'imaplib', 'smtplib'
        }

        self._dangerous_functions = {
            'exec', 'eval', 'compile', 'open', 'file', 'input', '__import__',
            'reload', 'dir', 'vars', 'locals', 'globals', 'getattr', 'setattr',
            'delattr', 'hasattr', 'callable', 'isinstance', 'issubclass'
        }

    def execute(self, func, *args, **kwargs):
        """Execute a function in the sandbox with security controls"""
        with self._lock:
            try:
                # Pre-execution security checks
                if not self._check_permissions(func):
                    raise PermissionError(f"Function {func.__name__} not allowed in current permission level")

                if not self._check_function_safety(func):
                    raise SecurityError(f"Function {func.__name__} contains unsafe operations")

                # Resource monitoring
                if not self._resource_monitor.check_limits():
                    raise ResourceError("Resource limits exceeded")

                # Execute with timeout and monitoring
                future = self.executor.submit(self._monitored_execution, func, args, kwargs)
                return future.result(timeout=self.context.execution_timeout)

            except Exception as e:
                logger.error(f"Sandbox execution error for plugin {self.context.plugin_id}: {e}")
                raise

    def _monitored_execution(self, func, args, kwargs):
        """Execute function with resource monitoring"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log resource usage
            logger.debug(f"Plugin {self.context.plugin_id} function {func.__name__} "
                        f"executed in {execution_time:.2f}s")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"Plugin {self.context.plugin_id} function {func.__name__} "
                          f"failed after {execution_time:.2f}s: {e}")
            raise

    def _check_permissions(self, func):
        """Enhanced permission checking"""
        func_name = func.__name__

        # Admin has all permissions
        if PluginPermission.ADMIN in self.context.permissions:
            return True

        # Check specific permissions
        if PluginPermission.EXECUTE in self.context.permissions:
            # Allow execution but block dangerous operations
            if func_name in self._dangerous_functions:
                return False
            # Check if function tries to access dangerous modules
            if hasattr(func, '__module__') and func.__module__:
                if any(module in func.__module__ for module in self._dangerous_modules):
                    return False
            return True

        elif PluginPermission.WRITE in self.context.permissions:
            # Allow read/write but no execution
            if func_name in ['exec', 'eval', 'compile', '__import__']:
                return False
            return True

        elif PluginPermission.READ in self.context.permissions:
            # Read-only operations
            read_only_funcs = ['get', 'read', 'list', 'find', 'search', 'count']
            return any(rof in func_name for rof in read_only_funcs)

        return False

    def _check_function_safety(self, func):
        """Check function for potentially unsafe operations"""
        try:
            # Get function source if possible
            source = inspect.getsource(func)

            # Check for dangerous patterns
            dangerous_patterns = [
                'import os', 'import subprocess', 'import sys',
                'exec(', 'eval(', 'compile(', 'open(',
                '__import__(', 'getattr(', 'setattr('
            ]

            for pattern in dangerous_patterns:
                if pattern in source:
                    logger.warning(f"Dangerous pattern '{pattern}' found in function {func.__name__}")
                    return False

        except (OSError, TypeError):
            # Can't get source, assume safe for now
            pass

        return True

class ResourceMonitor:
    """Monitor resource usage for plugins"""

    def __init__(self, memory_limit_mb, cpu_limit_cores):
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        self.cpu_limit = cpu_limit_cores
        self.start_time = time.time()

    def check_limits(self):
        """Check if resource limits are exceeded"""
        try:
            import psutil
            process = psutil.Process()

            # Check memory usage
            memory_usage = process.memory_info().rss
            if memory_usage > self.memory_limit:
                logger.warning(f"Memory limit exceeded: {memory_usage} > {self.memory_limit}")
                return False

            # Check CPU usage (rough estimate)
            cpu_percent = process.cpu_percent(interval=0.1)
            if cpu_percent > (self.cpu_limit * 100):
                logger.warning(f"CPU limit exceeded: {cpu_percent}% > {self.cpu_limit * 100}%")
                return False

            return True

        except ImportError:
            # psutil not available, skip resource monitoring
            return True
        except Exception as e:
            logger.error(f"Error checking resource limits: {e}")
            return True

class SecurityError(Exception):
    """Security violation exception"""
    pass

class ResourceError(Exception):
    """Resource limit exceeded exception"""
    pass

class PluginEventBus:
    """Event-driven communication system for plugins"""

    def __init__(self):
        self._listeners = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type, callback):
        """Subscribe to an event"""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        """Unsubscribe from an event"""
        with self._lock:
            if event_type in self._listeners:
                self._listeners[event_type] = [cb for cb in self._listeners[event_type] if cb != callback]

    def publish(self, event_type, data):
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

# Plugin Classes (must be defined before PluginManager)

class PluginBase:
    """Enhanced base class for all plugins"""

    def __init__(self):
        self._metadata = None
        self._context = None
        self._state = PluginState.UNLOADED
        self._hooks = {}
        self._settings = {}
        self._event_handlers = {}

    @property
    def name(self) -> str:
        """Plugin name"""
        return getattr(self, '_name', 'Unknown Plugin')

    @property
    def version(self) -> str:
        """Plugin version"""
        return getattr(self, '_version', '0.0.0')

    @property
    def metadata(self):
        """Plugin metadata"""
        return self._metadata

    @property
    def state(self):
        """Current plugin state"""
        return self._state

    @property
    def context(self):
        """Plugin execution context"""
        return self._context

    def initialize(self, config, context):
        """Initialize the plugin with enhanced context"""
        self._context = context
        self._state = PluginState.INITIALIZED
        return True

    def shutdown(self):
        """Shutdown the plugin"""
        pass

    def enable(self):
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

    def disable(self):
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

    def register_hook(self, hook_point, callback):
        """Register a hook callback"""
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        self._hooks[hook_point].append(callback)

    def unregister_hook(self, hook_point, callback):
        """Unregister a hook callback"""
        if hook_point in self._hooks:
            self._hooks[hook_point] = [cb for cb in self._hooks[hook_point] if cb != callback]

    def register_event_handler(self, event_type, callback):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(callback)

    def unregister_event_handler(self, event_type, callback):
        """Unregister an event handler"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [cb for cb in self._event_handlers[event_type] if cb != callback]

    def emit_event(self, event_type, data):
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

    def get_setting(self, key, default=None):
        """Get a plugin setting"""
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        """Set a plugin setting"""
        self._settings[key] = value

    def save_settings(self):
        """Save plugin settings (to be implemented by manager)"""
        pass

    def load_settings(self):
        """Load plugin settings (to be implemented by manager)"""
        pass

    # Lifecycle hooks for subclasses
    def on_enable(self):
        """Called when plugin is enabled"""
        pass

    def on_disable(self):
        """Called when plugin is disabled"""
        pass

    def on_settings_changed(self, settings):
        """Called when plugin settings are changed"""
        pass

class APIPlugin(PluginBase):
    """Plugin that adds API endpoints"""

    def get_routes(self):
        """Get FastAPI routes provided by this plugin"""
        return []

class ProcessingPlugin(PluginBase):
    """Plugin that provides data processing capabilities"""

    def process_data(self, data, data_type, **kwargs):
        """Process data of specified type"""
        return data

class StoragePlugin(PluginBase):
    """Plugin that provides storage backends"""

    def store(self, key, value, **kwargs):
        """Store value with key"""
        return False

    def retrieve(self, key, **kwargs):
        """Retrieve value by key"""
        return None

    def delete(self, key):
        """Delete value by key"""
        return False

    def list_keys(self, prefix=""):
        """List all keys with optional prefix"""
        return []

class UIPlugin(PluginBase):
    """Plugin that provides UI components"""

    def get_ui_components(self):
        """Get UI components provided by this plugin"""
        return []

    def get_ui_routes(self):
        """Get UI routes provided by this plugin"""
        return []

class AIModelPlugin(PluginBase):
    """Plugin that provides AI model integrations"""

    def get_supported_models(self):
        """Get list of supported AI models"""
        return []

    def load_model(self, model_name, **kwargs):
        """Load an AI model"""
        return None

    def generate(self, model_name, prompt, **kwargs):
        """Generate text using a model"""
        return ""

class DataSourcePlugin(PluginBase):
    """Plugin that provides external data source integrations"""

    def get_data_sources(self):
        """Get available data sources"""
        return []

    def connect(self, source_id, config):
        """Connect to a data source"""
        return False

    def query(self, source_id, query, **kwargs):
        """Query a data source"""
        return None

    def disconnect(self, source_id):
        """Disconnect from a data source"""
        return False

class WorkflowPlugin(PluginBase):
    """Plugin that provides custom workflow automation"""

    def get_workflows(self):
        """Get available workflows"""
        return []

    def execute_workflow(self, workflow_id, inputs):
        """Execute a workflow"""
        return {}

class PluginManager:
    """Manages plugin loading and lifecycle"""

    def __init__(self, config):
        self.config = config
        self.plugins = {}
        self.plugin_states = {}
        self.plugin_metadata = {}
        self.sandboxes = {}
        self.available_plugins = {}

        # Initialize directories
        self.plugin_dir = Path(__file__).parent / "installed"
        self.plugin_dir.mkdir(exist_ok=True)
        self.settings_dir = Path(__file__).parent / "settings"
        self.settings_dir.mkdir(exist_ok=True)

        # Initialize components
        self.event_bus = PluginEventBus()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin-manager")

        # Initialize marketplace
        from .marketplace import PluginMarketplace
        self.marketplace = PluginMarketplace(config)

        logger.info("Plugin manager initialized")

    def discover_plugins(self):
        """Discover available plugins"""
        discovered = []

        # Discover local plugins
        for plugin_file in self.plugin_dir.glob("*.py"):
            plugin_id = f"local:{plugin_file.stem}"
            discovered.append(plugin_id)

        # Discover installed plugins
        installed_dir = Path(__file__).parent / "installed_plugins"
        if installed_dir.exists():
            for plugin_dir in installed_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_id = f"installed:{plugin_dir.name}"
                    discovered.append(plugin_id)

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def load_plugin(self, plugin_id, enable_after_load=True):
        """Load a specific plugin"""
        try:
            self.plugin_states[plugin_id] = PluginState.LOADING

            # Parse plugin source and name
            if ":" in plugin_id:
                source, name = plugin_id.split(":", 1)
            else:
                source = "local"
                name = plugin_id

            # Import plugin module
            if source == "local":
                module_name = f"api_gateway.plugins.{name}"
            elif source == "installed":
                module_name = f"api_gateway.plugins.installed_plugins.{name}.{name}"
            else:
                raise ValueError(f"Unknown plugin source: {source}")

            plugin_module = importlib.import_module(module_name)

            # Find plugin class
            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, 'name') and hasattr(attr, 'version') and
                    hasattr(attr, 'initialize')):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No plugin class found in {plugin_id}")
                self.plugin_states[plugin_id] = PluginState.ERROR
                return False

            # Create plugin context
            context = self._create_plugin_context(plugin_id)

            # Instantiate plugin
            plugin_instance = plugin_class()

            # Load metadata
            metadata = self._load_plugin_metadata(plugin_instance)
            plugin_instance._metadata = metadata

            # Initialize plugin
            self.plugin_states[plugin_id] = PluginState.INITIALIZING
            if plugin_instance.initialize(self.config, context):
                self.plugins[plugin_id] = plugin_instance
                self.plugin_states[plugin_id] = PluginState.INITIALIZED

                # Create sandbox
                self.sandboxes[plugin_id] = PluginSandbox(context)

                # Load settings
                self._load_plugin_settings(plugin_id, plugin_instance)

                # Register plugin hooks and events
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

    def unload_plugin(self, plugin_id):
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

    def enable_plugin(self, plugin_id):
        """Enable a plugin"""
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].enable()
        return False

    def disable_plugin(self, plugin_id):
        """Disable a plugin"""
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].disable()
        return False

    def get_plugin_state(self, plugin_id):
        """Get plugin state"""
        return self.plugin_states.get(plugin_id, PluginState.UNLOADED)

    def list_plugins(self):
        """List all loaded plugins"""
        result = []
        for plugin_id, plugin in self.plugins.items():
            result.append({
                "id": plugin_id,
                "name": plugin.name,
                "version": plugin.version,
                "state": plugin.state.value,
                "description": plugin.metadata.description if plugin.metadata else "",
                "author": plugin.metadata.author if plugin.metadata else ""
            })
        return result

    def shutdown_all(self):
        """Shutdown all plugins"""
        for plugin_id in list(self.plugins.keys()):
            self.unload_plugin(plugin_id)

        self.executor.shutdown(wait=True)
        logger.info("All plugins shut down")

    def _create_plugin_context(self, plugin_id):
        """Create execution context for plugin"""
        return PluginContext(
            plugin_id=plugin_id,
            permissions={PluginPermission.READ, PluginPermission.WRITE},  # Default permissions
            sandbox_level="standard",
            execution_timeout=30
        )

    def _load_plugin_metadata(self, plugin):
        """Load plugin metadata"""
        from plugins import PluginMetadata
        return PluginMetadata(
            name=plugin.name,
            version=plugin.version,
            description=getattr(plugin, 'description', ''),
            author=getattr(plugin, 'author', 'Unknown'),
            license=getattr(plugin, 'license', ''),
            permissions=getattr(plugin, 'permissions', ['read'])
        )

    def _register_plugin_hooks(self, plugin):
        """Register plugin hooks and event handlers"""
        # Register hooks
        for hook_point, callbacks in plugin._hooks.items():
            for callback in callbacks:
                self.hook_system.register_hook(hook_point, callback)

        # Register event handlers
        for event_type, handlers in plugin._event_handlers.items():
            for handler in handlers:
                self.event_bus.subscribe(event_type, handler)

    def _load_plugin_settings(self, plugin_id, plugin):
        """Load plugin settings"""
        settings_file = self.settings_dir / f"{plugin_id}.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                plugin._settings.update(settings)
            except Exception as e:
                logger.error(f"Error loading settings for plugin {plugin_id}: {e}")

    def _save_plugin_settings(self, plugin_id, plugin):
        """Save plugin settings"""
        settings_file = self.settings_dir / f"{plugin_id}.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(plugin._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings for plugin {plugin_id}: {e}")

    def get_api_routes(self):
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

    def process_data(self, data, data_type, **kwargs):
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

    def store_data(self, key, value, **kwargs):
        """Store data using available storage plugins"""
        for plugin in self.plugins.values():
            if isinstance(plugin, StoragePlugin) and plugin.state == PluginState.ENABLED:
                try:
                    if plugin.store(key, value, **kwargs):
                        return True
                except Exception as e:
                    logger.error(f"Error storing data with plugin {plugin.name}: {e}")
        return False

    def retrieve_data(self, key, **kwargs):
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

    def get_ui_components(self):
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

    def get_ui_routes(self):
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

    def fetch_available_plugins(self):
        """Fetch available plugins from marketplace"""
        return self.marketplace.get_available_plugins()

    def install_plugin(self, plugin_name, version="latest"):
        """Install plugin from marketplace"""
        return self.marketplace.install_plugin(plugin_name, version)

    def uninstall_plugin(self, plugin_name):
        """Uninstall plugin"""
        return self.marketplace.uninstall_plugin(plugin_name)

    def update_plugin(self, plugin_name):
        """Update plugin"""
        return self.marketplace.update_plugin(plugin_name)

    def check_plugin_updates(self):
        """Check for plugin updates"""
        return self.marketplace.check_updates()

    # Placeholder for hook system - will be implemented
    class HookSystem:
        def register_hook(self, hook_point, callback):
            pass

    hook_system = HookSystem()