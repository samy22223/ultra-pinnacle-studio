#!/usr/bin/env python3
"""
Comprehensive Backup and Restore System for Ultra Pinnacle AI Studio
Provides automated backup creation, restoration, encryption, scheduling, and cloud storage capabilities
"""

import os
import json
import shutil
import gzip
import tarfile
import hashlib
import sqlite3
import threading
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class NotificationManager:
    """Handles backup notifications via email and logging"""

    def __init__(self, config: Dict):
        self.config = config
        self.smtp_config = config.get('notifications', {}).get('smtp', {})
        self.enabled = config.get('notifications', {}).get('enabled', False)

    def send_notification(self, subject: str, message: str, notification_type: str = 'info'):
        """Send notification via configured channels"""
        if not self.enabled:
            return

        # Log notification
        logger.info(f"Backup notification: {subject} - {message}")

        # Send email if configured
        if self.smtp_config.get('enabled', False):
            try:
                self._send_email(subject, message, notification_type)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")

    def _send_email(self, subject: str, message: str, notification_type: str):
        """Send email notification"""
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config.get('from_email', 'backup@ultra-pinnacle.ai')
        msg['To'] = self.smtp_config.get('to_email', 'admin@ultra-pinnacle.ai')
        msg['Subject'] = f"[Ultra Pinnacle Backup] {subject}"

        body = f"""
Backup System Notification

Type: {notification_type.upper()}
Time: {datetime.now().isoformat()}

{message}

--
Ultra Pinnacle AI Studio Backup System
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(self.smtp_config.get('server', 'localhost'), self.smtp_config.get('port', 587))
        if self.smtp_config.get('use_tls', True):
            server.starttls()

        if self.smtp_config.get('username') and self.smtp_config.get('password'):
            server.login(self.smtp_config['username'], self.smtp_config['password'])

        server.send_message(msg)
        server.quit()


class EncryptionManager:
    """Handles backup encryption and decryption"""

    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key
        self.fernet = None
        if encryption_key:
            self.fernet = Fernet(encryption_key)

    def generate_key(self, password: str, salt: bytes = None) -> str:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode()

    def encrypt_file(self, input_path: Path, output_path: Path):
        """Encrypt a file"""
        if not self.fernet:
            raise ValueError("Encryption key not set")

        with open(input_path, 'rb') as f:
            data = f.read()

        encrypted_data = self.fernet.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted_data)

    def decrypt_file(self, input_path: Path, output_path: Path):
        """Decrypt a file"""
        if not self.fernet:
            raise ValueError("Encryption key not set")

        with open(input_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = self.fernet.decrypt(encrypted_data)

        with open(output_path, 'wb') as f:
            f.write(decrypted_data)


class CloudStorageManager:
    """Handles cloud storage operations for backups"""

    def __init__(self, config: Dict):
        self.config = config.get('cloud_storage', {})
        self.enabled = self.config.get('enabled', False)
        self.provider = self.config.get('provider', 's3')
        self.bucket = self.config.get('bucket', '')
        self.client = None

        if self.enabled and self.provider == 's3':
            self.client = boto3.client(
                's3',
                aws_access_key_id=self.config.get('access_key'),
                aws_secret_access_key=self.config.get('secret_key'),
                region_name=self.config.get('region', 'us-east-1'),
                endpoint_url=self.config.get('endpoint_url')  # For S3-compatible services
            )

    def upload_backup(self, local_path: Path, remote_name: str) -> bool:
        """Upload backup to cloud storage"""
        if not self.enabled or not self.client:
            return False

        try:
            self.client.upload_file(str(local_path), self.bucket, remote_name)
            logger.info(f"Uploaded backup to cloud: {remote_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload backup to cloud: {e}")
            return False

    def download_backup(self, remote_name: str, local_path: Path) -> bool:
        """Download backup from cloud storage"""
        if not self.enabled or not self.client:
            return False

        try:
            self.client.download_file(self.bucket, remote_name, str(local_path))
            logger.info(f"Downloaded backup from cloud: {remote_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download backup from cloud: {e}")
            return False

    def list_backups(self, prefix: str = '') -> List[str]:
        """List backups in cloud storage"""
        if not self.enabled or not self.client:
            return []

        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"Failed to list cloud backups: {e}")
            return []


class BackupManager:
    """Enhanced backup and restore manager with comprehensive features"""

    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config.get('paths', {}).get('backups_dir', 'backups/'))
        self.backup_dir.mkdir(exist_ok=True)

        # Initialize components
        self.notification_manager = NotificationManager(config)
        self.encryption_manager = EncryptionManager(config.get('backup', {}).get('encryption_key'))
        self.cloud_manager = CloudStorageManager(config)

        # Backup configuration
        backup_config = config.get('backup', {})
        self.backup_paths = backup_config.get('paths', [
            'logs/',
            'uploads/',
            'encyclopedia/',
            'config.json'
        ])

        # Database configuration
        db_config = config.get('database', {})
        if db_config.get('url', '').startswith('sqlite'):
            self.database_path = db_config.get('url', 'sqlite:///./ultra_pinnacle.db').replace('sqlite:///', '')
            self.backup_paths.append(self.database_path)

        # Incremental backup settings
        self.incremental_enabled = backup_config.get('incremental', {}).get('enabled', False)
        self.incremental_manifest = self.backup_dir / 'incremental_manifest.json'

        # Scheduling
        self.scheduler = schedule.Scheduler()
        self.scheduler_thread = None
        self.stop_scheduler = False

        # Load incremental manifest if exists
        self._load_incremental_manifest()

    def _backup_full_files(self, source_path: Path, temp_dir: Path) -> int:
        """Backup files for full backup"""
        total_size = 0
        dest_path = temp_dir / source_path.name

        try:
            if source_path.is_file():
                # Special handling for SQLite database
                if str(source_path).endswith('.db'):
                    backup_db_path = dest_path
                    if self._backup_database_sqlite(str(source_path), backup_db_path):
                        total_size = backup_db_path.stat().st_size
                else:
                    shutil.copy2(source_path, dest_path)
                    total_size = source_path.stat().st_size
            else:
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                total_size = sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())
        except Exception as e:
            logger.warning(f"Failed to backup {source_path}: {e}")

        return total_size

    def _backup_incremental_files(self, source_path: Path, temp_dir: Path, changes: Dict[str, List[str]]) -> int:
        """Backup only changed files for incremental backup"""
        total_size = 0
        dest_dir = temp_dir / source_path.name
        dest_dir.mkdir(exist_ok=True)

        # Copy added and modified files
        for file_path in changes['added'] + changes['modified']:
            try:
                src_file = Path(file_path)
                if src_file.exists():
                    # Create relative path structure
                    rel_path = src_file.relative_to(source_path) if source_path.is_dir() else src_file.name
                    dest_file = dest_dir / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Special handling for SQLite database
                    if str(src_file).endswith('.db'):
                        if self._backup_database_sqlite(str(src_file), dest_file):
                            total_size += dest_file.stat().st_size
                    else:
                        shutil.copy2(src_file, dest_file)
                        total_size += src_file.stat().st_size
            except Exception as e:
                logger.warning(f"Failed to backup incremental file {file_path}: {e}")

        # Create deletion manifest
        if changes['deleted']:
            deletion_file = dest_dir / '.deleted_files.txt'
            with open(deletion_file, 'w') as f:
                for deleted_file in changes['deleted']:
                    f.write(f"{deleted_file}\n")

        return total_size

    def _get_last_full_backup(self) -> Optional[Dict[str, Any]]:
        """Get information about the last full backup"""
        try:
            backups = self.list_backups()
            for backup in backups:
                if backup.get('type') == 'full':
                    return backup
        except Exception as e:
            logger.warning(f"Failed to get last full backup: {e}")
        return None

    def _update_incremental_manifest(self, metadata: Dict[str, Any]):
        """Update incremental backup manifest with file information"""
        for file_info in metadata['files']:
            path_str = file_info['path']
            if path_str not in self.incremental_data:
                self.incremental_data[path_str] = {'files': {}}

            # Update file tracking
            source_path = Path(path_str)
            if source_path.is_file():
                files_to_track = [source_path]
            else:
                files_to_track = list(source_path.rglob('*'))

            for file_path in files_to_track:
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(source_path) if source_path.is_dir() else file_path.name)
                    self.incremental_data[path_str]['files'][relative_path] = {
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }

        self.incremental_data['last_full_backup'] = metadata['name']
        self._save_incremental_manifest()

    def _restore_full_backup(self, temp_extract: Path, extract_dir: Path):
        """Restore files from a full backup"""
        for item in temp_extract.iterdir():
            if item.name != 'backup_metadata.json':  # Skip metadata file
                dest_path = extract_dir / item.name
                if dest_path.exists():
                    if dest_path.is_dir():
                        shutil.rmtree(dest_path)
                    else:
                        dest_path.unlink()

                if item.is_file():
                    # Special handling for SQLite database
                    if str(item).endswith('.db'):
                        self._restore_database_sqlite(item, dest_path)
                    else:
                        shutil.move(str(item), str(dest_path))
                else:
                    shutil.move(str(item), str(dest_path))

    def _restore_incremental_backup(self, metadata: Dict[str, Any], temp_extract: Path, extract_dir: Path) -> bool:
        """Restore files from an incremental backup"""
        try:
            # First restore the base full backup
            base_backup_name = metadata.get('incremental_base')
            if base_backup_name:
                base_backup_file = f"{base_backup_name}.tar.gz"
                logger.info(f"Restoring base backup: {base_backup_file}")
                self.restore_backup(base_backup_file, str(extract_dir))

            # Then apply incremental changes
            for item in temp_extract.iterdir():
                if item.name != 'backup_metadata.json':
                    dest_path = extract_dir / item.name

                    if item.is_file():
                        # Special handling for SQLite database
                        if str(item).endswith('.db'):
                            self._restore_database_sqlite(item, dest_path)
                        else:
                            # Copy new/modified files
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, dest_path)
                    else:
                        # Handle directory of changes
                        self._apply_incremental_directory_changes(item, dest_path)

            # Handle deletions
            deletion_file = temp_extract / '.deleted_files.txt'
            if deletion_file.exists():
                with open(deletion_file, 'r') as f:
                    for line in f:
                        deleted_path = line.strip()
                        full_deleted_path = extract_dir / deleted_path
                        if full_deleted_path.exists():
                            if full_deleted_path.is_dir():
                                shutil.rmtree(full_deleted_path)
                            else:
                                full_deleted_path.unlink()
                            logger.info(f"Removed deleted file: {deleted_path}")

            return True
        except Exception as e:
            logger.error(f"Incremental backup restoration failed: {e}")
            raise

    def _apply_incremental_directory_changes(self, source_dir: Path, dest_dir: Path):
        """Apply incremental changes to a directory"""
        for item in source_dir.rglob('*'):
            if item.is_file():
                # Create relative path from source directory
                rel_path = item.relative_to(source_dir)
                dest_file = dest_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Special handling for SQLite database
                if str(item).endswith('.db'):
                    self._restore_database_sqlite(item, dest_file)
                else:
                    shutil.copy2(item, dest_file)

    def _load_incremental_manifest(self):
        """Load incremental backup manifest"""
        if self.incremental_manifest.exists():
            try:
                with open(self.incremental_manifest, 'r') as f:
                    self.incremental_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load incremental manifest: {e}")
                self.incremental_data = {}
        else:
            self.incremental_data = {}

    def _save_incremental_manifest(self):
        """Save incremental backup manifest"""
        try:
            with open(self.incremental_manifest, 'w') as f:
                json.dump(self.incremental_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save incremental manifest: {e}")

    def _backup_database_sqlite(self, db_path: str, backup_path: Path) -> bool:
        """Create SQLite database backup using proper locking"""
        try:
            # Connect to database with timeout to wait for locks
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.execute("BEGIN IMMEDIATE")  # Get exclusive lock

            # Create backup
            with open(backup_path, 'wb') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n".encode())

            conn.rollback()  # Release lock
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    def _restore_database_sqlite(self, backup_path: Path, db_path: str) -> bool:
        """Restore SQLite database from backup"""
        try:
            # Read SQL dump
            with open(backup_path, 'r') as f:
                sql_dump = f.read()

            # Connect to database (this will create it if it doesn't exist)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Execute SQL dump
            cursor.executescript(sql_dump)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    def _get_file_changes(self, path_str: str, last_backup_time: Optional[str] = None) -> Dict[str, Any]:
        """Get file changes since last backup for incremental backup"""
        changes = {'added': [], 'modified': [], 'deleted': []}
        source_path = Path(path_str)

        if not source_path.exists():
            return changes

        cutoff_time = None
        if last_backup_time:
            cutoff_time = datetime.fromisoformat(last_backup_time)

        if source_path.is_file():
            files_to_check = [source_path]
        else:
            files_to_check = list(source_path.rglob('*'))

        for file_path in files_to_check:
            if not file_path.is_file():
                continue

            try:
                stat = file_path.stat()
                modified_time = datetime.fromtimestamp(stat.st_mtime)

                if cutoff_time and modified_time <= cutoff_time:
                    continue

                # Check if file was in previous backup
                relative_path = str(file_path.relative_to(source_path) if source_path.is_dir() else file_path.name)
                was_backed_up = relative_path in self.incremental_data.get(path_str, {}).get('files', {})

                if was_backed_up:
                    changes['modified'].append(str(file_path))
                else:
                    changes['added'].append(str(file_path))

            except Exception as e:
                logger.warning(f"Error checking file {file_path}: {e}")

        # Check for deleted files
        if path_str in self.incremental_data:
            previous_files = set(self.incremental_data[path_str]['files'].keys())
            current_files = set()

            for file_path in files_to_check:
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(source_path) if source_path.is_dir() else file_path.name)
                    current_files.add(relative_path)

            deleted_files = previous_files - current_files
            changes['deleted'].extend(list(deleted_files))

        return changes

    def start_scheduler(self):
        """Start the automated backup scheduler"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler is already running")
            return

        self.stop_scheduler = False
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """Stop the automated backup scheduler"""
        self.stop_scheduler = True
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Backup scheduler stopped")

    def _run_scheduler(self):
        """Run the backup scheduler loop"""
        logger.info("Backup scheduler loop started")

        # Configure schedules from config
        schedule_config = self.config.get('backup', {}).get('schedule', {})

        # Daily full backup
        if schedule_config.get('daily_full_backup'):
            schedule.every().day.at(schedule_config.get('daily_full_backup_time', '02:00')).do(
                self._scheduled_backup, backup_type='full'
            )

        # Hourly incremental backup
        if schedule_config.get('hourly_incremental_backup', False):
            schedule.every().hour.do(self._scheduled_backup, backup_type='incremental')

        # Weekly cleanup
        if schedule_config.get('weekly_cleanup', False):
            schedule.every().week.do(self._scheduled_cleanup)

        while not self.stop_scheduler:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

        logger.info("Backup scheduler loop ended")

    def _scheduled_backup(self, backup_type: str = 'full'):
        """Perform scheduled backup"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = f"auto_{backup_type}_{timestamp}"

            encryption_password = self.config.get('backup', {}).get('encryption_password')
            self.create_backup(name, backup_type, encryption_password)

            logger.info(f"Scheduled {backup_type} backup completed: {name}")
        except Exception as e:
            logger.error(f"Scheduled {backup_type} backup failed: {e}")

    def _scheduled_cleanup(self):
        """Perform scheduled cleanup"""
        try:
            retention_days = self.config.get('backup', {}).get('retention_days', 30)
            removed = self.cleanup_old_backups(retention_days)
            logger.info(f"Scheduled cleanup completed: {removed} backups removed")
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")

    def configure_schedule(self, schedule_config: Dict[str, Any]):
        """Configure backup scheduling"""
        # Update config
        if 'backup' not in self.config:
            self.config['backup'] = {}
        self.config['backup']['schedule'] = schedule_config

        # Restart scheduler if running
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.stop_scheduler()
            time.sleep(1)
            self.start_scheduler()

        logger.info("Backup schedule configuration updated")

    def create_backup(self, name: Optional[str] = None, backup_type: str = 'full',
                     encryption_password: Optional[str] = None) -> str:
        """Create a new backup archive with enhanced features"""
        if name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = f"backup_{timestamp}"

        # Determine backup filename
        if backup_type == 'incremental':
            backup_filename = f"{name}_incremental.tar.gz"
        else:
            backup_filename = f"{name}.tar.gz"

        backup_path = self.backup_dir / backup_filename

        logger.info(f"Creating {backup_type} backup: {backup_filename}")

        try:
            # Create metadata
            metadata = {
                'created_at': datetime.now().isoformat(),
                'version': self.config.get('app', {}).get('version', '1.0.0'),
                'name': name,
                'type': backup_type,
                'files': [],
                'total_size': 0,
                'encrypted': encryption_password is not None,
                'incremental_base': None
            }

            # Create temporary directory for backup
            temp_dir = self.backup_dir / f"temp_{name}"
            temp_dir.mkdir(exist_ok=True)

            total_size = 0
            last_backup_time = None

            # For incremental backups, get last full backup time
            if backup_type == 'incremental':
                last_full_backup = self._get_last_full_backup()
                if last_full_backup:
                    metadata['incremental_base'] = last_full_backup['name']
                    last_backup_time = last_full_backup['created']

            # Process files for backup
            for path_str in self.backup_paths:
                source_path = Path(path_str)
                if source_path.exists():
                    if backup_type == 'incremental':
                        # Handle incremental backup
                        changes = self._get_file_changes(path_str, last_backup_time)
                        size = self._backup_incremental_files(source_path, temp_dir, changes)
                    else:
                        # Handle full backup
                        size = self._backup_full_files(source_path, temp_dir)

                    if size > 0:
                        metadata['files'].append({
                            'path': str(source_path),
                            'size': size,
                            'type': 'file' if source_path.is_file() else 'directory',
                            'changes': changes if backup_type == 'incremental' else None
                        })
                        total_size += size

            metadata['total_size'] = total_size

            # Save metadata
            with open(temp_dir / 'backup_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # Create compressed archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                for item in temp_dir.rglob('*'):
                    if item.is_file():
                        tar.add(item, arcname=item.relative_to(temp_dir))

            # Encrypt if password provided
            if encryption_password:
                encrypted_path = backup_path.with_suffix('.tar.gz.enc')
                encryption_key = self.encryption_manager.generate_key(encryption_password)
                temp_encryption = EncryptionManager(encryption_key)
                temp_encryption.encrypt_file(backup_path, encrypted_path)
                backup_path.unlink()  # Remove unencrypted file
                backup_path = encrypted_path
                backup_filename = encrypted_path.name

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            checksum_file = backup_path.with_suffix('.sha256')
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {backup_filename}\n")

            # Upload to cloud if configured
            if self.cloud_manager.enabled:
                cloud_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_filename}"
                if self.cloud_manager.upload_backup(backup_path, cloud_name):
                    metadata['cloud_storage'] = {
                        'uploaded': True,
                        'cloud_name': cloud_name,
                        'provider': self.cloud_manager.provider
                    }

            # Update incremental manifest for full backups
            if backup_type == 'full':
                self._update_incremental_manifest(metadata)

            # Cleanup
            shutil.rmtree(temp_dir)

            # Send notification
            self.notification_manager.send_notification(
                f"Backup {backup_type.title()} Created",
                f"Backup '{name}' created successfully. Size: {total_size} bytes",
                'success'
            )

            logger.info(f"Backup created successfully: {backup_filename} ({total_size} bytes)")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            # Send failure notification
            self.notification_manager.send_notification(
                "Backup Creation Failed",
                f"Failed to create backup '{name}': {str(e)}",
                'error'
            )
            # Cleanup on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_path.exists():
                backup_path.unlink()
            raise

    def list_backups(self) -> List[Dict]:
        """List all available backups with enhanced metadata"""
        backups = []

        # Check local backups
        for pattern in ['*.tar.gz', '*.tar.gz.enc']:
            for file_path in self.backup_dir.glob(pattern):
                backup_info = self._get_backup_info(file_path)
                if backup_info:
                    backups.append(backup_info)

        # Check cloud backups if enabled
        if self.cloud_manager.enabled:
            cloud_backups = self.cloud_manager.list_backups()
            for cloud_backup in cloud_backups:
                # Create info for cloud backup
                cloud_info = {
                    'filename': cloud_backup,
                    'path': f"cloud://{self.cloud_manager.bucket}/{cloud_backup}",
                    'size': 0,  # Size not available from list
                    'created': datetime.now().isoformat(),  # Approximate
                    'checksum_valid': True,  # Assume valid in cloud
                    'location': 'cloud',
                    'type': 'unknown',
                    'encrypted': cloud_backup.endswith('.enc')
                }
                backups.append(cloud_info)

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

    def _get_backup_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get detailed information about a backup file"""
        try:
            checksum_file = file_path.with_suffix('.sha256')
            encrypted = file_path.suffix == '.enc'

            backup_info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'created': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'checksum_valid': False,
                'location': 'local',
                'type': 'full',  # Default
                'encrypted': encrypted,
                'incremental_base': None,
                'cloud_storage': None
            }

            # Try to read metadata if not encrypted
            if not encrypted:
                try:
                    with tarfile.open(file_path, 'r:gz') as tar:
                        metadata_member = None
                        for member in tar.getmembers():
                            if member.name.endswith('backup_metadata.json'):
                                metadata_member = member
                                break

                        if metadata_member:
                            import io
                            metadata_content = tar.extractfile(metadata_member)
                            if metadata_content:
                                metadata = json.load(io.TextIOWrapper(metadata_content))
                                backup_info.update({
                                    'type': metadata.get('type', 'full'),
                                    'incremental_base': metadata.get('incremental_base'),
                                    'cloud_storage': metadata.get('cloud_storage'),
                                    'version': metadata.get('version'),
                                    'total_size': metadata.get('total_size', 0)
                                })
                except Exception as e:
                    logger.warning(f"Could not read metadata for {file_path}: {e}")

            # Verify checksum if available
            if checksum_file.exists():
                try:
                    with open(checksum_file, 'r') as f:
                        expected_checksum = f.read().split()[0]

                    actual_checksum = self._calculate_checksum(file_path)
                    backup_info['checksum_valid'] = expected_checksum == actual_checksum
                except Exception:
                    pass

            return backup_info
        except Exception as e:
            logger.warning(f"Error getting backup info for {file_path}: {e}")
            return None

    def restore_backup(self, backup_name: str, target_dir: Optional[str] = None,
                      decryption_password: Optional[str] = None,
                      point_in_time: Optional[str] = None) -> bool:
        """Restore from a backup archive with enhanced features"""
        backup_path = self.backup_dir / backup_name

        # Handle encrypted backups
        if backup_name.endswith('.enc'):
            if not decryption_password:
                raise ValueError("Decryption password required for encrypted backup")

            # Decrypt to temporary file
            temp_decrypted = backup_path.with_suffix('')
            encryption_key = self.encryption_manager.generate_key(decryption_password)
            temp_encryption = EncryptionManager(encryption_key)
            temp_encryption.decrypt_file(backup_path, temp_decrypted)
            backup_path = temp_decrypted
            use_temp_file = True
        else:
            use_temp_file = False

        try:
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup not found: {backup_name}")

            # Verify checksum if available
            checksum_file = backup_path.with_suffix('.sha256')
            if checksum_file.exists():
                try:
                    with open(checksum_file, 'r') as f:
                        expected_checksum = f.read().split()[0]

                    actual_checksum = self._calculate_checksum(backup_path)
                    if expected_checksum != actual_checksum:
                        raise ValueError("Backup checksum verification failed")
                except Exception as e:
                    logger.warning(f"Checksum verification failed: {e}")

            logger.info(f"Restoring backup: {backup_name}")

            # Create temporary extraction directory
            extract_dir = Path(target_dir) if target_dir else Path('.')
            temp_extract = extract_dir / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_extract.mkdir(parents=True, exist_ok=True)

            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_extract)

            # Load and validate backup metadata
            metadata_file = temp_extract / 'backup_metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                logger.info(f"Backup metadata: {metadata.get('name', 'unknown')} - {metadata.get('total_size', 0)} bytes")

                # Handle incremental backup restoration
                if metadata.get('type') == 'incremental':
                    return self._restore_incremental_backup(metadata, temp_extract, extract_dir)

            # Standard full backup restoration
            self._restore_full_backup(temp_extract, extract_dir)

            # Cleanup
            shutil.rmtree(temp_extract)
            if use_temp_file and temp_decrypted.exists():
                temp_decrypted.unlink()

            # Send notification
            self.notification_manager.send_notification(
                "Backup Restoration Completed",
                f"Successfully restored backup '{backup_name}'",
                'success'
            )

            logger.info("Backup restoration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            # Send failure notification
            self.notification_manager.send_notification(
                "Backup Restoration Failed",
                f"Failed to restore backup '{backup_name}': {str(e)}",
                'error'
            )
            # Cleanup on failure
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            if use_temp_file and 'temp_decrypted' in locals() and temp_decrypted.exists():
                temp_decrypted.unlink()
            raise

    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        for file_path in self.backup_dir.glob('*.tar.gz'):
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_date < cutoff_date:
                # Remove backup file and checksum
                file_path.unlink()
                checksum_file = file_path.with_suffix('.tar.gz.sha256')
                if checksum_file.exists():
                    checksum_file.unlink()

                removed_count += 1
                logger.info(f"Removed old backup: {file_path.name}")

        logger.info(f"Cleanup completed: {removed_count} old backups removed")
        return removed_count

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

def main():
    """Command-line interface for enhanced backup operations"""
    import argparse

    parser = argparse.ArgumentParser(description='Ultra Pinnacle AI Studio Enhanced Backup Manager')
    parser.add_argument('action', choices=['create', 'list', 'restore', 'cleanup', 'schedule', 'verify', 'status'],
                        help='Action to perform')
    parser.add_argument('--name', help='Backup name (for create/restore)')
    parser.add_argument('--target', help='Target directory for restore')
    parser.add_argument('--retention', type=int, default=30,
                        help='Retention period in days for cleanup')
    parser.add_argument('--type', choices=['full', 'incremental'], default='full',
                        help='Backup type (default: full)')
    parser.add_argument('--encrypt', help='Encryption password for backup')
    parser.add_argument('--decrypt', help='Decryption password for restore')
    parser.add_argument('--schedule-config', help='JSON string with schedule configuration')
    parser.add_argument('--start-scheduler', action='store_true', help='Start the backup scheduler')
    parser.add_argument('--stop-scheduler', action='store_true', help='Stop the backup scheduler')

    args = parser.parse_args()

    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found")
        return 1

    manager = BackupManager(config)

    try:
        if args.action == 'create':
            backup_path = manager.create_backup(args.name, args.type, args.encrypt)
            print(f"Backup created: {backup_path}")

        elif args.action == 'list':
            backups = manager.list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backups:")
                for backup in backups:
                    status = "✓" if backup['checksum_valid'] else "✗"
                    enc = "🔒" if backup.get('encrypted', False) else " "
                    loc = backup.get('location', 'local')
                    typ = backup.get('type', 'full')
                    size_mb = backup['size'] / (1024 * 1024) if backup['size'] > 0 else 0
                    print(f"  {status}{enc} {backup['filename']} ({size_mb:.1f} MB) - {backup['created']} [{loc}/{typ}]")

        elif args.action == 'restore':
            if not args.name:
                print("Error: --name required for restore")
                return 1
            success = manager.restore_backup(args.name, args.target, args.decrypt)
            print("Restore completed successfully" if success else "Restore failed")

        elif args.action == 'cleanup':
            removed = manager.cleanup_old_backups(args.retention)
            print(f"Cleanup completed: {removed} old backups removed")

        elif args.action == 'schedule':
            if args.schedule_config:
                schedule_config = json.loads(args.schedule_config)
                manager.configure_schedule(schedule_config)
                print("Backup schedule configured")
            else:
                print("Error: --schedule-config required for schedule action")

        elif args.action == 'verify':
            if not args.name:
                print("Error: --name required for verify")
                return 1
            # Verify backup integrity
            backups = manager.list_backups()
            backup = next((b for b in backups if b['filename'] == args.name), None)
            if not backup:
                print(f"Backup not found: {args.name}")
                return 1

            if backup['checksum_valid']:
                print(f"✓ Backup integrity verified: {args.name}")
            else:
                print(f"✗ Backup integrity check failed: {args.name}")
                return 1

        elif args.action == 'status':
            # Show backup system status
            scheduler_running = manager.scheduler_thread and manager.scheduler_thread.is_alive() if hasattr(manager, 'scheduler_thread') else False
            print(f"Scheduler running: {'Yes' if scheduler_running else 'No'}")
            print(f"Cloud storage: {'Enabled' if manager.cloud_manager.enabled else 'Disabled'}")
            print(f"Encryption: {'Enabled' if manager.encryption_manager.encryption_key else 'Disabled'}")
            print(f"Incremental backups: {'Enabled' if manager.incremental_enabled else 'Disabled'}")
            print(f"Notifications: {'Enabled' if manager.notification_manager.enabled else 'Disabled'}")

            backups = manager.list_backups()
            print(f"Total backups: {len(backups)}")

        # Scheduler control
        if args.start_scheduler:
            manager.start_scheduler()
            print("Backup scheduler started")

        if args.stop_scheduler:
            manager.stop_scheduler()
            print("Backup scheduler stopped")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())