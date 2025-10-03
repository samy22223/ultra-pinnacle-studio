import React, { useState, useEffect } from 'react'
import axios from 'axios'

const BackupManagement = () => {
  const [backups, setBackups] = useState([])
  const [backupStatus, setBackupStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [creatingBackup, setCreatingBackup] = useState(false)
  const [restoringBackup, setRestoringBackup] = useState(false)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  useEffect(() => {
    fetchBackups()
    fetchBackupStatus()
  }, [])

  const fetchBackups = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/backup/list', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setBackups(response.data)
    } catch (err) {
      console.error('Error fetching backups:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchBackupStatus = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/backup/status', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setBackupStatus(response.data)
    } catch (err) {
      console.error('Error fetching backup status:', err)
    }
  }

  const handleCreateBackup = async (backupData) => {
    try {
      setCreatingBackup(true)
      const token = localStorage.getItem('token')
      const response = await axios.post('http://localhost:8000/backup/create', backupData, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert(`Backup created successfully: ${response.data.backup_path}`)
      await fetchBackups()
      setShowCreateModal(false)
    } catch (err) {
      console.error('Error creating backup:', err)
      alert(`Failed to create backup: ${err.message}`)
    } finally {
      setCreatingBackup(false)
    }
  }

  const handleRestoreBackup = async (backupName) => {
    if (!window.confirm(`Are you sure you want to restore from backup "${backupName}"? This may overwrite current data.`)) {
      return
    }

    try {
      setRestoringBackup(true)
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/backup/restore', {
        backup_name: backupName
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Backup restored successfully')
      await fetchBackups()
    } catch (err) {
      console.error('Error restoring backup:', err)
      alert(`Failed to restore backup: ${err.message}`)
    } finally {
      setRestoringBackup(false)
    }
  }

  const handleDeleteBackup = async (backupName) => {
    if (!window.confirm(`Are you sure you want to delete backup "${backupName}"?`)) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      await axios.delete(`http://localhost:8000/backup/delete/${backupName}`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Backup deleted successfully')
      await fetchBackups()
    } catch (err) {
      console.error('Error deleting backup:', err)
      alert(`Failed to delete backup: ${err.message}`)
    }
  }

  const handleCleanupBackups = async () => {
    if (!window.confirm('Are you sure you want to clean up old backups? This will delete backups older than 30 days.')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      const response = await axios.delete('http://localhost:8000/backup/cleanup', {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert(response.data.message)
      await fetchBackups()
    } catch (err) {
      console.error('Error cleaning up backups:', err)
      alert(`Failed to cleanup backups: ${err.message}`)
    }
  }

  const handleSchedulerAction = async (action) => {
    try {
      const token = localStorage.getItem('token')
      const endpoint = action === 'start' ? 'start' : 'stop'
      await axios.post(`http://localhost:8000/backup/scheduler/${endpoint}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert(`Backup scheduler ${action}ed successfully`)
      await fetchBackupStatus()
    } catch (err) {
      console.error(`Error ${action}ing backup scheduler:`, err)
      alert(`Failed to ${action} backup scheduler: ${err.message}`)
    }
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A'
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading backup management...</p>
      </div>
    )
  }

  return (
    <div className="backup-management">
      <div className="admin-section-header">
        <h2>Backup & Restore Management</h2>
        <p>Create, manage, and restore system backups</p>
      </div>

      {/* Backup Status */}
      {backupStatus && (
        <div className="backup-status-card">
          <h3>Backup System Status</h3>
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Status:</span>
              <span className={`status-value ${backupStatus.status}`}>
                {backupStatus.status}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Cloud Storage:</span>
              <span className={`status-value ${backupStatus.cloud_storage}`}>
                {backupStatus.cloud_storage}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Encryption:</span>
              <span className={`status-value ${backupStatus.encryption}`}>
                {backupStatus.encryption}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Incremental Backups:</span>
              <span className={`status-value ${backupStatus.incremental_backups}`}>
                {backupStatus.incremental_backups}
              </span>
            </div>
          </div>

          <div className="scheduler-controls">
            <h4>Automated Backup Scheduler</h4>
            <div className="scheduler-actions">
              <button
                onClick={() => handleSchedulerAction('start')}
                className="admin-btn small success"
                disabled={backupStatus.status === 'running'}
              >
                Start Scheduler
              </button>
              <button
                onClick={() => handleSchedulerAction('stop')}
                className="admin-btn small warning"
                disabled={backupStatus.status === 'stopped'}
              >
                Stop Scheduler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="backup-actions">
        <button
          onClick={() => setShowCreateModal(true)}
          className="admin-btn primary"
          disabled={creatingBackup}
        >
          {creatingBackup ? 'Creating...' : 'Create New Backup'}
        </button>
        <button
          onClick={handleCleanupBackups}
          className="admin-btn warning"
        >
          Cleanup Old Backups
        </button>
        <button
          onClick={fetchBackups}
          className="admin-btn secondary"
        >
          Refresh List
        </button>
      </div>

      {/* Backups List */}
      <div className="backups-table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Type</th>
              <th>Size</th>
              <th>Created</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {backups.map(backup => (
              <tr key={backup.filename}>
                <td>{backup.filename}</td>
                <td>
                  <span className={`backup-type ${backup.backup_type}`}>
                    {backup.backup_type}
                  </span>
                </td>
                <td>{formatFileSize(backup.size)}</td>
                <td>{new Date(backup.created_at).toLocaleString()}</td>
                <td>
                  <span className={`backup-status ${backup.checksum_valid ? 'valid' : 'invalid'}`}>
                    {backup.checksum_valid ? 'Valid' : 'Corrupted'}
                  </span>
                </td>
                <td>
                  <div className="action-buttons">
                    <button
                      onClick={() => handleRestoreBackup(backup.filename)}
                      className="admin-btn small success"
                      disabled={restoringBackup}
                    >
                      Restore
                    </button>
                    <button
                      onClick={() => handleDeleteBackup(backup.filename)}
                      className="admin-btn small danger"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {backups.length === 0 && (
        <div className="no-backups">
          <p>No backups found</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="admin-btn primary"
          >
            Create Your First Backup
          </button>
        </div>
      )}

      {/* Create Backup Modal */}
      {showCreateModal && (
        <CreateBackupModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateBackup}
          creating={creatingBackup}
        />
      )}
    </div>
  )
}

// Create Backup Modal Component
const CreateBackupModal = ({ onClose, onCreate, creating }) => {
  const [backupData, setBackupData] = useState({
    name: '',
    backup_type: 'full',
    encryption_password: ''
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setBackupData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onCreate(backupData)
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Create New Backup</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="name">Backup Name (optional):</label>
            <input
              type="text"
              id="name"
              name="name"
              value={backupData.name}
              onChange={handleChange}
              placeholder="e.g., weekly_backup_2024"
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="backup_type">Backup Type:</label>
            <select
              id="backup_type"
              name="backup_type"
              value={backupData.backup_type}
              onChange={handleChange}
              className="admin-select"
            >
              <option value="full">Full Backup</option>
              <option value="incremental">Incremental Backup</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="encryption_password">Encryption Password (optional):</label>
            <input
              type="password"
              id="encryption_password"
              name="encryption_password"
              value={backupData.encryption_password}
              onChange={handleChange}
              placeholder="Leave empty for no encryption"
              className="admin-input"
            />
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary" disabled={creating}>
            Cancel
          </button>
          <button onClick={handleSubmit} className="admin-btn primary" disabled={creating}>
            {creating ? 'Creating Backup...' : 'Create Backup'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default BackupManagement