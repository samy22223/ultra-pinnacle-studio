import logging
import logging.handlers
import json
from pathlib import Path

def setup_logging(config_path: str = None):
    """Setup logging configuration from config file"""

    # Load config
    if config_path is None:
        import os
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {"app": {"log_level": "INFO"}}
        print(f"Warning: Config file not found at {config_path}, using defaults")

    log_level = getattr(logging, config.get("app", {}).get("log_level", "INFO").upper())
    logs_dir = Path(config.get("paths", {}).get("logs_dir", "logs/"))
    logs_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("ultra_pinnacle")
    logger.setLevel(log_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "ultra_pinnacle.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

# Global logger instance
logger = setup_logging()