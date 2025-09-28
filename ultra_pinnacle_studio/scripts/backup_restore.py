#!/usr/bin/env python3
"""
Backup and Restore System for Ultra Pinnacle AI Studio
Provides automated backup creation and restoration capabilities
"""

import os
import json
import shutil
import gzip
import tarfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages backup and restore operations"""

    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config.get('paths', {}).get('backups_dir', 'backups/'))
        self.backup_dir.mkdir(exist_ok=True)

        # Directories to backup
        self.backup_paths = [
            'logs/',
            'uploads/',
            'encyclopedia/',
            'config.json'
        ]

        # Optional: database backup if configured
        if config.get('database', {}).get('type'):
            self.backup_paths.append('database/')

    def create_backup(self, name: Optional[str] = None) -> str:
        """Create a new backup archive"""
        if name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = f"backup_{timestamp}"

        backup_filename = f"{name}.tar.gz"
        backup_path = self.backup_dir / backup_filename

        logger.info(f"Creating backup: {backup_filename}")

        try:
            # Create metadata
            metadata = {
                'created_at': datetime.now().isoformat(),
                'version': self.config.get('app', {}).get('version', '1.0.0'),
                'name': name,
                'files': [],
                'total_size': 0
            }

            # Create temporary directory for backup
            temp_dir = self.backup_dir / f"temp_{name}"
            temp_dir.mkdir(exist_ok=True)

            total_size = 0

            # Copy files to backup
            for path_str in self.backup_paths:
                source_path = Path(path_str)
                if source_path.exists():
                    dest_path = temp_dir / source_path.name

                    if source_path.is_file():
                        shutil.copy2(source_path, dest_path)
                        size = source_path.stat().st_size
                    else:
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                        size = sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())

                    metadata['files'].append({
                        'path': str(source_path),
                        'size': size,
                        'type': 'file' if source_path.is_file() else 'directory'
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

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            checksum_file = backup_path.with_suffix('.tar.gz.sha256')
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {backup_filename}\n")

            # Cleanup
            shutil.rmtree(temp_dir)

            logger.info(f"Backup created successfully: {backup_filename} ({total_size} bytes)")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            # Cleanup on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_path.exists():
                backup_path.unlink()
            raise

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []

        for file_path in self.backup_dir.glob('*.tar.gz'):
            checksum_file = file_path.with_suffix('.tar.gz.sha256')

            backup_info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'created': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'checksum_valid': False
            }

            # Verify checksum if available
            if checksum_file.exists():
                try:
                    with open(checksum_file, 'r') as f:
                        expected_checksum = f.read().split()[0]

                    actual_checksum = self._calculate_checksum(file_path)
                    backup_info['checksum_valid'] = expected_checksum == actual_checksum
                except Exception:
                    pass

            backups.append(backup_info)

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

    def restore_backup(self, backup_name: str, target_dir: Optional[str] = None) -> bool:
        """Restore from a backup archive"""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        # Verify checksum if available
        checksum_file = backup_path.with_suffix('.tar.gz.sha256')
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

        try:
            # Create temporary extraction directory
            extract_dir = Path(target_dir) if target_dir else Path('.')
            temp_extract = extract_dir / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_extract.mkdir(parents=True, exist_ok=True)

            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_extract)

            # Validate backup metadata
            metadata_file = temp_extract / 'backup_metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                logger.info(f"Backup metadata: {metadata.get('name', 'unknown')} - {metadata.get('total_size', 0)} bytes")

            # Move files to final location
            for item in temp_extract.iterdir():
                if item.name != 'backup_metadata.json':  # Skip metadata file
                    dest_path = extract_dir / item.name
                    if dest_path.exists():
                        if dest_path.is_dir():
                            shutil.rmtree(dest_path)
                        else:
                            dest_path.unlink()

                    if item.is_file():
                        shutil.move(str(item), str(dest_path))
                    else:
                        shutil.move(str(item), str(dest_path))

            # Cleanup
            shutil.rmtree(temp_extract)

            logger.info("Backup restoration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            # Cleanup on failure
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
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
    """Command-line interface for backup operations"""
    import argparse

    parser = argparse.ArgumentParser(description='Ultra Pinnacle AI Studio Backup Manager')
    parser.add_argument('action', choices=['create', 'list', 'restore', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--name', help='Backup name (for create/restore)')
    parser.add_argument('--target', help='Target directory for restore')
    parser.add_argument('--retention', type=int, default=30,
                       help='Retention period in days for cleanup')

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
            backup_path = manager.create_backup(args.name)
            print(f"Backup created: {backup_path}")

        elif args.action == 'list':
            backups = manager.list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backups:")
                for backup in backups:
                    status = "✓" if backup['checksum_valid'] else "✗"
                    print(f"  {status} {backup['filename']} ({backup['size']} bytes) - {backup['created']}")

        elif args.action == 'restore':
            if not args.name:
                print("Error: --name required for restore")
                return 1
            success = manager.restore_backup(args.name, args.target)
            print("Restore completed successfully" if success else "Restore failed")

        elif args.action == 'cleanup':
            removed = manager.cleanup_old_backups(args.retention)
            print(f"Cleanup completed: {removed} old backups removed")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())