"""
Configuration management for Ultra Pinnacle AI Studio
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class Config:
    """Configuration manager with environment variable support"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config = self._load_config()
        self._apply_env_overrides()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        current_dir = Path(__file__).parent
        return str(current_dir.parent / "config.json")

    def _get_config_path_based_on_env(self) -> str:
        """Get configuration file path based on environment"""
        current_dir = Path(__file__).parent
        base_dir = current_dir.parent

        # Check for explicit config file override
        config_file = os.environ.get('CONFIG_FILE')
        if config_file:
            return str(base_dir / config_file)

        # Check environment for production config
        environment = os.environ.get('ENVIRONMENT', os.environ.get('ENV', 'development'))
        if environment == 'production':
            prod_config = base_dir / "config.production.json"
            if prod_config.exists():
                return str(prod_config)

        # Default to development config
        return str(base_dir / "config.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # JWT Secret
        jwt_secret = os.environ.get('JWT_SECRET')
        if jwt_secret:
            self._config['security']['secret_key'] = jwt_secret
        elif self._config['security']['secret_key'] == '${JWT_SECRET}':
            # Generate a secure random secret for development
            import secrets
            self._config['security']['secret_key'] = secrets.token_urlsafe(32)
            print("WARNING: Using auto-generated JWT secret for development. Set JWT_SECRET environment variable in production.")
        
        # Database URL
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            self._config['database']['url'] = database_url
        
        # Log level
        log_level = os.environ.get('LOG_LEVEL')
        if log_level:
            self._config['app']['log_level'] = log_level
        
        # Environment
        env = os.environ.get('ENVIRONMENT', os.environ.get('ENV', 'development'))
        if env:
            self._config['app']['env'] = env
        
        # Host and port
        host = os.environ.get('HOST')
        if host:
            self._config['app']['host'] = host
        
        port = os.environ.get('PORT')
        if port:
            self._config['app']['port'] = int(port)
        
        # Debug mode
        debug = os.environ.get('DEBUG')
        if debug is not None:
            self._config['app']['debug'] = debug.lower() in ('true', '1', 'yes')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key using bracket notation"""
        return self.get(key)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in configuration"""
        return self.get(key) is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self._config.copy()
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_keys = [
            'app.name',
            'app.version',
            'security.secret_key',
            'security.algorithm',
            'database.url',
            'models.default_model'
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                raise ValueError(f"Required configuration key missing: {key}")
        
        # Validate secret key is not default in production
        if (self.get('app.env') == 'production' and 
            self.get('security.secret_key') == 'ultra-pinnacle-dev-secret-key-change-in-production'):
            raise ValueError("Default secret key detected in production environment")
        
        return True

# Global configuration instance
config = Config()
