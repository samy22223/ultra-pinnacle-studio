"""
Plugin Marketplace for Ultra Pinnacle AI Studio
"""
import json
import hashlib
import requests
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import tempfile
import zipfile
import shutil

logger = logging.getLogger("ultra_pinnacle")

class PluginMarketplace:
    """Plugin marketplace for discovering, installing, and updating plugins"""

    def __init__(self, config):
        self.config = config
        self.marketplace_url = config.get("plugins", {}).get("marketplace_url", "https://api.ultra-pinnacle.ai/plugins")
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.installed_dir = Path(__file__).parent / "installed_plugins"
        self.installed_dir.mkdir(exist_ok=True)

        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self._marketplace_cache = None
        self._cache_timestamp = None

    def get_available_plugins(self) -> List[Dict[str, Any]]:
        """Get list of available plugins from marketplace"""
        try:
            # Check cache first
            if self._is_cache_valid():
                return self._marketplace_cache

            # Fetch from marketplace
            response = requests.get(f"{self.marketplace_url}/list", timeout=30)
            response.raise_for_status()

            plugins = response.json().get("plugins", [])

            # Cache the result
            self._marketplace_cache = plugins
            self._cache_timestamp = datetime.now()

            # Save to local cache
            self._save_cache(plugins)

            return plugins

        except requests.RequestException as e:
            logger.error(f"Error fetching plugins from marketplace: {e}")
            # Try to load from local cache
            return self._load_cache()
        except Exception as e:
            logger.error(f"Error getting available plugins: {e}")
            return []

    def search_plugins(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Search plugins by query and category"""
        try:
            params = {"q": query}
            if category:
                params["category"] = category

            response = requests.get(f"{self.marketplace_url}/search", params=params, timeout=30)
            response.raise_for_status()

            return response.json().get("plugins", [])

        except requests.RequestException as e:
            logger.error(f"Error searching plugins: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching plugins: {e}")
            return []

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific plugin"""
        try:
            response = requests.get(f"{self.marketplace_url}/plugin/{plugin_name}", timeout=30)
            response.raise_for_status()

            return response.json().get("plugin")

        except requests.RequestException as e:
            logger.error(f"Error getting plugin details for {plugin_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting plugin details for {plugin_name}: {e}")
            return None

    def install_plugin(self, plugin_name: str, version: str = "latest") -> bool:
        """Install a plugin from the marketplace"""
        try:
            logger.info(f"Installing plugin {plugin_name} version {version}")

            # Get plugin details
            plugin_details = self.get_plugin_details(plugin_name)
            if not plugin_details:
                logger.error(f"Plugin {plugin_name} not found in marketplace")
                return False

            # Determine version to install
            if version == "latest":
                version = plugin_details.get("latest_version", plugin_details.get("version"))

            # Download plugin
            download_url = plugin_details.get("download_url", "").format(version=version)
            if not download_url:
                logger.error(f"No download URL available for plugin {plugin_name}")
                return False

            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Download plugin archive
                response = requests.get(download_url, timeout=60)
                response.raise_for_status()

                # Save to temporary file
                archive_path = temp_path / f"{plugin_name}-{version}.zip"
                with open(archive_path, 'wb') as f:
                    f.write(response.content)

                # Verify checksum if provided
                expected_checksum = plugin_details.get("checksum")
                if expected_checksum:
                    actual_checksum = self._calculate_checksum(archive_path)
                    if actual_checksum != expected_checksum:
                        logger.error(f"Checksum verification failed for plugin {plugin_name}")
                        return False

                # Extract plugin
                plugin_dir = self.installed_dir / plugin_name
                plugin_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(plugin_dir)

                # Validate plugin structure
                if not self._validate_plugin_structure(plugin_dir):
                    logger.error(f"Invalid plugin structure for {plugin_name}")
                    shutil.rmtree(plugin_dir)
                    return False

                # Create plugin metadata
                metadata = {
                    "name": plugin_name,
                    "version": version,
                    "installed_at": datetime.now().isoformat(),
                    "source": "marketplace",
                    "marketplace_info": plugin_details
                }

                metadata_file = plugin_dir / "installed.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

                logger.info(f"Plugin {plugin_name} version {version} installed successfully")
                return True

        except Exception as e:
            logger.error(f"Error installing plugin {plugin_name}: {e}")
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Uninstall a plugin"""
        try:
            logger.info(f"Uninstalling plugin {plugin_name}")

            plugin_dir = self.installed_dir / plugin_name
            if not plugin_dir.exists():
                logger.warning(f"Plugin {plugin_name} not found")
                return False

            # Remove plugin directory
            shutil.rmtree(plugin_dir)

            logger.info(f"Plugin {plugin_name} uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_name}: {e}")
            return False

    def update_plugin(self, plugin_name: str) -> bool:
        """Update a plugin to the latest version"""
        try:
            logger.info(f"Updating plugin {plugin_name}")

            # Check current version
            plugin_dir = self.installed_dir / plugin_name
            if not plugin_dir.exists():
                logger.error(f"Plugin {plugin_name} not installed")
                return False

            metadata_file = plugin_dir / "installed.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                current_version = metadata.get("version")
            else:
                current_version = "0.0.0"

            # Get latest version info
            plugin_details = self.get_plugin_details(plugin_name)
            if not plugin_details:
                logger.error(f"Plugin {plugin_name} not found in marketplace")
                return False

            latest_version = plugin_details.get("latest_version", plugin_details.get("version"))

            if self._compare_versions(current_version, latest_version) >= 0:
                logger.info(f"Plugin {plugin_name} is already up to date (version {current_version})")
                return True

            # Uninstall current version
            if not self.uninstall_plugin(plugin_name):
                return False

            # Install new version
            return self.install_plugin(plugin_name, latest_version)

        except Exception as e:
            logger.error(f"Error updating plugin {plugin_name}: {e}")
            return False

    def check_updates(self) -> List[Dict[str, Any]]:
        """Check for available updates for installed plugins"""
        try:
            updates = []

            for plugin_dir in self.installed_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                plugin_name = plugin_dir.name
                metadata_file = plugin_dir / "installed.json"

                if not metadata_file.exists():
                    continue

                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    current_version = metadata.get("version")
                    marketplace_info = metadata.get("marketplace_info", {})

                    # Get latest version from marketplace
                    plugin_details = self.get_plugin_details(plugin_name)
                    if plugin_details:
                        latest_version = plugin_details.get("latest_version", plugin_details.get("version"))

                        if self._compare_versions(current_version, latest_version) < 0:
                            updates.append({
                                "name": plugin_name,
                                "current_version": current_version,
                                "latest_version": latest_version,
                                "description": plugin_details.get("description", ""),
                                "changelog": plugin_details.get("changelog", "")
                            })

                except Exception as e:
                    logger.error(f"Error checking updates for plugin {plugin_name}: {e}")

            return updates

        except Exception as e:
            logger.error(f"Error checking for plugin updates: {e}")
            return []

    def _is_cache_valid(self) -> bool:
        """Check if marketplace cache is still valid"""
        if self._cache_timestamp is None:
            return False

        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.cache_ttl

    def _save_cache(self, plugins: List[Dict[str, Any]]) -> None:
        """Save plugins list to local cache"""
        try:
            cache_file = self.cache_dir / "marketplace.json"
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "plugins": plugins
            }

            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving marketplace cache: {e}")

    def _load_cache(self) -> List[Dict[str, Any]]:
        """Load plugins list from local cache"""
        try:
            cache_file = self.cache_dir / "marketplace.json"
            if not cache_file.exists():
                return []

            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            self._marketplace_cache = cache_data.get("plugins", [])
            self._cache_timestamp = datetime.fromisoformat(cache_data.get("timestamp"))

            return self._marketplace_cache

        except Exception as e:
            logger.error(f"Error loading marketplace cache: {e}")
            return []

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _validate_plugin_structure(self, plugin_dir: Path) -> bool:
        """Validate that plugin has required structure"""
        try:
            # Check for required files
            required_files = ["__init__.py", "plugin.json"]
            for filename in required_files:
                if not (plugin_dir / filename).exists():
                    logger.error(f"Missing required file: {filename}")
                    return False

            # Validate plugin.json
            plugin_json = plugin_dir / "plugin.json"
            with open(plugin_json, 'r') as f:
                metadata = json.load(f)

            required_fields = ["name", "version", "description", "author"]
            for field in required_fields:
                if field not in metadata:
                    logger.error(f"Missing required field in plugin.json: {field}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating plugin structure: {e}")
            return False

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1

            return 0

        except Exception:
            # If version comparison fails, assume version2 is newer
            return -1