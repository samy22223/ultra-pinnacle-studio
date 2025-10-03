import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const Analytics = ({ token }) => {
  const [analyticsData, setAnalyticsData] = useState({})
  const [timeRange, setTimeRange] = useState('7d')
  const [selectedMetric, setSelectedMetric] = useState('usage')
  const [isLoading, setIsLoading] = useState(false)
  const canvasRef = useRef(null)

  const timeRanges = [
    { value: '1h', label: 'Last Hour' },
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' }
  ]

  const metrics = [
    { value: 'usage', label: 'System Usage' },
    { value: 'performance', label: 'Performance' },
    { value: 'ai', label: 'AI Usage' },
    { value: 'storage', label: 'Storage' },
    { value: 'network', label: 'Network' }
  ]

  useEffect(() => {
    if (token) {
      loadAnalytics()
    }
  }, [token, timeRange, selectedMetric])

  const loadAnalytics = async () => {
    setIsLoading(true)
    try {
      const response = await axios.get('http://localhost:8000/analytics/data', {
        headers: { Authorization: `Bearer ${token}` },
        params: { timeRange, metric: selectedMetric }
      })

      setAnalyticsData(response.data)
      drawChart(response.data)
    } catch (error) {
      console.error('Error loading analytics:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const drawChart = (data) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height

    // Clear canvas
    ctx.fillStyle = '#f5f5f5'
    ctx.fillRect(0, 0, width, height)

    // Draw simple bar chart
    if (data.chartData && data.chartData.length > 0) {
      const maxValue = Math.max(...data.chartData.map(d => d.value))
      const barWidth = width / data.chartData.length

      data.chartData.forEach((point, index) => {
        const barHeight = (point.value / maxValue) * (height - 40)
        const x = index * barWidth
        const y = height - barHeight - 20

        // Draw bar
        ctx.fillStyle = '#4CAF50'
        ctx.fillRect(x + 2, y, barWidth - 4, barHeight)

        // Draw label
        ctx.fillStyle = '#000'
        ctx.font = '10px Arial'
        ctx.textAlign = 'center'
        ctx.fillText(point.label, x + barWidth / 2, height - 5)
      })
    }
  }

  const exportAnalytics = async (format) => {
    try {
      const response = await axios.get(`http://localhost:8000/analytics/export`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { format, timeRange, metric: selectedMetric },
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `analytics_${selectedMetric}_${timeRange}.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      alert('Error exporting analytics: ' + error.message)
    }
  }

  const generateInsights = async () => {
    try {
      const response = await axios.post('http://localhost:8000/analytics/insights', {
        data: analyticsData,
        metric: selectedMetric
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('AI Insights: ' + response.data.insights)
    } catch (error) {
      alert('Error generating insights: ' + error.message)
    }
  }

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h1>Analytics Dashboard</h1>
        <p>Comprehensive data visualization and insights</p>
      </div>

      {/* Controls */}
      <div className="analytics-controls">
        <div className="control-group">
          <label>Time Range: </label>
          <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            {timeRanges.map(range => (
              <option key={range.value} value={range.value}>{range.label}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Metric: </label>
          <select value={selectedMetric} onChange={(e) => setSelectedMetric(e.target.value)}>
            {metrics.map(metric => (
              <option key={metric.value} value={metric.value}>{metric.label}</option>
            ))}
          </select>
        </div>

        <div className="control-buttons">
          <button onClick={generateInsights} className="btn-primary">Generate AI Insights</button>
          <button onClick={() => exportAnalytics('csv')} className="btn-secondary">Export CSV</button>
          <button onClick={() => exportAnalytics('json')} className="btn-secondary">Export JSON</button>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-state">Loading analytics...</div>
      ) : (
        <div className="analytics-grid">
          {/* Key Metrics */}
          <div className="analytics-card">
            <h3>Key Metrics</h3>
            <div className="metrics-list">
              <div className="metric-item">
                <strong>Total Requests:</strong> {analyticsData.totalRequests || 0}
              </div>
              <div className="metric-item">
                <strong>Average Response Time:</strong> {analyticsData.avgResponseTime || 0}ms
              </div>
              <div className="metric-item">
                <strong>Error Rate:</strong> {analyticsData.errorRate || 0}%
              </div>
              <div className="metric-item">
                <strong>Active Users:</strong> {analyticsData.activeUsers || 0}
              </div>
            </div>
          </div>

          {/* Chart */}
          <div className="analytics-card chart-card">
            <h3>{selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)} Over Time</h3>
            <canvas
              ref={canvasRef}
              width={400}
              height={300}
              className="analytics-chart"
            />
          </div>

          {/* Top Items */}
          <div className="analytics-card">
            <h3>Top Performing Items</h3>
            <div className="top-items-list">
              {analyticsData.topItems?.map((item, index) => (
                <div key={index} className="top-item">
                  <strong>{item.name}</strong>: {item.value}
                </div>
              )) || <p>No data available</p>}
            </div>
          </div>

          {/* System Health */}
          <div className="analytics-card">
            <h3>System Health</h3>
            <div className="health-metrics">
              <div className="health-item">
                <strong>CPU Usage:</strong>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${analyticsData.cpuUsage > 80 ? 'danger' : 'success'}`}
                    style={{ width: `${analyticsData.cpuUsage || 0}%` }}
                  />
                </div>
                {analyticsData.cpuUsage || 0}%
              </div>
              <div className="health-item">
                <strong>Memory Usage:</strong>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${analyticsData.memoryUsage > 80 ? 'danger' : 'success'}`}
                    style={{ width: `${analyticsData.memoryUsage || 0}%` }}
                  />
                </div>
                {analyticsData.memoryUsage || 0}%
              </div>
              <div className="health-item">
                <strong>Disk Usage:</strong>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${analyticsData.diskUsage > 90 ? 'danger' : 'success'}`}
                    style={{ width: `${analyticsData.diskUsage || 0}%` }}
                  />
                </div>
                {analyticsData.diskUsage || 0}%
              </div>
            </div>
          </div>

          {/* AI Usage */}
          <div className="analytics-card">
            <h3>AI Usage Statistics</h3>
            <div className="metrics-list">
              <div className="metric-item">
                <strong>Models Loaded:</strong> {analyticsData.modelsLoaded || 0}
              </div>
              <div className="metric-item">
                <strong>Total AI Requests:</strong> {analyticsData.aiRequests || 0}
              </div>
              <div className="metric-item">
                <strong>Average AI Response Time:</strong> {analyticsData.avgAiResponseTime || 0}ms
              </div>
              <div className="metric-item">
                <strong>Most Used Model:</strong> {analyticsData.mostUsedModel || 'N/A'}
              </div>
            </div>
          </div>

          {/* Network Stats */}
          <div className="analytics-card">
            <h3>Network Statistics</h3>
            <div className="metrics-list">
              <div className="metric-item">
                <strong>Data Transferred:</strong> {analyticsData.dataTransferred || 0} MB
              </div>
              <div className="metric-item">
                <strong>Active Connections:</strong> {analyticsData.activeConnections || 0}
              </div>
              <div className="metric-item">
                <strong>Average Latency:</strong> {analyticsData.avgLatency || 0}ms
              </div>
              <div className="metric-item">
                <strong>Uptime:</strong> {analyticsData.uptime || 0}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Real-time Updates */}
      <div className="analytics-card realtime-card">
        <h3>Real-time Updates</h3>
        <div className="realtime-status">
          <div className="status-indicator" />
          <span>Live data streaming enabled</span>
          <button onClick={loadAnalytics} className="btn-secondary">Refresh</button>
        </div>
      </div>
    </div>
  )
}

export default Analytics