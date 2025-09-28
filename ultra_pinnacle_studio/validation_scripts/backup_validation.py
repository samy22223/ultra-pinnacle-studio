#!/usr/bin/env python3
"""
Backup & Restore Validation Script for Ultra Pinnacle AI Studio
Tests the backup and restore functionality
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_backup_system():
    """Test backup and restore system functionality"""
    print("💾 BACKUP SYSTEM VALIDATION")
    print("=" * 50)

    try:
        from scripts.backup_restore import BackupManager
    except ImportError as e:
        print(f"❌ Cannot import BackupManager: {e}")
        return False

    # Create temporary config for testing
    test_config = {
        'paths': {
            'backups_dir': 'test_backups/',
            'logs_dir': 'logs/',
            'uploads_dir': 'uploads/',
            'encyclopedia_dir': 'encyclopedia/'
        }
    }

    # Create test data
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        backup_dir = test_dir / 'test_backups'
        backup_dir.mkdir()

        # Create test files
        logs_dir = test_dir / 'logs'
        logs_dir.mkdir()
        (logs_dir / 'test.log').write_text('Test log content')

        uploads_dir = test_dir / 'uploads'
        uploads_dir.mkdir()
        (uploads_dir / 'test.txt').write_text('Test upload content')

        encyclopedia_dir = test_dir / 'encyclopedia'
        encyclopedia_dir.mkdir()
        (encyclopedia_dir / 'test.md').write_text('# Test Article\n\nTest content')

        # Update config with temp paths
        test_config['paths']['backups_dir'] = str(backup_dir)
        test_config['paths']['logs_dir'] = str(logs_dir)
        test_config['paths']['uploads_dir'] = str(uploads_dir)
        test_config['paths']['encyclopedia_dir'] = str(encyclopedia_dir)

        # Initialize backup manager
        manager = BackupManager(test_config)

        # Test 1: Create backup
        print("\n1. Testing backup creation...")
        try:
            backup_path = manager.create_backup('test_backup')
            if os.path.exists(backup_path):
                print("✅ Backup creation successful")
                backup_size = os.path.getsize(backup_path)
                print(f"   └─ Backup size: {backup_size} bytes")
            else:
                print("❌ Backup file not created")
                return False
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            return False

        # Test 2: List backups
        print("\n2. Testing backup listing...")
        try:
            backups = manager.list_backups()
            if len(backups) > 0:
                print(f"✅ Found {len(backups)} backup(s)")
                for backup in backups:
                    print(f"   └─ {backup['filename']} ({backup['size']} bytes)")
            else:
                print("❌ No backups found")
                return False
        except Exception as e:
            print(f"❌ Backup listing failed: {e}")
            return False

        # Test 3: Verify backup integrity
        print("\n3. Testing backup integrity...")
        try:
            # Check if backup is valid archive
            import tarfile
            with tarfile.open(backup_path, 'r:gz') as tar:
                members = tar.getmembers()
                print(f"✅ Backup contains {len(members)} files")

                # Check for expected files
                expected_files = ['backup_metadata.json', 'logs/test.log', 'uploads/test.txt', 'encyclopedia/test.md']
                found_files = [m.name for m in members]

                found_count = sum(1 for ef in expected_files if any(ef in ff for ff in found_files))
                if found_count == len(expected_files):
                    print("✅ All expected files present in backup")
                else:
                    print(f"⚠️ Some files missing: {found_count}/{len(expected_files)} found")
                    return False

        except Exception as e:
            print(f"❌ Backup integrity check failed: {e}")
            return False

        # Test 4: Restore backup
        print("\n4. Testing backup restoration...")
        restore_dir = test_dir / 'restore_test'
        restore_dir.mkdir()

        try:
            success = manager.restore_backup('test_backup.tar.gz', str(restore_dir))
            if success:
                print("✅ Backup restoration successful")

                # Verify restored files
                restored_files = [
                    restore_dir / 'logs' / 'test.log',
                    restore_dir / 'uploads' / 'test.txt',
                    restore_dir / 'encyclopedia' / 'test.md'
                ]

                restored_count = sum(1 for f in restored_files if f.exists())
                if restored_count == len(restored_files):
                    print("✅ All files restored correctly")
                else:
                    print(f"❌ Some files not restored: {restored_count}/{len(restored_files)}")
                    return False

            else:
                print("❌ Backup restoration failed")
                return False

        except Exception as e:
            print(f"❌ Backup restoration failed: {e}")
            return False

        # Test 5: Checksum validation
        print("\n5. Testing checksum validation...")
        try:
            # Verify checksum file exists
            checksum_file = Path(backup_path).with_suffix('.tar.gz.sha256')
            if checksum_file.exists():
                print("✅ Checksum file created")

                # Test checksum validation
                import hashlib
                with open(backup_path, 'rb') as f:
                    actual_checksum = hashlib.sha256(f.read()).hexdigest()

                with open(checksum_file, 'r') as f:
                    expected_checksum = f.read().split()[0]

                if actual_checksum == expected_checksum:
                    print("✅ Checksum validation passed")
                else:
                    print("❌ Checksum validation failed")
                    return False
            else:
                print("⚠️ Checksum file not found")
        except Exception as e:
            print(f"❌ Checksum validation error: {e}")
            return False

    print("\n🎉 All backup system tests passed!")
    return True

def validate_backup_cli():
    """Test backup command-line interface"""
    print("\n💻 BACKUP CLI VALIDATION")
    print("=" * 50)

    # Test CLI help
    import subprocess
    try:
        result = subprocess.run([sys.executable, '../scripts/backup_restore.py', '--help'],
                              capture_output=True, text=True, cwd='..')

        if result.returncode == 0 and 'usage:' in result.stdout.lower():
            print("✅ CLI help command works")
        else:
            print("❌ CLI help command failed")
            return False

        # Test list command (should work even with no backups)
        result = subprocess.run([sys.executable, '../scripts/backup_restore.py', 'list'],
                              capture_output=True, text=True, cwd='..')

        if result.returncode == 0:
            print("✅ CLI list command works")
        else:
            print(f"❌ CLI list command failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ CLI validation error: {e}")
        return False

    return True

def main():
    """Run comprehensive backup validation"""
    print("🔍 BACKUP & RESTORE VALIDATION")
    print("=" * 60)

    checks = [
        validate_backup_system,
        validate_backup_cli,
    ]

    results = []
    for check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f'❌ {check_func.__name__}: Exception - {e}')
            results.append(False)

    # Summary
    print('\n' + '=' * 60)
    passed_count = sum(results)
    total_count = len(results)

    if passed_count == total_count:
        print('🎉 ALL BACKUP VALIDATION CHECKS PASSED!')
        print('✅ Backup and restore system is fully functional')
        print('\n💡 Usage examples:')
        print('   python scripts/backup_restore.py create --name daily')
        print('   python scripts/backup_restore.py list')
        print('   python scripts/backup_restore.py restore daily_backup.tar.gz')
    else:
        print(f'⚠️ {passed_count}/{total_count} validation checks passed')
        print('❌ Some backup system issues found')

    print('=' * 60)

    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)