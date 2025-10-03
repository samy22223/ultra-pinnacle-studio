import React, { useState, useEffect } from 'react'
import axios from 'axios'

const PluginManagement = () => {
  const [plugins, setPlugins] = useState([])
  const [marketplacePlugins, setMarketplacePlugins] = useState([])
  const [loading, setLoading] = useState(true)
  const [marketplaceLoading, setMarketplaceLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedPlugin, setSelectedPlugin] = useState(null)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [activeTab, setActiveTab] = useState('installed')

  useEffect(() => {
    fetchPlugins()
  }, [])

  const fetchPlugins = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/api/plugins', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setPlugins(response.data)
    } catch (err) {
      console.error('Error fetching plugins:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchMarketplacePlugins = async () => {
    try {
      setMarketplaceLoading(true)
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/api/plugins/marketplace', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setMarketplacePlugins(response.data.plugins || [])
    } catch (err) {
      console.error('Error fetching marketplace plugins:', err)
      setError(err.message)
    } finally {
      setMarketplaceLoading(false)
    }
  }

  const handlePluginAction = async (pluginId, action, version = null) => {
    try {
      const token = localStorage.getItem('token')
      let response

      switch (action) {
        case 'enable':
          response = await axios.post(`http://localhost:8000/api/plugins/${pluginId}/enable`, {}, {
            headers: { Authorization: `Bearer ${token}` }
          })
          break
        case 'disable':
          response = await axios.post(`http://localhost:8000/api/plugins/${pluginId}/disable`, {}, {
            headers: { Authorization: `Bearer ${token}` }
          })
          break
        case 'unload':
          response = await axios.delete(`http://localhost:8000/api/plugins/${pluginId}`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          break
        case 'install':
          response = await axios.post(`http://localhost:8000/api/plugins/marketplace/${pluginId}/install`, {
            version: version || 'latest'
          }, {
            headers: { Authorization: `Bearer ${token}` }
          })
          break
        default:
          throw new Error(`Unknown action: ${action}`)
      }

      // Refresh plugin list
      await fetchPlugins()
      alert(response.data.message)
    } catch (err) {
      console.error(`Error ${action}ing plugin:`, err)
      alert(`Failed to ${action} plugin: ${err.message}`)
    }
  }

  const openConfigModal = (plugin) => {
    setSelectedPlugin(plugin)
    setShowConfigModal(true)
  }

  const closeConfigModal = () => {
    setSelectedPlugin(null)
    setShowConfigModal(false)
  }

  const handleConfigSave = async (config) => {
    try {
      const token = localStorage.getItem('token')
      await axios.put(`http://localhost:8000/api/plugins/${selectedPlugin.id}/settings`, config, {
        headers: { Authorization: `Bearer ${token}` }
      })

      await fetchPlugins()
      closeConfigModal()
      alert('Plugin configuration updated successfully')
    } catch (err) {
      console.error('Error updating plugin config:', err)
      alert(`Failed to update configuration: ${err.message}`)
    }
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading plugins...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="admin-error">
        <h3>Error Loading Plugins</h3>
        <p>{error}</p>
        <button onClick={fetchPlugins} className="admin-btn primary">Retry</button>
      </div>
    )
  }

  return (
    <div className="plugin-management">
      <div className="admin-section-header">
        <h2>Plugin Management</h2>
        <p>Install, configure, and manage system plugins</p>
      </div>

      {/* Tab Navigation */}
      <div className="plugin-tabs">
        <button
          className={`tab-button ${activeTab === 'installed' ? 'active' : ''}`}
          onClick={() => setActiveTab('installed')}
        >
          Installed Plugins ({plugins.length})
        </button>
        <button
          className={`tab-button ${activeTab === 'marketplace' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('marketplace')
            if (marketplacePlugins.length === 0) {
              fetchMarketplacePlugins()
            }
          }}
        >
          Marketplace
        </button>
      </div>

      {/* Installed Plugins Tab */}
      {activeTab === 'installed' && (
        <div className="plugins-grid">
          {plugins.map(plugin => (
            <div key={plugin.id} className="plugin-card">
              <div className="plugin-header">
                <h3>{plugin.name || plugin.id}</h3>
                <span className={`plugin-status ${plugin.state?.toLowerCase()}`}>
                  {plugin.state || 'Unknown'}
                </span>
              </div>

              <div className="plugin-info">
                <p className="plugin-description">
                  {plugin.metadata?.description || 'No description available'}
                </p>
                <div className="plugin-meta">
                  <span>Version: {plugin.version || 'N/A'}</span>
                  <span>Author: {plugin.metadata?.author || 'Unknown'}</span>
                </div>
              </div>

              <div className="plugin-actions">
                {plugin.state === 'LOADED' && (
                  <>
                    {plugin.enabled ? (
                      <button
                        onClick={() => handlePluginAction(plugin.id, 'disable')}
                        className="admin-btn small warning"
                      >
                        Disable
                      </button>
                    ) : (
                      <button
                        onClick={() => handlePluginAction(plugin.id, 'enable')}
                        className="admin-btn small success"
                      >
                        Enable
                      </button>
                    )}
                  </>
                )}

                <button
                  onClick={() => openConfigModal(plugin)}
                  className="admin-btn small secondary"
                  disabled={!plugin.enabled}
                >
                  Configure
                </button>

                <button
                  onClick={() => handlePluginAction(plugin.id, 'unload')}
                  className="admin-btn small danger"
                >
                  Unload
                </button>
              </div>
            </div>
          ))}

          {plugins.length === 0 && (
            <div className="no-plugins">
              <p>No plugins installed</p>
              <button
                onClick={() => setActiveTab('marketplace')}
                className="admin-btn primary"
              >
                Browse Marketplace
              </button>
            </div>
          )}
        </div>
      )}

      {/* Marketplace Tab */}
      {activeTab === 'marketplace' && (
        <div className="marketplace">
          {marketplaceLoading ? (
            <div className="admin-loading">
              <div className="loading-spinner"></div>
              <p>Loading marketplace...</p>
            </div>
          ) : (
            <div className="plugins-grid">
              {marketplacePlugins.map(plugin => (
                <div key={plugin.id} className="plugin-card marketplace-card">
                  <div className="plugin-header">
                    <h3>{plugin.name}</h3>
                    <span className="plugin-price">
                      {plugin.price === 0 ? 'Free' : `$${plugin.price}`}
                    </span>
                  </div>

                  <div className="plugin-info">
                    <p className="plugin-description">{plugin.description}</p>
                    <div className="plugin-meta">
                      <span>Version: {plugin.version}</span>
                      <span>Author: {plugin.author}</span>
                      <span>Downloads: {plugin.downloads || 0}</span>
                    </div>
                  </div>

                  <div className="plugin-actions">
                    <button
                      onClick={() => handlePluginAction(plugin.id, 'install', plugin.version)}
                      className="admin-btn small primary"
                    >
                      Install
                    </button>
                  </div>
                </div>
              ))}

              {marketplacePlugins.length === 0 && !marketplaceLoading && (
                <div className="no-plugins">
                  <p>No plugins available in marketplace</p>
                  <button
                    onClick={fetchMarketplacePlugins}
                    className="admin-btn primary"
                  >
                    Refresh
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Plugin Configuration Modal */}
      {showConfigModal && selectedPlugin && (
        <PluginConfigModal
          plugin={selectedPlugin}
          onClose={closeConfigModal}
          onSave={handleConfigSave}
        />
      )}
    </div>
  )
}

// Plugin Configuration Modal Component
const PluginConfigModal = ({ plugin, onClose, onSave }) => {
  const [config, setConfig] = useState(plugin.settings || {})

  const handleChange = (key, value) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
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
          <h3>Configure {plugin.name || plugin.id}</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          {Object.entries(config).map(([key, value]) => (
            <div key={key} className="form-group">
              <label htmlFor={key}>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
              {typeof value === 'boolean' ? (
                <input
                  type="checkbox"
                  id={key}
                  checked={value}
                  onChange={(e) => handleChange(key, e.target.checked)}
                />
              ) : typeof value === 'number' ? (
                <input
                  type="number"
                  id={key}
                  value={value}
                  onChange={(e) => handleChange(key, parseFloat(e.target.value))}
                  className="admin-input"
                />
              ) : (
                <input
                  type="text"
                  id={key}
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="admin-input"
                />
              )}
            </div>
          ))}

          {Object.keys(config).length === 0 && (
            <p className="no-config">This plugin has no configurable settings.</p>
          )}
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Save Configuration</button>
        </div>
      </div>
    </div>
  )
}

export default PluginManagement