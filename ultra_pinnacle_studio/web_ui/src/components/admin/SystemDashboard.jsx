import React, { useState, useEffect } from 'react'
import axios from 'axios'

const SystemDashboard = () => {
  const [healthData, setHealthData] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const token = localStorage.getItem('token')
        const headers = { Authorization: `Bearer ${token}` }

        const [healthRes, metricsRes] = await Promise.all([
          axios.get('http://localhost:8000/health', { headers }),
          axios.get('http://localhost:8000/metrics/system', { headers })
        ])

        setHealthData(healthRes.data)
        setMetrics(metricsRes.data)
      } catch (err) {
        console.error('Error fetching dashboard data:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()

    // Refresh data every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="admin-dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading system dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="admin-dashboard-error">
        <h3>Dashboard Error</h3>
        <p>Failed to load dashboard data: {error}</p>
      </div>
    )
  }

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'green'
      case 'warning': return 'yellow'
      case 'unhealthy': return 'red'
      default: return 'gray'
    }
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-dashboard-header">
        <h2>System Dashboard</h2>
        <p className="admin-dashboard-subtitle">
          Real-time system health and performance monitoring
        </p>
      </div>

      {/* Health Overview */}
      <div className="admin-dashboard-grid">
        <div className="admin-dashboard-card">
          <h3>System Health</h3>
          <div className={`health-status ${getHealthStatusColor(healthData?.status)}`}>
            <span className="health-indicator"></span>
            <span className="health-text">{healthData?.status || 'Unknown'}</span>
          </div>
          <div className="health-details">
            <p><strong>Timestamp:</strong> {healthData?.timestamp}</p>
            <p><strong>Models Loaded:</strong> {healthData?.models_loaded || 0}</p>
            <p><strong>Active Tasks:</strong> {healthData?.active_tasks || 0}</p>
          </div>
        </div>

        {/* Health Checks */}
        <div className="admin-dashboard-card">
          <h3>Health Checks</h3>
          <div className="health-checks">
            {healthData?.checks && Object.entries(healthData.checks).map(([check, data]) => (
              <div key={check} className={`health-check-item ${data.status}`}>
                <span className="check-name">{check}:</span>
                <span className="check-status">{data.status}</span>
                {data.details && <span className="check-details">({data.details})</span>}
              </div>
            ))}
          </div>
        </div>

        {/* System Metrics */}
        {metrics && (
          <div className="admin-dashboard-card">
            <h3>System Metrics</h3>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">CPU Usage:</span>
                <span className="metric-value">{metrics.cpu_percent || 'N/A'}%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Memory Usage:</span>
                <span className="metric-value">{metrics.memory_percent || 'N/A'}%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Disk Usage:</span>
                <span className="metric-value">{metrics.disk_percent || 'N/A'}%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Active Connections:</span>
                <span className="metric-value">{metrics.active_connections || 0}</span>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="admin-dashboard-card">
          <h3>Quick Actions</h3>
          <div className="quick-actions">
            <button className="admin-btn primary">Run Health Check</button>
            <button className="admin-btn secondary">Clear Cache</button>
            <button className="admin-btn warning">Restart Services</button>
            <button className="admin-btn danger">Emergency Stop</button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="admin-dashboard-card full-width">
        <h3>Recent System Activity</h3>
        <div className="activity-log">
          <div className="activity-item">
            <span className="activity-time">2 minutes ago</span>
            <span className="activity-message">User 'admin' logged in</span>
          </div>
          <div className="activity-item">
            <span className="activity-time">5 minutes ago</span>
            <span className="activity-message">Plugin 'ai-enhancer' enabled</span>
          </div>
          <div className="activity-item">
            <span className="activity-time">10 minutes ago</span>
            <span className="activity-message">System backup completed</span>
          </div>
          <div className="activity-item">
            <span className="activity-time">15 minutes ago</span>
            <span className="activity-message">Translation cache cleared</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemDashboard