"""
Example API Plugin for Ultra Pinnacle AI Studio
"""
from ..plugins import APIPlugin
import logging

logger = logging.getLogger("ultra_pinnacle")

class ExampleAPIPlugin(APIPlugin):
    """Example API plugin demonstrating plugin capabilities"""

    @property
    def name(self) -> str:
        return "example_api"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config, context):
        """Initialize the plugin"""
        logger.info("Example API plugin initialized")
        return True

    def shutdown(self):
        """Shutdown the plugin"""
        logger.info("Example API plugin shut down")

    def get_routes(self):
        """Get FastAPI routes provided by this plugin"""
        return [
            {
                'path': '/api/plugins/example',
                'methods': ['GET'],
                'handler': self.example_handler,
                'summary': 'Example plugin endpoint'
            },
            {
                'path': '/api/plugins/example/data',
                'methods': ['POST'],
                'handler': self.process_data_handler,
                'summary': 'Process data via plugin'
            }
        ]

    def example_handler(self):
        """Example handler"""
        return {
            "message": "Hello from Example API Plugin!",
            "plugin": self.name,
            "version": self.version,
            "status": "active"
        }

    def process_data_handler(self, data: dict):
        """Process data handler"""
        # Use plugin manager's processing capability
        from ..main import plugin_manager
        processed = plugin_manager.process_data(data.get('content', ''), data.get('type', 'text'))
        return {
            "original": data,
            "processed": processed,
            "plugin": self.name
        }