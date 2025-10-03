"""
Tests for the Ultra Pinnacle AI Studio Plugin System
"""
import pytest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_gateway.plugins import (
    PluginManager, PluginBase, PluginState, PluginPermission,
    PluginMetadata, PluginContext, HookPoint,
    APIPlugin, ProcessingPlugin, StoragePlugin,
    UIPlugin, AIModelPlugin, DataSourcePlugin, WorkflowPlugin
)


class TestPlugin(PluginBase):
    """Test plugin implementation"""

    def __init__(self):
        super().__init__()
        self._name = "test_plugin"
        self._version = "1.0.0"
        self.initialized = False
        self.shutdown_called = False

    def initialize(self, config, context):
        super().initialize(config, context)
        self.initialized = True
        return True

    def shutdown(self):
        self.shutdown_called = True


class TestAPIPlugin(APIPlugin):
    """Test API plugin"""

    def __init__(self):
        super().__init__()
        self._name = "test_api_plugin"
        self._version = "1.0.0"

    def get_routes(self):
        return [
            {
                'path': '/api/test',
                'methods': ['GET'],
                'handler': self.test_handler,
                'summary': 'Test endpoint'
            }
        ]

    def test_handler(self):
        return {"message": "test response"}


class TestProcessingPlugin(ProcessingPlugin):
    """Test processing plugin"""

    def __init__(self):
        super().__init__()
        self._name = "test_processing_plugin"
        self._version = "1.0.0"

    def process_data(self, data, data_type, **kwargs):
        if data_type == "test":
            return f"processed_{data}"
        return data


class TestStoragePlugin(StoragePlugin):
    """Test storage plugin"""

    def __init__(self):
        super().__init__()
        self._name = "test_storage_plugin"
        self._version = "1.0.0"
        self.storage = {}

    def store(self, key, value, **kwargs):
        self.storage[key] = value
        return True

    def retrieve(self, key, **kwargs):
        return self.storage.get(key)


class TestAIModelPlugin(AIModelPlugin):
    """Test AI model plugin"""

    def __init__(self):
        super().__init__()
        self._name = "test_ai_plugin"
        self._version = "1.0.0"

    def get_supported_models(self):
        return [
            {
                "name": "test-model",
                "type": "text-generation",
                "description": "Test model",
                "max_tokens": 100
            }
        ]

    def load_model(self, model_name, **kwargs):
        if model_name == "test-model":
            return {"loaded": True}
        return None

    def generate(self, model_name, prompt, **kwargs):
        return f"Generated response for: {prompt}"


def test_plugin_base():
    """Test basic plugin functionality"""
    plugin = TestPlugin()

    assert plugin.name == "test_plugin"
    assert plugin.version == "1.0.0"
    assert plugin.state == PluginState.UNLOADED

    # Test initialization
    config = {}
    context = PluginContext(
        plugin_id="test_plugin",
        permissions={PluginPermission.READ}
    )

    assert plugin.initialize(config, context) == True
    assert plugin.initialized == True

    # Test enable/disable
    assert plugin.state == PluginState.INITIALIZED  # Should be initialized after initialize() call
    assert plugin.enable() == True
    assert plugin.state == PluginState.ENABLED

    assert plugin.disable() == True
    assert plugin.state == PluginState.DISABLED

    # Test shutdown
    plugin.shutdown()
    assert plugin.shutdown_called == True


def test_plugin_manager():
    """Test plugin manager functionality"""
    config = {"test": "config"}
    manager = PluginManager(config)

    assert len(manager.plugins) == 0

    # Test plugin listing
    plugins = manager.list_plugins()
    assert isinstance(plugins, list)

    # Test marketplace methods
    available = manager.fetch_available_plugins()
    assert isinstance(available, list)

    # Test plugin state checking
    state = manager.get_plugin_state("nonexistent")
    assert state == PluginState.UNLOADED


def test_api_plugin():
    """Test API plugin functionality"""
    plugin = TestAPIPlugin()

    routes = plugin.get_routes()
    assert len(routes) == 1
    assert routes[0]['path'] == '/api/test'

    # Test route handler
    handler = routes[0]['handler']
    response = handler()
    assert response == {"message": "test response"}


def test_processing_plugin():
    """Test processing plugin functionality"""
    plugin = TestProcessingPlugin()

    # Test data processing
    result = plugin.process_data("test_data", "test")
    assert result == "processed_test_data"

    # Test unhandled data type
    result = plugin.process_data("test_data", "unknown")
    assert result == "test_data"


def test_storage_plugin():
    """Test storage plugin functionality"""
    plugin = TestStoragePlugin()

    # Test storing data
    assert plugin.store("key1", "value1") == True

    # Test retrieving data
    assert plugin.retrieve("key1") == "value1"
    assert plugin.retrieve("nonexistent") is None


def test_ai_model_plugin():
    """Test AI model plugin functionality"""
    plugin = TestAIModelPlugin()

    models = plugin.get_supported_models()
    assert len(models) == 1
    assert models[0]['name'] == "test-model"

    # Test model loading
    model = plugin.load_model("test-model")
    assert model == {"loaded": True}

    # Test text generation
    response = plugin.generate("test-model", "Hello")
    assert "Generated response for: Hello" in response


def test_plugin_permissions():
    """Test plugin permission system"""
    from api_gateway.plugins.manager import PluginPermission

    # Test permission enum
    assert PluginPermission.READ.value == "read"
    assert PluginPermission.WRITE.value == "write"
    assert PluginPermission.EXECUTE.value == "execute"
    assert PluginPermission.ADMIN.value == "admin"


def test_plugin_metadata():
    """Test plugin metadata structure"""
    metadata = PluginMetadata(
        name="test_plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        license="MIT"
    )

    assert metadata.name == "test_plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test plugin"
    assert metadata.author == "Test Author"
    assert metadata.license == "MIT"


def test_plugin_context():
    """Test plugin execution context"""
    context = PluginContext(
        plugin_id="test_plugin",
        permissions={PluginPermission.READ, PluginPermission.WRITE},
        sandbox_level="standard",
        execution_timeout=30
    )

    assert context.plugin_id == "test_plugin"
    assert PluginPermission.READ in context.permissions
    assert PluginPermission.WRITE in context.permissions
    assert context.sandbox_level == "standard"
    assert context.execution_timeout == 30


def test_hook_system():
    """Test hook system functionality"""
    # Test hook point enum
    assert HookPoint.PRE_REQUEST.value == "pre_request"
    assert HookPoint.POST_REQUEST.value == "post_request"
    assert HookPoint.PRE_MODEL_LOAD.value == "pre_model_load"
    assert HookPoint.POST_MODEL_LOAD.value == "post_model_load"


if __name__ == "__main__":
    # Run basic tests
    print("Running plugin system tests...")

    try:
        test_plugin_base()
        print("✓ Plugin base tests passed")

        test_plugin_manager()
        print("✓ Plugin manager tests passed")

        test_api_plugin()
        print("✓ API plugin tests passed")

        test_processing_plugin()
        print("✓ Processing plugin tests passed")

        test_storage_plugin()
        print("✓ Storage plugin tests passed")

        test_ai_model_plugin()
        print("✓ AI model plugin tests passed")

        test_plugin_permissions()
        print("✓ Plugin permissions tests passed")

        test_plugin_metadata()
        print("✓ Plugin metadata tests passed")

        test_plugin_context()
        print("✓ Plugin context tests passed")

        test_hook_system()
        print("✓ Hook system tests passed")

        print("\n🎉 All plugin system tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)