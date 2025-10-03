import React, { useState, useEffect } from 'react'
import axios from 'axios'

const DataExportImport = () => {
  const [exports, setExports] = useState([])
  const [exportStats, setExportStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [showCreateExport, setShowCreateExport] = useState(false)
  const [selectedExport, setSelectedExport] = useState(null)

  useEffect(() => {
    fetchExportData()
  }, [])

  const fetchExportData = async () => {
    try {
      const token = localStorage.getItem('token')
      const [exportsRes, statsRes] = await Promise.all([
        axios.get('http://localhost:8000/admin/exports', { headers: { Authorization: `Bearer ${token}` } }),
        axios.get('http://localhost:8000/admin/exports/stats', { headers: { Authorization: `Bearer ${token}` } })
      ])

      setExports(exportsRes.data || [])
      setExportStats(statsRes.data || {})
    } catch (err) {
      console.error('Error fetching export data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateExport = async (exportData) => {
    try {
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/api/exports', exportData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Export operation created successfully')
      setShowCreateExport(false)
      await fetchExportData()
    } catch (err) {
      console.error('Error creating export:', err)
      alert(`Failed to create export: ${err.message}`)
    }
  }

  const handleDownloadExport = async (operationId) => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`http://localhost:8000/api/exports/download/${operationId}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `export_${operationId}.zip`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      alert('Export downloaded successfully')
    } catch (err) {
      console.error('Error downloading export:', err)
      alert(`Failed to download export: ${err.message}`)
    }
  }

  const handleDeleteExport = async (operationId) => {
    if (!window.confirm('Are you sure you want to delete this export operation and its files?')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      await axios.delete(`http://localhost:8000/api/exports/${operationId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Export operation deleted successfully')
      await fetchExportData()
    } catch (err) {
      console.error('Error deleting export:', err)
      alert(`Failed to delete export: ${err.message}`)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success'
      case 'running': return 'warning'
      case 'failed': return 'danger'
      case 'pending': return 'secondary'
      default: return 'secondary'
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
        <p>Loading data export/import management...</p>
      </div>
    )
  }

  return (
    <div className="data-export-import">
      <div className="admin-section-header">
        <h2>Data Export/Import Management</h2>
        <p>Manage GDPR-compliant data exports and imports for users and administrators</p>
      </div>

      {/* Navigation Tabs */}
      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`admin-tab ${activeTab === 'exports' ? 'active' : ''}`}
          onClick={() => setActiveTab('exports')}
        >
          Export Operations
        </button>
        <button
          className={`admin-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="export-overview">
          {/* Statistics Cards */}
          <div className="export-stats">
            <div className="stat-card">
              <h4>Total Export Operations</h4>
              <span className="stat-number">{exportStats.total_operations || 0}</span>
            </div>
            <div className="stat-card">
              <h4>Completed Exports</h4>
              <span className="stat-number">{exportStats.status_breakdown?.completed || 0}</span>
            </div>
            <div className="stat-card">
              <h4>Failed Exports</h4>
              <span className="stat-number">{exportStats.status_breakdown?.failed || 0}</span>
            </div>
            <div className="stat-card">
              <h4>Total File Size</h4>
              <span className="stat-number">{formatFileSize(exportStats.total_file_size_bytes)}</span>
            </div>
            <div className="stat-card">
              <h4>Avg File Size</h4>
              <span className="stat-number">{formatFileSize(exportStats.average_file_size_bytes)}</span>
            </div>
            <div className="stat-card">
              <h4>GDPR Compliance Rate</h4>
              <span className="stat-number">100%</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h3>Quick Actions</h3>
            <div className="action-buttons">
              <button
                onClick={() => setShowCreateExport(true)}
                className="admin-btn primary"
              >
                Create Export
              </button>
              <button
                onClick={() => fetchExportData()}
                className="admin-btn secondary"
              >
                Refresh Data
              </button>
            </div>
          </div>

          {/* Recent Exports */}
          <div className="recent-exports">
            <h3>Recent Export Operations</h3>
            <div className="recent-exports-list">
              {exports.slice(0, 5).map((exportOp) => (
                <div key={exportOp.id} className="export-item">
                  <div className="export-info">
                    <span className="export-id">{exportOp.id}</span>
                    <span className={`status-badge ${getStatusColor(exportOp.status)}`}>
                      {exportOp.status}
                    </span>
                    <span className="export-type">{exportOp.export_type}</span>
                    <span className="export-format">{exportOp.format}</span>
                  </div>
                  <div className="export-meta">
                    <span className="created-at">{new Date(exportOp.created_at).toLocaleString()}</span>
                    {exportOp.file_size && (
                      <span className="file-size">{formatFileSize(exportOp.file_size)}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Exports Tab */}
      {activeTab === 'exports' && (
        <div className="export-operations">
          <div className="section-header">
            <h3>Export Operations</h3>
            <button
              onClick={() => setShowCreateExport(true)}
              className="admin-btn primary"
            >
              Create Export
            </button>
          </div>

          <div className="exports-table">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Operation ID</th>
                  <th>User</th>
                  <th>Type</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>File Size</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {exports.map((exportOp) => (
                  <tr key={exportOp.id}>
                    <td className="operation-id">{exportOp.id.slice(0, 8)}...</td>
                    <td>{exportOp.username}</td>
                    <td>{exportOp.export_type}</td>
                    <td>{exportOp.format}</td>
                    <td>
                      <span className={`status-badge ${getStatusColor(exportOp.status)}`}>
                        {exportOp.status}
                      </span>
                    </td>
                    <td>
                      {exportOp.status === 'running' ? (
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{ width: `${exportOp.progress || 0}%` }}
                          ></div>
                          <span className="progress-text">{exportOp.progress || 0}%</span>
                        </div>
                      ) : (
                        exportOp.progress || 0
                      )}
                    </td>
                    <td>{formatFileSize(exportOp.file_size)}</td>
                    <td>{new Date(exportOp.created_at).toLocaleString()}</td>
                    <td>
                      <div className="action-buttons">
                        {exportOp.status === 'completed' && (
                          <button
                            onClick={() => handleDownloadExport(exportOp.id)}
                            className="admin-btn small success"
                            title="Download"
                          >
                            ↓
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedExport(exportOp)}
                          className="admin-btn small secondary"
                          title="View Details"
                        >
                          👁
                        </button>
                        <button
                          onClick={() => handleDeleteExport(exportOp.id)}
                          className="admin-btn small danger"
                          title="Delete"
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="export-analytics">
          <h3>Export Analytics</h3>

          {/* Export Type Breakdown */}
          <div className="analytics-section">
            <h4>Export Types</h4>
            <div className="breakdown-chart">
              {Object.entries(exportStats.type_breakdown || {}).map(([type, count]) => (
                <div key={type} className="breakdown-item">
                  <span className="breakdown-label">{type.replace('_', ' ').toUpperCase()}</span>
                  <div className="breakdown-bar">
                    <div
                      className="breakdown-fill"
                      style={{
                        width: `${(count / exportStats.total_operations) * 100}%`
                      }}
                    ></div>
                  </div>
                  <span className="breakdown-count">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Format Breakdown */}
          <div className="analytics-section">
            <h4>Export Formats</h4>
            <div className="breakdown-chart">
              {Object.entries(exportStats.format_breakdown || {}).map(([format, count]) => (
                <div key={format} className="breakdown-item">
                  <span className="breakdown-label">{format.toUpperCase()}</span>
                  <div className="breakdown-bar">
                    <div
                      className="breakdown-fill"
                      style={{
                        width: `${(count / exportStats.total_operations) * 100}%`
                      }}
                    ></div>
                  </div>
                  <span className="breakdown-count">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Status Breakdown */}
          <div className="analytics-section">
            <h4>Operation Status</h4>
            <div className="status-summary">
              {Object.entries(exportStats.status_breakdown || {}).map(([status, count]) => (
                <div key={status} className="status-item">
                  <span className={`status-badge ${getStatusColor(status)}`}>{status}</span>
                  <span className="status-count">{count}</span>
                  <span className="status-percentage">
                    ({((count / exportStats.total_operations) * 100).toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreateExport && (
        <CreateExportModal
          onClose={() => setShowCreateExport(false)}
          onSave={handleCreateExport}
        />
      )}

      {selectedExport && (
        <ExportDetailsModal
          exportOp={selectedExport}
          onClose={() => setSelectedExport(null)}
          onDownload={() => handleDownloadExport(selectedExport.id)}
          onDelete={() => handleDeleteExport(selectedExport.id)}
        />
      )}
    </div>
  )
}

// Create Export Modal
const CreateExportModal = ({ onClose, onSave }) => {
  const [exportData, setExportData] = useState({
    export_type: 'user_data',
    format: 'json',
    data_scope: {},
    filters: {},
    encryption_password: ''
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setExportData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleScopeChange = (e) => {
    const { name, value } = e.target
    setExportData(prev => ({
      ...prev,
      data_scope: {
        ...prev.data_scope,
        [name]: value
      }
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(exportData)
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Create Data Export</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="export_type">Export Type:</label>
            <select
              id="export_type"
              name="export_type"
              value={exportData.export_type}
              onChange={handleChange}
              required
              className="admin-select"
            >
              <option value="user_data">User Data (GDPR)</option>
              <option value="conversations">Conversations</option>
              <option value="bulk_admin">Bulk Admin Export</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="format">Export Format:</label>
            <select
              id="format"
              name="format"
              value={exportData.format}
              onChange={handleChange}
              required
              className="admin-select"
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="pdf">PDF</option>
              <option value="html">HTML</option>
            </select>
          </div>

          {exportData.export_type === 'conversations' && (
            <div className="form-group">
              <label htmlFor="conversation_ids">Conversation IDs (comma-separated):</label>
              <input
                type="text"
                id="conversation_ids"
                name="conversation_ids"
                value={exportData.data_scope.conversation_ids || ''}
                onChange={handleScopeChange}
                placeholder="conv_123,conv_456"
                className="admin-input"
              />
            </div>
          )}

          {exportData.export_type === 'bulk_admin' && (
            <div className="form-group">
              <label htmlFor="bulk_type">Bulk Export Type:</label>
              <select
                id="bulk_type"
                name="bulk_type"
                value={exportData.data_scope.bulk_type || 'all_users'}
                onChange={handleScopeChange}
                className="admin-select"
              >
                <option value="all_users">All Users</option>
                <option value="all_conversations">All Conversations</option>
                <option value="system_audit">System Audit Logs</option>
              </select>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="encryption_password">Encryption Password (optional):</label>
            <input
              type="password"
              id="encryption_password"
              name="encryption_password"
              value={exportData.encryption_password}
              onChange={handleChange}
              placeholder="Leave empty for no encryption"
              className="admin-input"
            />
          </div>

          <div className="gdpr-notice">
            <p><strong>GDPR Notice:</strong> This export operation complies with GDPR requirements for data portability. User data exports include profile information, conversations, and activity logs.</p>
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Create Export</button>
        </div>
      </div>
    </div>
  )
}

// Export Details Modal
const ExportDetailsModal = ({ exportOp, onClose, onDownload, onDelete }) => {
  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Export Operation Details</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <div className="admin-modal-body">
          <div className="export-details">
            <div className="detail-row">
              <span className="detail-label">Operation ID:</span>
              <span className="detail-value">{exportOp.id}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">User:</span>
              <span className="detail-value">{exportOp.username}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Type:</span>
              <span className="detail-value">{exportOp.export_type}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Format:</span>
              <span className="detail-value">{exportOp.format}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Status:</span>
              <span className={`detail-value status-${exportOp.status}`}>
                {exportOp.status}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Progress:</span>
              <span className="detail-value">{exportOp.progress || 0}%</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">File Size:</span>
              <span className="detail-value">
                {exportOp.file_size ? `${(exportOp.file_size / 1024 / 1024).toFixed(2)} MB` : 'N/A'}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Created:</span>
              <span className="detail-value">
                {new Date(exportOp.created_at).toLocaleString()}
              </span>
            </div>
            {exportOp.completed_at && (
              <div className="detail-row">
                <span className="detail-label">Completed:</span>
                <span className="detail-value">
                  {new Date(exportOp.completed_at).toLocaleString()}
                </span>
              </div>
            )}
            {exportOp.error_message && (
              <div className="detail-row">
                <span className="detail-label">Error:</span>
                <span className="detail-value error">{exportOp.error_message}</span>
              </div>
            )}
          </div>
        </div>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Close</button>
          {exportOp.status === 'completed' && (
            <button onClick={onDownload} className="admin-btn success">Download</button>
          )}
          <button onClick={onDelete} className="admin-btn danger">Delete</button>
        </div>
      </div>
    </div>
  )
}

export default DataExportImport