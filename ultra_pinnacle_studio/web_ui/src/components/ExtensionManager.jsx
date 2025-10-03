import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import extensionBridge from '../utils/extensionBridge'
import './ExtensionManager.css'

const ExtensionManager = ({ token }) => {
  const { t } = useTranslation('common')
  const [extensions, setExtensions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadExtensions()
  }, [])

  const loadExtensions = async () => {
    try {
      setLoading(true)
      const extList = extensionBridge.getAllExtensions()
      setExtensions(extList)
    } catch (error) {
      console.error('Failed to load extensions:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleExtension = async (extensionId) => {
    try {
      const extension = extensions.find(ext => ext.id === extensionId)
      if (!extension) return

      let success
      if (extension.enabled) {
        success = await extensionBridge.disableExtension(extensionId)
      } else {
        success = await extensionBridge.enableExtension(extensionId)
      }

      if (success) {
        setExtensions(prev => prev.map(ext =>
          ext.id === extensionId
            ? { ...ext, enabled: !ext.enabled }
            : ext
        ))
      }
    } catch (error) {
      console.error('Failed to toggle extension:', error)
    }
  }

  const testExtension = async (extensionId) => {
    try {
      const result = await extensionBridge.sendMessage(extensionId, {
        type: 'TEST_CONNECTION',
        timestamp: Date.now()
      })
      alert(`Extension ${extensionId} test result: ${JSON.stringify(result)}`)
    } catch (error) {
      alert(`Extension ${extensionId} test failed: ${error.message}`)
    }
  }

  const categories = [
    { id: 'all', label: 'All Extensions', icon: '🔧' },
    { id: 'productivity', label: 'Productivity', icon: '⚡' },
    { id: 'writing', label: 'Writing', icon: '✍️' },
    { id: 'developer', label: 'Developer Tools', icon: '🛠️' },
    { id: 'accessibility', label: 'Accessibility', icon: '♿' },
    { id: 'privacy', label: 'Privacy & Security', icon: '🔒' },
    { id: 'storage', label: 'Storage', icon: '💾' }
  ]

  const filteredExtensions = extensions.filter(ext => {
    const matchesCategory = selectedCategory === 'all' || ext.type === selectedCategory
    const matchesSearch = ext.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ext.id.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesCategory && matchesSearch
  })

  if (loading) {
    return (
      <div className="extension-manager">
        <div className="loading-spinner">Loading extensions...</div>
      </div>
    )
  }

  return (
    <div className="extension-manager">
      <div className="extension-header">
        <h2>Browser Extension Manager</h2>
        <p>Manage and configure browser extensions for enhanced functionality</p>
      </div>

      <div className="extension-controls">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search extensions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="category-tabs">
          {categories.map(category => (
            <button
              key={category.id}
              className={`category-tab ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              <span className="category-icon">{category.icon}</span>
              <span className="category-label">{category.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="extensions-grid">
        {filteredExtensions.map(extension => (
          <div key={extension.id} className="extension-card">
            <div className="extension-header">
              <div className="extension-info">
                <h3 className="extension-name">{extension.name}</h3>
                <span className="extension-type">{extension.type}</span>
                <span className="extension-version">v{extension.version}</span>
              </div>
              <div className="extension-status">
                <span className={`status-indicator ${extension.enabled ? 'enabled' : 'disabled'}`}>
                  {extension.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>

            <div className="extension-description">
              <p>Integration with {extension.name} for enhanced {extension.type} features.</p>
            </div>

            <div className="extension-actions">
              <button
                className={`toggle-btn ${extension.enabled ? 'disable' : 'enable'}`}
                onClick={() => toggleExtension(extension.id)}
              >
                {extension.enabled ? 'Disable' : 'Enable'}
              </button>
              <button
                className="test-btn"
                onClick={() => testExtension(extension.id)}
                disabled={!extension.enabled}
              >
                Test
              </button>
            </div>

            <div className="extension-features">
              <h4>Features:</h4>
              <ul>
                <li>Seamless integration with Ultra Pinnacle Studio</li>
                <li>Cross-browser compatibility</li>
                <li>Real-time synchronization</li>
                <li>Enhanced user experience</li>
              </ul>
            </div>
          </div>
        ))}
      </div>

      {filteredExtensions.length === 0 && (
        <div className="no-extensions">
          <p>No extensions found matching your criteria.</p>
        </div>
      )}

      <div className="extension-info-panel">
        <h3>Extension Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <h4>Browser Compatibility</h4>
            <p>Extensions are designed to work across Chrome, Firefox, Safari, and Edge browsers.</p>
          </div>
          <div className="info-item">
            <h4>Security</h4>
            <p>All extensions follow strict security guidelines and require user consent for data access.</p>
          </div>
          <div className="info-item">
            <h4>Performance</h4>
            <p>Extensions are optimized for minimal performance impact and battery usage.</p>
          </div>
          <div className="info-item">
            <h4>Updates</h4>
            <p>Extensions are automatically updated to ensure compatibility and security.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExtensionManager