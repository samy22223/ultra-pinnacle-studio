# Ultra Pinnacle AI Studio Backup and Recovery Guide

## Overview

This document provides comprehensive guidance for backup and recovery operations in Ultra Pinnacle AI Studio. The system includes automated scheduling, encryption, incremental backups, cloud storage integration, and point-in-time recovery capabilities.

## Features

- **Automated Backup Scheduling**: Configurable daily full backups and hourly incremental backups
- **Incremental Backups**: Only backup changed files to reduce storage requirements
- **Encryption**: AES-256 encryption for secure backup storage
- **Cloud Storage**: S3-compatible cloud storage integration
- **Point-in-Time Recovery**: Restore to specific points in time
- **Integrity Verification**: SHA256 checksums for backup validation
- **Web UI Management**: Complete backup management through the web interface
- **Notification System**: Email notifications for backup events

## Configuration

### Basic Configuration

The backup system is configured in `config.json`:

```json
{
  "backup": {
    "enabled": true,
    "paths": [
      "logs/",
      "uploads/",
      "encyclopedia/",
      "config.json"
    ],
    "incremental": {
      "enabled": true
    },
    "schedule": {
      "daily_full_backup": true,
      "daily_full_backup_time": "02:00",
      "hourly_incremental_backup": false,
      "weekly_cleanup": true
    },
    "retention_days": 30,
    "encryption": {
      "enabled": false,
      "key": null
    }
  },
  "notifications": {
    "enabled": true,
    "smtp": {
      "enabled": false,
      "server": "localhost",
      "port": 587,
      "use_tls": true,
      "username": null,
      "password": null,
      "from_email": "backup@ultra-pinnacle.ai",
      "to_email": "admin@ultra-pinnacle.ai"
    }
  },
  "cloud_storage": {
    "enabled": false,
    "provider": "s3",
    "bucket": "ultra-pinnacle-backups",
    "access_key": null,
    "secret_key": null,
    "region": "us-east-1",
    "endpoint_url": null
  }
}
```

### Cloud Storage Setup

To enable cloud storage:

1. Set `"cloud_storage.enabled": true`
2. Configure your S3-compatible storage credentials
3. For AWS S3: Use standard AWS credentials
4. For other providers (MinIO, DigitalOcean Spaces, etc.): Set `endpoint_url`

### Encryption Setup

To enable backup encryption:

1. Set `"backup.encryption.enabled": true`
2. Provide an encryption key or password when creating backups
3. The same password/key is required for restoration

## Using the Web Interface

### Accessing Backup Management

1. Navigate to the Backup section in the web UI
2. Login with administrator credentials

### Creating Backups

1. Click "Create Backup"
2. Choose backup type:
   - **Full Backup**: Complete backup of all configured paths
   - **Incremental Backup**: Only backup changes since last full backup
3. Optionally provide a custom name
4. Optionally set an encryption password
5. Click "Create Backup"

### Restoring Backups

1. Select a backup from the list
2. Click "Restore"
3. Confirm the restoration (this will overwrite existing files)
4. If encrypted, provide the decryption password

### Managing the Scheduler

- **Start Scheduler**: Enable automated backups
- **Stop Scheduler**: Disable automated backups
- View scheduler status in the System Status panel

## Command Line Usage

### Basic Commands

```bash
# Create a full backup
python scripts/backup_restore.py create --type full --name my_backup

# Create an incremental backup
python scripts/backup_restore.py create --type incremental

# Create an encrypted backup
python scripts/backup_restore.py create --encrypt mypassword

# List all backups
python scripts/backup_restore.py list

# Restore a backup
python scripts/backup_restore.py restore backup_20231201_020000.tar.gz

# Restore an encrypted backup
python scripts/backup_restore.py restore backup_20231201_020000.tar.gz.enc --decrypt mypassword

# Verify backup integrity
python scripts/backup_restore.py verify backup_20231201_020000.tar.gz

# Clean up old backups
python scripts/backup_restore.py cleanup --retention 30

# Start backup scheduler
python scripts/backup_restore.py schedule --start-scheduler

# Get system status
python scripts/backup_restore.py status
```

### Advanced Configuration

Configure scheduling via JSON:

```bash
python scripts/backup_restore.py schedule --schedule-config '{
  "daily_full_backup": true,
  "daily_full_backup_time": "03:00",
  "hourly_incremental_backup": true,
  "weekly_cleanup": true
}'
```

## Disaster Recovery Procedures

### Emergency Recovery Steps

1. **Stop the System**
   ```bash
   # Stop all services
   pkill -f "python start_server.py"
   ```

2. **Identify the Recovery Point**
   - Check available backups using the web UI or CLI
   - Choose the most recent full backup + any incremental backups

3. **Prepare Recovery Environment**
   ```bash
   # Create a backup of current state (if possible)
   cp -r ultra_pinnacle_studio ultra_pinnacle_studio.backup

   # Ensure backup directory exists
   mkdir -p ultra_pinnacle_studio/backups
   ```

