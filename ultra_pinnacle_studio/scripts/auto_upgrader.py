#!/usr/bin/env python3
"""
Auto-Upgrade Service for Ultra Pinnacle Studio
Handles automatic version checking, seamless updates, and rollback capabilities
"""

import os
import sys
import json
import time
import requests
import subprocess
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import threading

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api_gateway.config import config
from api_gateway.logging_config import logger

class AutoUpgrader:
    """Auto-upgrade service with version management and rollback capabilities"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = config
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backups" / "upgrades"
        self.logs_dir = self.project_root / "logs"
        self.upgrade_history = []
        self.is_upgrading = False

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger("auto_upgrader")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.logs_dir / "auto_upgrader.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

        # Load upgrade configuration
        self.upgrade_config = self._load_upgrade_config()

    def _load_upgrade_config(self) -> Dict[str, Any]:
        """Load upgrade configuration"""
        return {
            "repositories": {
                "main": {
                    "url": "https://api.github.com/repos/ultra-pinnacle/ultra-pinnacle-studio/releases/latest",
                    "type": "github",
                    "check_interval": 3600,  # Check every hour
                    "auto_update": True
                },
                "web_ui": {
                    "url": "https://registry.npmjs.org/@ultra-pinnacle/studio-ui/latest",
                    "type": "npm",
                    "check_interval": 7200,  # Check every 2 hours
                    "auto_update": True
                }
            },
            "backup_before_upgrade": True,
            "max_backups": 5,
            "rollback_timeout": 300,  # 5 minutes to detect issues after upgrade
            "health_check_after_upgrade": True
        }

    def start_auto_upgrade_monitoring(self):
        """Start automatic upgrade monitoring"""
        self.logger.info("Starting Auto-Upgrade Monitoring Service")

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_upgrades, daemon=True)
        monitor_thread.start()

        self.logger.info("Auto-Upgrade Monitoring Service started")

    def _monitor_upgrades(self):
        """Monitor for available upgrades"""
        last_checks = {}

        while True:
            try:
                current_time = datetime.now()

                for repo_name, repo_config in self.upgrade_config["repositories"].items():
                    last_check = last_checks.get(repo_name, datetime.min)
                    check_interval = timedelta(seconds=repo_config["check_interval"])

                    if current_time - last_check >= check_interval:
                        self._check_for_updates(repo_name, repo_config)
                        last_checks[repo_name] = current_time

                time.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in upgrade monitoring: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def _check_for_updates(self, repo_name: str, repo_config: Dict[str, Any]):
        """Check for updates for a specific repository"""
        try:
            self.logger.info(f"Checking for updates: {repo_name}")

            if repo_config["type"] == "github":
                latest_version, download_url = self._check_github_updates(repo_config["url"])
            elif repo_config["type"] == "npm":
                latest_version, download_url = self._check_npm_updates(repo_config["url"])
            else:
                self.logger.warning(f"Unknown repository type: {repo_config['type']}")
                return

            current_version = self._get_current_version(repo_name)

            if self._is_newer_version(latest_version, current_version):
                self.logger.info(f"New version available for {repo_name}: {latest_version} (current: {current_version})")

                if repo_config.get("auto_update", False):
                    self.perform_upgrade(repo_name, latest_version, download_url)
                else:
                    self.logger.info(f"Auto-update disabled for {repo_name}, manual intervention required")
            else:
                self.logger.debug(f"{repo_name} is up to date (version {current_version})")

        except Exception as e:
            self.logger.error(f"Error checking updates for {repo_name}: {e}")

    def _check_github_updates(self, url: str) -> Tuple[str, str]:
        """Check GitHub releases for updates"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        release_data = response.json()
        latest_version = release_data["tag_name"].lstrip('v')
        download_url = None

        # Find the appropriate asset (assuming it's a tar.gz or zip)
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(('.tar.gz', '.zip')):
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            # Fallback to source code download
            download_url = release_data["zipball_url"]

        return latest_version, download_url

    def _check_npm_updates(self, url: str) -> Tuple[str, str]:
        """Check NPM package for updates"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        package_data = response.json()
        latest_version = package_data["version"]
        download_url = package_data.get("dist", {}).get("tarball", "")

        return latest_version, download_url

    def _get_current_version(self, component: str) -> str:
        """Get current version of a component"""
        try:
            if component == "main":
                # Read from config.json
                with open(self.project_root / "config.json", 'r') as f:
                    config_data = json.load(f)
                return config_data.get("app", {}).get("version", "0.0.0")
            elif component == "web_ui":
                # Read from package.json
                with open(self.project_root / "web_ui" / "package.json", 'r') as f:
                    package_data = json.load(f)
                return package_data.get("version", "0.0.0")
            else:
                return "0.0.0"
        except Exception as e:
            self.logger.error(f"Error getting current version for {component}: {e}")
            return "0.0.0"

    def _is_newer_version(self, new_version: str, current_version: str) -> bool:
        """Compare version strings"""
        try:
            def parse_version(v):
                return [int(x) for x in v.split('.')]

            new_parts = parse_version(new_version)
            current_parts = parse_version(current_version)

            return new_parts > current_parts
        except:
            # Fallback to string comparison
            return new_version != current_version

    def perform_upgrade(self, component: str, new_version: str, download_url: str) -> bool:
        """Perform an upgrade with backup and rollback capabilities"""
        if self.is_upgrading:
            self.logger.warning("Upgrade already in progress, skipping")
            return False

        self.is_upgrading = True
        upgrade_id = f"{component}_{new_version}_{int(time.time())}"

        try:
            self.logger.info(f"Starting upgrade: {component} to {new_version}")

            # Create backup
            if self.upgrade_config["backup_before_upgrade"]:
                backup_path = self._create_backup(component, upgrade_id)
                if not backup_path:
                    self.logger.error("Failed to create backup, aborting upgrade")
                    return False

            # Download and install update
            success = self._download_and_install(component, new_version, download_url)

            if success:
                # Wait for health check period
                if self.upgrade_config["health_check_after_upgrade"]:
                    self.logger.info("Waiting for health check period...")
                    time.sleep(self.upgrade_config["rollback_timeout"])

                    if not self._verify_upgrade_health(component):
                        self.logger.error("Health check failed, initiating rollback")
                        return self._rollback_upgrade(component, backup_path, upgrade_id)

                # Record successful upgrade
                self._record_upgrade_success(component, new_version, upgrade_id)
                self.logger.info(f"Upgrade completed successfully: {component} to {new_version}")
                return True
            else:
                self.logger.error("Upgrade installation failed")
                return False

        except Exception as e:
            self.logger.error(f"Upgrade failed with error: {e}")
            # Attempt rollback on failure
            try:
                backup_path = self.backup_dir / f"{upgrade_id}.backup"
                if backup_path.exists():
                    self._rollback_upgrade(component, backup_path, upgrade_id)
            except Exception as rollback_error:
                self.logger.error(f"Rollback also failed: {rollback_error}")
            return False
        finally:
            self.is_upgrading = False

    def _create_backup(self, component: str, upgrade_id: str) -> Optional[Path]:
        """Create backup before upgrade"""
        try:
            backup_path = self.backup_dir / f"{upgrade_id}.backup"
            backup_path.mkdir(exist_ok=True)

            if component == "main":
                # Backup main application files
                source_dirs = ["api_gateway", "scripts", "config.json", "requirements.txt"]
                for item in source_dirs:
                    source_path = self.project_root / item
                    if source_path.exists():
                        dest_path = backup_path / item
                        if source_path.is_file():
                            shutil.copy2(source_path, dest_path)
                        else:
                            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

            elif component == "web_ui":
                # Backup web UI files
                source_path = self.project_root / "web_ui"
                dest_path = backup_path / "web_ui"
                if source_path.exists():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

            # Clean up old backups
            self._cleanup_old_backups()

            self.logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _download_and_install(self, component: str, new_version: str, download_url: str) -> bool:
        """Download and install the update"""
        try:
            self.logger.info(f"Downloading update from: {download_url}")

            # Download file
            response = requests.get(download_url, timeout=300)
            response.raise_for_status()

            # Save to temporary location
            temp_file = self.project_root / f"temp_upgrade_{component}"
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            # Verify download integrity
            if not self._verify_download(temp_file, response.headers.get('content-length')):
                self.logger.error("Download verification failed")
                temp_file.unlink()
                return False

            # Extract and install
            if download_url.endswith('.tar.gz'):
                self._extract_tarball(temp_file, component)
            elif download_url.endswith('.zip'):
                self._extract_zip(temp_file, component)
            else:
                self.logger.error(f"Unsupported archive format: {download_url}")
                temp_file.unlink()
                return False

            # Update version
            self._update_version(component, new_version)

            # Cleanup
            temp_file.unlink()

            self.logger.info(f"Update installed successfully: {component} {new_version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to download/install update: {e}")
            return False

    def _extract_tarball(self, archive_path: Path, component: str):
        """Extract tar.gz archive"""
        import tarfile

        extract_dir = self.project_root / f"temp_extract_{component}"
        extract_dir.mkdir(exist_ok=True)

        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(extract_dir)

        # Move files to correct location
        self._move_extracted_files(extract_dir, component)

        shutil.rmtree(extract_dir)

    def _extract_zip(self, archive_path: Path, component: str):
        """Extract zip archive"""
        import zipfile

        extract_dir = self.project_root / f"temp_extract_{component}"
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Move files to correct location
        self._move_extracted_files(extract_dir, component)

        shutil.rmtree(extract_dir)

    def _move_extracted_files(self, extract_dir: Path, component: str):
        """Move extracted files to correct locations"""
        if component == "main":
            # Move main application files
            for item in extract_dir.iterdir():
                if item.is_dir():
                    dest_path = self.project_root / item.name
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.move(str(item), str(dest_path))
                elif item.is_file():
                    dest_path = self.project_root / item.name
                    shutil.move(str(item), str(dest_path))

        elif component == "web_ui":
            # Move web UI files
            web_ui_dir = self.project_root / "web_ui"
            for item in extract_dir.iterdir():
                if item.name == "web_ui" or item.name.startswith("ultra-pinnacle-studio-"):
                    # Handle GitHub release structure
                    source_dir = item / "web_ui" if (item / "web_ui").exists() else item
                    if source_dir.exists():
                        if web_ui_dir.exists():
                            shutil.rmtree(web_ui_dir)
                        shutil.move(str(source_dir), str(web_ui_dir))

    def _update_version(self, component: str, new_version: str):
        """Update version in configuration files"""
        try:
            if component == "main":
                config_path = self.project_root / "config.json"
                with open(config_path, 'r') as f:
                    config_data = json.load(f)

                if "app" not in config_data:
                    config_data["app"] = {}
                config_data["app"]["version"] = new_version

                with open(config_path, 'w') as f:
                    json.dump(config_data, f, indent=2)

            elif component == "web_ui":
                package_path = self.project_root / "web_ui" / "package.json"
                with open(package_path, 'r') as f:
                    package_data = json.load(f)

                package_data["version"] = new_version

                with open(package_path, 'w') as f:
                    json.dump(package_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to update version: {e}")

    def _verify_upgrade_health(self, component: str) -> bool:
        """Verify system health after upgrade"""
        try:
            # Basic health checks
            if component == "main":
                # Check if API is still responding
                response = requests.get("http://localhost:8000/health", timeout=10)
                return response.status_code == 200
            elif component == "web_ui":
                # Check if frontend is accessible
                response = requests.get("http://localhost:3000", timeout=10)
                return response.status_code == 200

            return True

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def _rollback_upgrade(self, component: str, backup_path: Path, upgrade_id: str) -> bool:
        """Rollback to previous version"""
        try:
            self.logger.info(f"Rolling back upgrade: {upgrade_id}")

            if component == "main":
                # Restore main application files
                source_dirs = ["api_gateway", "scripts", "config.json", "requirements.txt"]
                for item in source_dirs:
                    source_path = backup_path / item
                    dest_path = self.project_root / item

                    if source_path.exists():
                        if dest_path.exists():
                            if dest_path.is_file():
                                dest_path.unlink()
                            else:
                                shutil.rmtree(dest_path)

                        if source_path.is_file():
                            shutil.copy2(source_path, dest_path)
                        else:
                            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

            elif component == "web_ui":
                # Restore web UI files
                source_path = backup_path / "web_ui"
                dest_path = self.project_root / "web_ui"

                if source_path.exists():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

            self.logger.info(f"Rollback completed: {upgrade_id}")
            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

    def _record_upgrade_success(self, component: str, version: str, upgrade_id: str):
        """Record successful upgrade"""
        upgrade_record = {
            "id": upgrade_id,
            "component": component,
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

        self.upgrade_history.append(upgrade_record)

        # Save to file
        history_file = self.logs_dir / "upgrade_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.upgrade_history[-100:], f, indent=2)  # Keep last 100
        except Exception as e:
            self.logger.error(f"Failed to save upgrade history: {e}")

    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            backups = sorted(self.backup_dir.glob("*.backup"), key=lambda x: x.stat().st_mtime)
            max_backups = self.upgrade_config["max_backups"]

            if len(backups) > max_backups:
                for old_backup in backups[:-max_backups]:
                    shutil.rmtree(old_backup)
                    self.logger.info(f"Removed old backup: {old_backup}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")

    def _verify_download(self, file_path: Path, expected_size: Optional[str]) -> bool:
        """Verify downloaded file integrity"""
        try:
            if expected_size:
                actual_size = file_path.stat().st_size
                expected_size_int = int(expected_size)
                if actual_size != expected_size_int:
                    self.logger.error(f"Size mismatch: expected {expected_size_int}, got {actual_size}")
                    return False

            # Basic file validation
            if file_path.stat().st_size == 0:
                self.logger.error("Downloaded file is empty")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Download verification error: {e}")
            return False

    def get_upgrade_status(self) -> Dict[str, Any]:
        """Get current upgrade status"""
        return {
            "is_upgrading": self.is_upgrading,
            "last_check": datetime.now().isoformat(),
            "upgrade_history": self.upgrade_history[-10:],  # Last 10 upgrades
            "available_backups": len(list(self.backup_dir.glob("*.backup")))
        }

    def manual_upgrade(self, component: str, version: str, download_url: str) -> bool:
        """Perform manual upgrade"""
        self.logger.info(f"Manual upgrade requested: {component} to {version}")
        return self.perform_upgrade(component, version, download_url)

    def list_available_updates(self) -> Dict[str, Any]:
        """List available updates for all components"""
        updates = {}

        for repo_name, repo_config in self.upgrade_config["repositories"].items():
            try:
                current_version = self._get_current_version(repo_name)

                if repo_config["type"] == "github":
                    latest_version, _ = self._check_github_updates(repo_config["url"])
                elif repo_config["type"] == "npm":
                    latest_version, _ = self._check_npm_updates(repo_config["url"])
                else:
                    continue

                updates[repo_name] = {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "update_available": self._is_newer_version(latest_version, current_version)
                }

            except Exception as e:
                self.logger.error(f"Error checking updates for {repo_name}: {e}")
                updates[repo_name] = {
                    "error": str(e)
                }

        return updates


def main():
    """Main entry point"""
    upgrader = AutoUpgrader()

    try:
        upgrader.start_auto_upgrade_monitoring()

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()