import React, { useState, useEffect } from 'react'
import axios from 'axios'

const APIManagement = () => {
  const [rateLimitConfigs, setRateLimitConfigs] = useState([])
  const [endpointLimits, setEndpointLimits] = useState([])
  const [rateLimitStats, setRateLimitStats] = useState({})
  const [blockedIPs, setBlockedIPs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedConfig, setSelectedConfig] = useState(null)
  const [selectedEndpoint, setSelectedEndpoint] = useState(null)
  const [showCreateConfig, setShowCreateConfig] = useState(false)
  const [showCreateEndpoint, setShowCreateEndpoint] = useState(false)

  useEffect(() => {
    fetchAPIData()
  }, [])

  const fetchAPIData = async () => {
    try {
      const token = localStorage.getItem('token')
      const [configsRes, endpointsRes, statsRes, blockedRes] = await Promise.all([
        axios.get('http://localhost:8000/admin/rate-limits/configs', { headers: { Authorization: `Bearer ${token}` } }),
        axios.get('http://localhost:8000/admin/rate-limits/endpoints', { headers: { Authorization: `Bearer ${token}` } }),
        axios.get('http://localhost:8000/admin/rate-limits/stats', { headers: { Authorization: `Bearer ${token}` } }),
        axios.get('http://localhost:8000/security/blocked-ips', { headers: { Authorization: `Bearer ${token}` } })
      ])

      setRateLimitConfigs(configsRes.data || [])
      setEndpointLimits(endpointsRes.data || [])
      setRateLimitStats(statsRes.data || {})
      setBlockedIPs(blockedRes.data || [])
    } catch (err) {
      console.error('Error fetching API data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateConfig = async (configData) => {
    try {
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/admin/rate-limits/configs', configData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Rate limit configuration created successfully')
      setShowCreateConfig(false)
      await fetchAPIData()
    } catch (err) {
      console.error('Error creating config:', err)
      alert(`Failed to create configuration: ${err.message}`)
    }
  }

  const handleUpdateConfig = async (configId, configData) => {
    try {
      const token = localStorage.getItem('token')
      await axios.put(`http://localhost:8000/admin/rate-limits/configs/${configId}`, configData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Rate limit configuration updated successfully')
      setSelectedConfig(null)
      await fetchAPIData()
    } catch (err) {
      console.error('Error updating config:', err)
      alert(`Failed to update configuration: ${err.message}`)
    }
  }

  const handleCreateEndpointLimit = async (endpointData) => {
    try {
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/admin/rate-limits/endpoints', endpointData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Endpoint rate limit created successfully')
      setShowCreateEndpoint(false)
      await fetchAPIData()
    } catch (err) {
      console.error('Error creating endpoint limit:', err)
      alert(`Failed to create endpoint limit: ${err.message}`)
    }
  }

  const handleClearCache = async () => {
    if (!window.confirm('Are you sure you want to clear all rate limit caches? This will reset all counters.')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/admin/rate-limits/clear-cache', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Rate limit cache cleared successfully')
    } catch (err) {
      console.error('Error clearing cache:', err)
      alert(`Failed to clear cache: ${err.message}`)
    }
  }

  const handleUnblockIP = async (ip) => {
    if (!window.confirm(`Are you sure you want to unblock IP ${ip}?`)) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      await axios.post('http://localhost:8000/security/unblock-ip', { ip_address: ip }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert(`IP ${ip} has been unblocked`)
      await fetchAPIData()
    } catch (err) {
      console.error('Error unblocking IP:', err)
      alert(`Failed to unblock IP: ${err.message}`)
    }
  }

  const getMethodColor = (method) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'success'
      case 'POST': return 'primary'
      case 'PUT': return 'warning'
      case 'DELETE': return 'danger'
      default: return 'secondary'
    }
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading rate limiting management...</p>
      </div>
    )
  }

  return (
    <div className="rate-limit-management">
      <div className="admin-section-header">
        <h2>Rate Limiting Management</h2>
        <p>Configure and monitor API rate limits, user tiers, and endpoint restrictions</p>
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
          className={`admin-tab ${activeTab === 'configs' ? 'active' : ''}`}
          onClick={() => setActiveTab('configs')}
        >
          Configurations
        </button>
        <button
          className={`admin-tab ${activeTab === 'endpoints' ? 'active' : ''}`}
          onClick={() => setActiveTab('endpoints')}
        >
          Endpoint Limits
        </button>
        <button
          className={`admin-tab ${activeTab === 'monitoring' ? 'active' : ''}`}
          onClick={() => setActiveTab('monitoring')}
        >
          Monitoring
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="rate-limit-overview">
          {/* Statistics Cards */}
          <div className="api-stats">
            <div className="stat-card">
              <h4>Total Configurations</h4>
              <span className="stat-number">{rateLimitConfigs.length}</span>
            </div>
            <div className="stat-card">
              <h4>Endpoint Limits</h4>
              <span className="stat-number">{endpointLimits.length}</span>
            </div>
            <div className="stat-card">
              <h4>Total Requests (24h)</h4>
              <span className="stat-number">{rateLimitStats.total_requests || 0}</span>
            </div>
            <div className="stat-card">
              <h4>Rate Limit Violations (24h)</h4>
              <span className="stat-number">{rateLimitStats.rate_limit_violations || 0}</span>
            </div>
            <div className="stat-card">
              <h4>Violation Rate</h4>
              <span className="stat-number">
                {rateLimitStats.total_requests ?
                  `${((rateLimitStats.rate_limit_violations || 0) / rateLimitStats.total_requests * 100).toFixed(2)}%` :
                  '0%'
                }
              </span>
            </div>
            <div className="stat-card">
              <h4>Blocked IPs</h4>
              <span className="stat-number">{blockedIPs.length}</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h3>Quick Actions</h3>
            <div className="action-buttons">
              <button
                onClick={() => setShowCreateConfig(true)}
                className="admin-btn primary"
              >
                Create Configuration
              </button>
              <button
                onClick={() => setShowCreateEndpoint(true)}
                className="admin-btn secondary"
              >
                Add Endpoint Limit
              </button>
              <button
                onClick={handleClearCache}
                className="admin-btn warning"
              >
                Clear Cache
              </button>
            </div>
          </div>

          {/* Top Violators */}
          {rateLimitStats.top_violators && rateLimitStats.top_violators.length > 0 && (
            <div className="top-violators">
              <h3>Top Violators (24h)</h3>
              <div className="violators-list">
                {rateLimitStats.top_violators.map((violator, index) => (
                  <div key={index} className="violator-item">
                    <span className="ip-address">{violator.ip}</span>
                    <span className="violation-count">{violator.violations} violations</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Configurations Tab */}
      {activeTab === 'configs' && (
        <div className="rate-limit-configs">
          <div className="section-header">
            <h3>Rate Limit Configurations</h3>
            <button
              onClick={() => setShowCreateConfig(true)}
              className="admin-btn primary"
            >
              Create Configuration
            </button>
          </div>

          <div className="configs-table">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>User Type</th>
                  <th>Requests/Min</th>
                  <th>Requests/Hour</th>
                  <th>Requests/Day</th>
                  <th>Burst Limit</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rateLimitConfigs.map((config) => (
                  <tr key={config.id}>
                    <td>{config.name}</td>
                    <td>{config.user_type_id || 'Global'}</td>
                    <td>{config.requests_per_minute}</td>
                    <td>{config.requests_per_hour}</td>
                    <td>{config.requests_per_day}</td>
                    <td>{config.burst_limit}</td>
                    <td>
                      <button
                        onClick={() => setSelectedConfig(config)}
                        className="admin-btn small secondary"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Endpoints Tab */}
      {activeTab === 'endpoints' && (
        <div className="endpoint-limits">
          <div className="section-header">
            <h3>Endpoint-Specific Limits</h3>
            <button
              onClick={() => setShowCreateEndpoint(true)}
              className="admin-btn primary"
            >
              Add Endpoint Limit
            </button>
          </div>

          <div className="endpoints-table">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Endpoint Pattern</th>
                  <th>Method</th>
                  <th>Requests/Min</th>
                  <th>Requests/Hour</th>
                  <th>Burst Limit</th>
                  <th>Priority</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {endpointLimits.map((limit) => (
                  <tr key={limit.id}>
                    <td className="endpoint-pattern">{limit.endpoint_pattern}</td>
                    <td><span className={`method-badge ${getMethodColor(limit.method)}`}>{limit.method}</span></td>
                    <td>{limit.requests_per_minute}</td>
                    <td>{limit.requests_per_hour}</td>
                    <td>{limit.burst_limit}</td>
                    <td>{limit.priority}</td>
                    <td>{limit.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Monitoring Tab */}
      {activeTab === 'monitoring' && (
        <div className="rate-limit-monitoring">
          <h3>Rate Limiting Analytics</h3>

          {/* Top Endpoints */}
          {rateLimitStats.top_endpoints && rateLimitStats.top_endpoints.length > 0 && (
            <div className="top-endpoints">
              <h4>Most Active Endpoints (24h)</h4>
              <div className="endpoints-list">
                {rateLimitStats.top_endpoints.map((endpoint, index) => (
                  <div key={index} className="endpoint-item">
                    <span className="endpoint-path">{endpoint.endpoint}</span>
                    <span className="request-count">{endpoint.requests} requests</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Blocked IPs */}
          <div className="blocked-ips">
            <h4>Blocked IP Addresses</h4>
            {blockedIPs.length > 0 ? (
              <div className="blocked-ips-list">
                {blockedIPs.map(ip => (
                  <div key={ip} className="blocked-ip-item">
                    <span className="ip-address">{ip}</span>
                    <button
                      onClick={() => handleUnblockIP(ip)}
                      className="admin-btn small success"
                    >
                      Unblock
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-blocked-ips">No IP addresses are currently blocked</p>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreateConfig && (
        <CreateConfigModal
          onClose={() => setShowCreateConfig(false)}
          onSave={handleCreateConfig}
        />
      )}

      {selectedConfig && (
        <EditConfigModal
          config={selectedConfig}
          onClose={() => setSelectedConfig(null)}
          onSave={(data) => handleUpdateConfig(selectedConfig.id, data)}
        />
      )}

      {showCreateEndpoint && (
        <CreateEndpointModal
          onClose={() => setShowCreateEndpoint(false)}
          onSave={handleCreateEndpointLimit}
        />
      )}
    </div>
  )
}

// Create Configuration Modal
const CreateConfigModal = ({ onClose, onSave }) => {
  const [config, setConfig] = useState({
    name: '',
    user_type_id: '',
    requests_per_minute: 60,
    requests_per_hour: 1000,
    requests_per_day: 5000,
    burst_limit: 10,
    description: ''
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setConfig(prev => ({
      ...prev,
      [name]: name.includes('requests') || name === 'burst_limit' || name === 'user_type_id' ?
        (value ? parseInt(value) : '') : value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(config)
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Create Rate Limit Configuration</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="name">Configuration Name:</label>
            <input
              type="text"
              id="name"
              name="name"
              value={config.name}
              onChange={handleChange}
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="user_type_id">User Type ID (optional):</label>
            <input
              type="number"
              id="user_type_id"
              name="user_type_id"
              value={config.user_type_id}
              onChange={handleChange}
              min="1"
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_minute">Requests per Minute:</label>
            <input
              type="number"
              id="requests_per_minute"
              name="requests_per_minute"
              value={config.requests_per_minute}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_hour">Requests per Hour:</label>
            <input
              type="number"
              id="requests_per_hour"
              name="requests_per_hour"
              value={config.requests_per_hour}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_day">Requests per Day:</label>
            <input
              type="number"
              id="requests_per_day"
              name="requests_per_day"
              value={config.requests_per_day}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="burst_limit">Burst Limit:</label>
            <input
              type="number"
              id="burst_limit"
              name="burst_limit"
              value={config.burst_limit}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description:</label>
            <textarea
              id="description"
              name="description"
              value={config.description}
              onChange={handleChange}
              className="admin-textarea"
            />
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Create Configuration</button>
        </div>
      </div>
    </div>
  )
}

// Edit Configuration Modal
const EditConfigModal = ({ config, onClose, onSave }) => {
  const [configData, setConfigData] = useState({
    name: config.name,
    requests_per_minute: config.requests_per_minute,
    requests_per_hour: config.requests_per_hour,
    requests_per_day: config.requests_per_day,
    burst_limit: config.burst_limit,
    description: config.description || ''
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setConfigData(prev => ({
      ...prev,
      [name]: name.includes('requests') || name === 'burst_limit' ?
        (value ? parseInt(value) : '') : value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(configData)
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Edit Rate Limit Configuration</h3>
          <p>{config.name}</p>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="name">Configuration Name:</label>
            <input
              type="text"
              id="name"
              name="name"
              value={configData.name}
              onChange={handleChange}
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_minute">Requests per Minute:</label>
            <input
              type="number"
              id="requests_per_minute"
              name="requests_per_minute"
              value={configData.requests_per_minute}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_hour">Requests per Hour:</label>
            <input
              type="number"
              id="requests_per_hour"
              name="requests_per_hour"
              value={configData.requests_per_hour}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_day">Requests per Day:</label>
            <input
              type="number"
              id="requests_per_day"
              name="requests_per_day"
              value={configData.requests_per_day}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="burst_limit">Burst Limit:</label>
            <input
              type="number"
              id="burst_limit"
              name="burst_limit"
              value={configData.burst_limit}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description:</label>
            <textarea
              id="description"
              name="description"
              value={configData.description}
              onChange={handleChange}
              className="admin-textarea"
            />
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Update Configuration</button>
        </div>
      </div>
    </div>
  )
}

// Create Endpoint Limit Modal
const CreateEndpointModal = ({ onClose, onSave }) => {
  const [endpointData, setEndpointData] = useState({
    endpoint_pattern: '',
    method: '*',
    requests_per_minute: 30,
    requests_per_hour: 500,
    burst_limit: 5,
    priority: 0,
    description: ''
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setEndpointData(prev => ({
      ...prev,
      [name]: name.includes('requests') || name === 'burst_limit' || name === 'priority' ?
        (value ? parseInt(value) : '') : value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(endpointData)
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Create Endpoint Rate Limit</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="endpoint_pattern">Endpoint Pattern:</label>
            <input
              type="text"
              id="endpoint_pattern"
              name="endpoint_pattern"
              value={endpointData.endpoint_pattern}
              onChange={handleChange}
              placeholder="/api/example or /api/*"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="method">HTTP Method:</label>
            <select
              id="method"
              name="method"
              value={endpointData.method}
              onChange={handleChange}
              className="admin-select"
            >
              <option value="*">All Methods</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
              <option value="PATCH">PATCH</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_minute">Requests per Minute:</label>
            <input
              type="number"
              id="requests_per_minute"
              name="requests_per_minute"
              value={endpointData.requests_per_minute}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="requests_per_hour">Requests per Hour:</label>
            <input
              type="number"
              id="requests_per_hour"
              name="requests_per_hour"
              value={endpointData.requests_per_hour}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="burst_limit">Burst Limit:</label>
            <input
              type="number"
              id="burst_limit"
              name="burst_limit"
              value={endpointData.burst_limit}
              onChange={handleChange}
              min="1"
              required
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="priority">Priority:</label>
            <input
              type="number"
              id="priority"
              name="priority"
              value={endpointData.priority}
              onChange={handleChange}
              min="0"
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description:</label>
            <textarea
              id="description"
              name="description"
              value={endpointData.description}
              onChange={handleChange}
              className="admin-textarea"
            />
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Create Endpoint Limit</button>
        </div>
      </div>
    </div>
  )
}

export default APIManagement