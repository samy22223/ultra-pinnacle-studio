"""
Example Processing Plugin for Ultra Pinnacle AI Studio
"""
from ..plugins import ProcessingPlugin
import logging
import re

logger = logging.getLogger("ultra_pinnacle")

class ExampleProcessingPlugin(ProcessingPlugin):
    """Example processing plugin demonstrating data processing capabilities"""

    @property
    def name(self) -> str:
        return "example_processing"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config, context):
        """Initialize the plugin"""
        logger.info("Example processing plugin initialized")
        return True

    def shutdown(self):
        """Shutdown the plugin"""
        logger.info("Example processing plugin shut down")

    def process_data(self, data, data_type: str, **kwargs):
        """Process data of specified type"""
        if data_type == "text" and isinstance(data, str):
            # Simple text processing: add prefix and clean up
            processed = f"[PROCESSED] {data.strip()}"
            # Remove extra whitespace
            processed = re.sub(r'\s+', ' ', processed)
            return processed

        elif data_type == "json" and isinstance(data, dict):
            # Add processing metadata to JSON
            processed_data = data.copy()
            processed_data["_processed_by"] = self.name
            processed_data["_processed_at"] = "2024-01-01T00:00:00Z"  # Would use datetime
            return processed_data

        elif data_type == "list" and isinstance(data, list):
            # Process list items
            return [f"item_{i}: {item}" for i, item in enumerate(data)]

        # Return None if we can't process this type
        return None