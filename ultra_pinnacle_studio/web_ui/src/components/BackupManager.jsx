import React, { useState, useEffect } from 'react';
import './BackupManager.css';

const BackupManager = () => {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({});
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    type: 'full',
    encryptionPassword: ''
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadBackups();
    loadStatus();
  }, []);

  const loadBackups = async () => {
    try {
      const response = await fetch('/backup/list', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setBackups(data);
      }
    } catch (error) {
      console.error('Error loading backups:', error);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch('/backup/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Error loading status:', error);
    }
  };

  const createBackup = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        name: createForm.name || undefined,
        backup_type: createForm.type,
        ...(createForm.encryptionPassword && { encryption_password: createForm.encryptionPassword })
      });

      const response = await fetch(`/backup/create?${params}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        setMessage('Backup created successfully!');
        setShowCreateForm(false);
        setCreateForm({ name: '', type: 'full', encryptionPassword: '' });
        loadBackups();
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  const restoreBackup = async (backupName) => {
    if (!confirm(`Are you sure you want to restore backup: ${backupName}?`)) return;

    setLoading(true);
    try {
      const response = await fetch('/backup/restore', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: new URLSearchParams({ backup_name: backupName })
      });

      if (response.ok) {
        setMessage('Backup restored successfully!');
        loadBackups();
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  const verifyBackup = async (backupName) => {
    setLoading(true);
    try {
      const response = await fetch('/backup/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: new URLSearchParams({ backup_name: backupName })
      });

      if (response.ok) {
        const result = await response.json();
        setMessage(result.message);
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  const cleanupBackups = async () => {
    if (!confirm('Are you sure you want to clean up old backups?')) return;

    setLoading(true);
    try {
      const response = await fetch('/backup/cleanup', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const result = await response.json();
        setMessage(result.message);
        loadBackups();
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  const toggleScheduler = async (action) => {
    setLoading(true);
    try {
      const response = await fetch(`/backup/scheduler/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        setMessage(`Scheduler ${action}d successfully!`);
        loadStatus();
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="backup-manager">
      <h2>Backup Management</h2>

      {message && (
        <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
          {message}
          <button onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <div className="backup-controls">
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          disabled={loading}
          className="btn-primary"
        >
          Create Backup
        </button>
        <button
          onClick={cleanupBackups}
          disabled={loading}
          className="btn-secondary"
        >
          Cleanup Old Backups
        </button>
        <button
          onClick={() => toggleScheduler(status.status === 'running' ? 'stop' : 'start')}
          disabled={loading}
          className={`btn-secondary ${status.status === 'running' ? 'active' : ''}`}
        >
          {status.status === 'running' ? 'Stop' : 'Start'} Scheduler
        </button>
      </div>

      {showCreateForm && (
        <div className="create-form">
          <h3>Create New Backup</h3>
          <div className="form-group">
            <label>Name (optional):</label>
            <input
              type="text"
              value={createForm.name}
              onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
              placeholder="auto-generated if empty"
            />
          </div>
          <div className="form-group">
            <label>Type:</label>
            <select
              value={createForm.type}
              onChange={(e) => setCreateForm({...createForm, type: e.target.value})}
            >
              <option value="full">Full Backup</option>
              <option value="incremental">Incremental Backup</option>
            </select>
          </div>
          <div className="form-group">
            <label>Encryption Password (optional):</label>
            <input
              type="password"
              value={createForm.encryptionPassword}
              onChange={(e) => setCreateForm({...createForm, encryptionPassword: e.target.value})}
              placeholder="leave empty for no encryption"
            />
          </div>
          <div className="form-actions">
            <button onClick={createBackup} disabled={loading} className="btn-primary">
              {loading ? 'Creating...' : 'Create Backup'}
            </button>
            <button onClick={() => setShowCreateForm(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="status-panel">
        <h3>System Status</h3>
        <div className="status-grid">
          <div className="status-item">
            <span className="label">Scheduler:</span>
            <span className={`value ${status.status === 'running' ? 'active' : 'inactive'}`}>
              {status.status || 'unknown'}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Cloud Storage:</span>
            <span className={`value ${status.cloud_storage === 'enabled' ? 'active' : 'inactive'}`}>
              {status.cloud_storage || 'disabled'}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Encryption:</span>
            <span className={`value ${status.encryption === 'enabled' ? 'active' : 'inactive'}`}>
              {status.encryption || 'disabled'}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Incremental:</span>
            <span className={`value ${status.incremental_backups === 'enabled' ? 'active' : 'inactive'}`}>
              {status.incremental_backups || 'disabled'}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Notifications:</span>
            <span className={`value ${status.notifications === 'enabled' ? 'active' : 'inactive'}`}>
              {status.notifications || 'disabled'}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Last Full Backup:</span>
            <span className="value">{status.last_full_backup || 'none'}</span>
          </div>
        </div>
      </div>

      <div className="backups-list">
        <h3>Available Backups ({backups.length})</h3>
        {backups.length === 0 ? (
          <p>No backups found.</p>
        ) : (
          <div className="backups-table">
            <div className="table-header">
              <div>Name</div>
              <div>Size</div>
              <div>Type</div>
              <div>Location</div>
              <div>Created</div>
              <div>Status</div>
              <div>Actions</div>
            </div>
            {backups.map((backup, index) => (
              <div key={index} className="table-row">
                <div className="backup-name">
                  {backup.filename}
                  {backup.encrypted && <span className="encrypted-icon" title="Encrypted">🔒</span>}
                </div>
                <div>{formatSize(backup.size)}</div>
                <div>{backup.type || 'unknown'}</div>
                <div>{backup.location || 'local'}</div>
                <div>{formatDate(backup.created)}</div>
                <div>
                  <span className={`status ${backup.checksum_valid ? 'valid' : 'invalid'}`}>
                    {backup.checksum_valid ? '✓ Valid' : '✗ Invalid'}
                  </span>
                </div>
                <div className="actions">
                  <button
                    onClick={() => restoreBackup(backup.filename)}
                    disabled={loading}
                    className="btn-small"
                    title="Restore this backup"
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => verifyBackup(backup.filename)}
                    disabled={loading}
                    className="btn-small"
                    title="Verify backup integrity"
                  >
                    Verify
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default BackupManager;