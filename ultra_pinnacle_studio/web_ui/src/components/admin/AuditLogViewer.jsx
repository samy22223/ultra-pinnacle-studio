import React, { useState, useEffect } from 'react'
import axios from 'axios'

const AuditLogViewer = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    hours: 24,
    event_type: '',
    user: '',
    action: ''
  })

  useEffect(() => {
    fetchAuditLogs()
  }, [filters])

  const fetchAuditLogs = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const params = {
        hours: filters.hours
      }
      if (filters.event_type) params.event_type = filters.event_type

      const response = await axios.get('http://localhost:8000/security/audit-log', {
        headers: { Authorization: `Bearer ${token}` },
        params
      })
      setLogs(response.data.logs || [])
    } catch (err) {
      console.error('Error fetching audit logs:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const getActionColor = (action) => {
    if (action.includes('login') || action.includes('create')) return 'success'
    if (action.includes('delete') || action.includes('ban')) return 'danger'
    if (action.includes('update') || action.includes('change')) return 'warning'
    return 'info'
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading audit logs...</p>
      </div>
    )
  }

  return (
    <div className="audit-log-viewer">
      <div className="admin-section-header">
        <h2>Audit Log Viewer</h2>
        <p>View security events and system activities</p>
      </div>

      {/* Filters */}
      <div className="audit-filters">
        <div className="filter-group">
          <label>Time Range:</label>
          <select
            value={filters.hours}
            onChange={(e) => handleFilterChange('hours', parseInt(e.target.value))}
            className="admin-select"
          >
            <option value={1}>Last Hour</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
            <option value={720}>Last 30 Days</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Event Type:</label>
          <select
            value={filters.event_type}
            onChange={(e) => handleFilterChange('event_type', e.target.value)}
            className="admin-select"
          >
            <option value="">All Events</option>
            <option value="authentication">Authentication</option>
            <option value="authorization">Authorization</option>
            <option value="data_access">Data Access</option>
            <option value="admin_action">Admin Action</option>
            <option value="system">System</option>
          </select>
        </div>

        <button onClick={fetchAuditLogs} className="admin-btn secondary">
          Refresh
        </button>
      </div>

      {/* Audit Logs Table */}
      <div className="audit-logs-table">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Details</th>
              <th>IP Address</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, index) => (
              <tr key={index}>
                <td>{formatTimestamp(log.timestamp)}</td>
                <td>{log.user || 'System'}</td>
                <td>
                  <span className={`action-badge ${getActionColor(log.action)}`}>
                    {log.action}
                  </span>
                </td>
                <td>{log.resource || '-'}</td>
                <td>
                  {log.details && (
                    <details>
                      <summary>View Details</summary>
                      <pre className="log-details">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </details>
                  )}
                </td>
                <td>{log.ip_address || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logs.length === 0 && (
        <div className="no-logs">
          <p>No audit logs found for the selected time range</p>
        </div>
      )}

      {/* Summary Statistics */}
      <div className="audit-summary">
        <div className="summary-stats">
          <div className="stat-card">
            <h4>Total Events</h4>
            <span className="stat-number">{logs.length}</span>
          </div>
          <div className="stat-card">
            <h4>Authentication Events</h4>
            <span className="stat-number">
              {logs.filter(log => log.action.includes('login') || log.action.includes('auth')).length}
            </span>
          </div>
          <div className="stat-card">
            <h4>Admin Actions</h4>
            <span className="stat-number">
              {logs.filter(log => log.action.includes('admin') || log.action.includes('user')).length}
            </span>
          </div>
          <div className="stat-card">
            <h4>Error Events</h4>
            <span className="stat-number">
              {logs.filter(log => log.action.includes('error') || log.action.includes('fail')).length}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AuditLogViewer