4. **Perform Recovery**
   ```bash
   # Navigate to the studio directory
   cd ultra_pinnacle_studio

   # Restore the most recent full backup
   python scripts/backup_restore.py restore backup_20231201_020000.tar.gz

   # If using incremental backups, restore them in order
   python scripts/backup_restore.py restore backup_20231201_030000_incremental.tar.gz
   python scripts/backup_restore.py restore backup_20231201_040000_incremental.tar.gz
   ```

5. **Verify Recovery**
   ```bash
   # Check file integrity
   python scripts/backup_restore.py verify backup_20231201_020000.tar.gz

   # Start the system
   python start_server.py

   # Check logs for any issues
   tail -f logs/ultra_pinnacle.log
   ```

6. **Post-Recovery Tasks**
   - Verify database integrity
   - Check user data and configurations
   - Test core functionality
   - Update any external systems with new endpoints

### Database-Specific Recovery

For SQLite database recovery:

```bash
# Stop the application first
pkill -f "python start_server.py"

# Restore database from backup
python scripts/backup_restore.py restore backup_name.tar.gz

# Verify database integrity
sqlite3 ultra_pinnacle.db "PRAGMA integrity_check;"

# Restart the application
python start_server.py
```

### Cloud Storage Recovery

If backups are stored in cloud storage:

```bash
# Download backup from cloud (if not using integrated cloud sync)
# Use your cloud provider's CLI tools or the web interface

# Then restore normally
python scripts/backup_restore.py restore downloaded_backup.tar.gz
```

## Backup Strategy Recommendations

### Daily Operations

- **Full Backups**: Daily at 2:00 AM (low-usage time)
- **Incremental Backups**: Every 6 hours during business hours
- **Retention**: 30 days for daily backups, 7 days for incrementals

### High-Availability Setup

- **Multiple Locations**: Store backups locally and in cloud
- **Offsite Storage**: Use geographically separate cloud regions
- **Encryption**: Always encrypt sensitive backups
- **Testing**: Monthly recovery testing

### Large-Scale Deployments

- **Parallel Processing**: Use multiple backup processes for large datasets
- **Compression**: Enable compression for storage efficiency
- **Monitoring**: Set up alerts for backup failures
- **Documentation**: Maintain detailed recovery procedures

## Monitoring and Alerts

### Backup Health Checks

The system provides several monitoring endpoints:

- `/backup/status` - Current backup system status
- `/backup/list` - List of available backups
- `/health` - Overall system health including backup status

### Notification Configuration

Configure email notifications in `config.json`:

```json
{
  "notifications": {
    "enabled": true,
    "smtp": {
      "enabled": true,
      "server": "smtp.gmail.com",
      "port": 587,
      "use_tls": true,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "from_email": "backup@ultra-pinnacle.ai",
      "to_email": "admin@ultra-pinnacle.ai"
    }
  }
}
```

### Log Monitoring

Monitor backup logs in:
- `logs/ultra_pinnacle.log` - Main application logs
- `logs/auto_backup.log` - Automated backup logs
- `logs/backup_errors.log` - Backup error logs

## Troubleshooting

### Common Issues

1. **Backup Creation Fails**
   - Check disk space: `df -h`
   - Verify permissions on backup directory
   - Check database locks: `fuser ultra_pinnacle.db`

2. **Restore Fails**
   - Ensure application is stopped
   - Check file permissions
   - Verify backup integrity first

3. **Scheduler Not Running**
   - Check system logs for errors
   - Verify configuration is valid
   - Restart the scheduler manually

4. **Cloud Storage Issues**
   - Verify credentials
   - Check network connectivity
   - Confirm bucket permissions

### Performance Optimization

- **Large Backups**: Use incremental backups for faster operations
- **Compression**: Enable gzip compression (default)
- **Parallel Processing**: For large filesystems, consider parallel backup processes
- **Storage**: Use SSD storage for backup operations

## Security Considerations

- **Encryption**: Always encrypt backups containing sensitive data
- **Access Control**: Limit backup management to administrators
- **Network Security**: Use HTTPS for web UI access
- **Credential Management**: Store cloud credentials securely
- **Audit Logging**: Monitor backup operations for security events

## Maintenance Tasks

### Weekly Tasks
- Review backup logs for errors
- Verify backup integrity
- Check storage usage
- Test restore procedures

### Monthly Tasks
- Perform full system recovery test
- Update backup configurations as needed
- Review retention policies
- Audit backup access logs

### Annual Tasks
- Review disaster recovery procedures
- Update contact information
- Test cloud storage failover
- Evaluate backup system performance

## Support and Contact

For technical support with backup and recovery operations:

- Check the logs in `logs/` directory
- Review this documentation
- Contact the system administrator
- Check the GitHub repository for updates

## Version History

- **v1.0.0**: Initial comprehensive backup system
  - Full and incremental backups
  - Encryption support
  - Cloud storage integration
  - Web UI management
  - Automated scheduling
  - Point-in-time recovery