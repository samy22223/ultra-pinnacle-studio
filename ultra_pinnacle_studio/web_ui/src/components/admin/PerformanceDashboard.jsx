import React, { useState, useEffect } from 'react'
import axios from 'axios'

const PerformanceDashboard = () => {
  const [metrics, setMetrics] = useState(null)
  const [performanceStats, setPerformanceStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeRange, setTimeRange] = useState('1h')

  useEffect(() => {
    fetchPerformanceData()
    const interval = setInterval(fetchPerformanceData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [timeRange])

  const fetchPerformanceData = async () => {
    try {
      const token = localStorage.getItem('token')
      const [metricsRes, statsRes] = await Promise.all([
        axios.get('http://localhost:8000/metrics/performance', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get('http://localhost:8000/logging/stats', {
          headers: { Authorization: `Bearer ${token}` }
        })
      ])

      setMetrics(metricsRes.data)
      setPerformanceStats(statsRes.data)
    } catch (err) {
      console.error('Error fetching performance data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDuration = (ms) => {
    if (ms < 1000) return `${ms.toFixed(2)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const getPerformanceColor = (value, thresholds) => {
    if (value <= thresholds.good) return 'good'
    if (value <= thresholds.warning) return 'warning'
    return 'critical'
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading performance data...</p>
      </div>
    )
  }

  return (
    <div className="performance-dashboard">
      <div className="admin-section-header">
        <h2>Performance Dashboard</h2>
        <p>Monitor system performance and analytics</p>
      </div>

      {/* Time Range Selector */}
      <div className="performance-controls">
        <div className="time-range-selector">
          <label>Time Range:</label>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="admin-select"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
        <button onClick={fetchPerformanceData} className="admin-btn secondary">
          Refresh
        </button>
      </div>

      {/* Performance Metrics Grid */}
      <div className="performance-grid">
        {/* System Performance */}
        <div className="performance-card">
          <h3>System Performance</h3>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">CPU Usage</span>
              <span className={`metric-value ${getPerformanceColor(metrics?.cpu_percent || 0, { good: 50, warning: 80 })}`}>
                {metrics?.cpu_percent || 0}%
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Memory Usage</span>
              <span className={`metric-value ${getPerformanceColor(metrics?.memory_percent || 0, { good: 60, warning: 85 })}`}>
                {metrics?.memory_percent || 0}%
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Disk Usage</span>
              <span className={`metric-value ${getPerformanceColor(metrics?.disk_percent || 0, { good: 70, warning: 90 })}`}>
                {metrics?.disk_percent || 0}%
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Active Connections</span>
              <span className="metric-value info">
                {metrics?.active_connections || 0}
              </span>
            </div>
          </div>
        </div>

        {/* API Performance */}
        <div className="performance-card">
          <h3>API Performance</h3>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Avg Response Time</span>
              <span className={`metric-value ${getPerformanceColor(performanceStats?.performance_stats?.avg_response_time || 0, { good: 500, warning: 2000 })}`}>
                {formatDuration(performanceStats?.performance_stats?.avg_response_time || 0)}
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Total Requests</span>
              <span className="metric-value info">
                {performanceStats?.aggregated_stats?.total_requests || 0}
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Error Rate</span>
              <span className={`metric-value ${getPerformanceColor(performanceStats?.aggregated_stats?.error_rate || 0, { good: 1, warning: 5 })}`}>
                {(performanceStats?.aggregated_stats?.error_rate || 0).toFixed(2)}%
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Success Rate</span>
              <span className={`metric-value ${getPerformanceColor(100 - (performanceStats?.aggregated_stats?.error_rate || 0), { good: 99, warning: 95 })}`}>
                {(100 - (performanceStats?.aggregated_stats?.error_rate || 0)).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Operation Performance */}
        <div className="performance-card full-width">
          <h3>Operation Performance</h3>
          <div className="operations-table">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Operation</th>
                  <th>Count</th>
                  <th>Avg Time</th>
                  <th>Min Time</th>
                  <th>Max Time</th>
                  <th>Success Rate</th>
                </tr>
              </thead>
              <tbody>
                {performanceStats?.performance_stats?.operations &&
                  Object.entries(performanceStats.performance_stats.operations).map(([op, stats]) => (
                    <tr key={op}>
                      <td>{op}</td>
                      <td>{stats.count}</td>
                      <td>{formatDuration(stats.avg_time)}</td>
                      <td>{formatDuration(stats.min_time)}</td>
                      <td>{formatDuration(stats.max_time)}</td>
                      <td>
                        <span className={`metric-value ${getPerformanceColor(stats.success_rate, { good: 99, warning: 95 })}`}>
                          {stats.success_rate.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Performance Charts Placeholder */}
      <div className="performance-charts">
        <div className="chart-placeholder">
          <h4>Response Time Trend</h4>
          <div className="chart-area">
            <p>Chart visualization would be implemented here</p>
            <small>Integration with charting library (Chart.js, D3.js, etc.)</small>
          </div>
        </div>

        <div className="chart-placeholder">
          <h4>Resource Usage Over Time</h4>
          <div className="chart-area">
            <p>Real-time resource monitoring charts</p>
            <small>CPU, Memory, Disk, Network usage trends</small>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PerformanceDashboard