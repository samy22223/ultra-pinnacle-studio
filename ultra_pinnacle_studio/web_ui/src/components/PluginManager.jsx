import React, { useState, useEffect } from 'react';
import './PluginManager.css';

const PluginManager = ({ token }) => {
  const [plugins, setPlugins] = useState([]);
  const [availablePlugins, setAvailablePlugins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('installed');
  const [selectedPlugin, setSelectedPlugin] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    loadPlugins();
    loadAvailablePlugins();
  }, []);

  const loadPlugins = async () => {
    try {
      const response = await fetch('/api/plugins', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setPlugins(data);
      }
    } catch (error) {
      console.error('Error loading plugins:', error);
    }
  };

  const loadAvailablePlugins = async () => {
    try {
      const response = await fetch('/api/plugins/marketplace', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setAvailablePlugins(data.plugins || []);
      }
    } catch (error) {
      console.error('Error loading available plugins:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePluginAction = async (pluginId, action) => {
    try {
      const response = await fetch(`/api/plugins/${pluginId}/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        await loadPlugins(); // Refresh plugin list
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error(`Error ${action}ing plugin:`, error);
      alert(`Error ${action}ing plugin`);
    }
  };

  const handleInstallPlugin = async (pluginName) => {
    try {
      const response = await fetch(`/api/plugins/marketplace/${pluginName}/install`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        alert('Plugin installed successfully');
        await loadPlugins();
        await loadAvailablePlugins();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error installing plugin:', error);
      alert('Error installing plugin');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'enabled': return 'green';
      case 'disabled': return 'orange';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const renderPluginCard = (plugin, isInstalled = true) => (
    <div key={plugin.id || plugin.name} className="plugin-card">
      <div className="plugin-header">
        <h3>{plugin.name}</h3>
        <span className={`status-badge ${getStatusColor(plugin.state)}`}>
          {plugin.state || 'available'}
        </span>
      </div>

      <p className="plugin-description">
        {plugin.description || 'No description available'}
      </p>

      <div className="plugin-meta">
        <span>Version: {plugin.version || 'N/A'}</span>
        {plugin.author && <span>Author: {plugin.author}</span>}
        {plugin.downloads && <span>Downloads: {plugin.downloads}</span>}
      </div>

      <div className="plugin-actions">
        {isInstalled ? (
          <>
            {plugin.state === 'initialized' && (
              <button
                className="btn btn-primary"
                onClick={() => handlePluginAction(plugin.id, 'enable')}
              >
                Enable
              </button>
            )}
            {plugin.state === 'enabled' && (
              <button
                className="btn btn-warning"
                onClick={() => handlePluginAction(plugin.id, 'disable')}
              >
                Disable
              </button>
            )}
            <button
              className="btn btn-danger"
              onClick={() => handlePluginAction(plugin.id, 'unload')}
            >
              Unload
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setSelectedPlugin(plugin);
                setShowSettings(true);
              }}
            >
              Settings
            </button>
          </>
        ) : (
          <button
            className="btn btn-success"
            onClick={() => handleInstallPlugin(plugin.name)}
          >
            Install
          </button>
        )}
      </div>
    </div>
  );

  if (loading) {
    return <div className="plugin-manager loading">Loading plugins...</div>;
  }

  return (
    <div className="plugin-manager">
      <div className="plugin-header">
        <h1>Plugin Manager</h1>
        <p>Manage plugins for Ultra Pinnacle AI Studio</p>
      </div>

      <div className="plugin-tabs">
        <button
          className={`tab ${activeTab === 'installed' ? 'active' : ''}`}
          onClick={() => setActiveTab('installed')}
        >
          Installed Plugins ({plugins.length})
        </button>
        <button
          className={`tab ${activeTab === 'marketplace' ? 'active' : ''}`}
          onClick={() => setActiveTab('marketplace')}
        >
          Marketplace ({availablePlugins.length})
        </button>
      </div>

      <div className="plugin-content">
        {activeTab === 'installed' ? (
          <div className="plugin-grid">
            {plugins.length > 0 ? (
              plugins.map(plugin => renderPluginCard(plugin, true))
            ) : (
              <div className="no-plugins">
                <p>No plugins installed</p>
                <button
                  className="btn btn-primary"
                  onClick={() => setActiveTab('marketplace')}
                >
                  Browse Marketplace
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="plugin-grid">
            {availablePlugins.length > 0 ? (
              availablePlugins.map(plugin => renderPluginCard(plugin, false))
            ) : (
              <div className="no-plugins">
                <p>No plugins available in marketplace</p>
              </div>
            )}
          </div>
        )}
      </div>

      {showSettings && selectedPlugin && (
        <PluginSettingsModal
          plugin={selectedPlugin}
          token={token}
          onClose={() => {
            setShowSettings(false);
            setSelectedPlugin(null);
          }}
          onSave={() => loadPlugins()}
        />
      )}
    </div>
  );
};

const PluginSettingsModal = ({ plugin, token, onClose, onSave }) => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, [plugin]);

  const loadSettings = async () => {
    try {
      const response = await fetch(`/api/plugins/${plugin.id}/settings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setSettings(data.settings || {});
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      const response = await fetch(`/api/plugins/${plugin.id}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });

      if (response.ok) {
        onSave();
        onClose();
      } else {
        alert('Error saving settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Error saving settings');
    }
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings for {plugin.name}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {Object.keys(settings).length > 0 ? (
            Object.entries(settings).map(([key, value]) => (
              <div key={key} className="setting-item">
                <label>{key}:</label>
                {typeof value === 'boolean' ? (
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={e => handleSettingChange(key, e.target.checked)}
                  />
                ) : typeof value === 'number' ? (
                  <input
                    type="number"
                    value={value}
                    onChange={e => handleSettingChange(key, parseFloat(e.target.value))}
                  />
                ) : (
                  <input
                    type="text"
                    value={value}
                    onChange={e => handleSettingChange(key, e.target.value)}
                  />
                )}
              </div>
            ))
          ) : (
            <p>No settings available for this plugin</p>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={saveSettings}>Save</button>
        </div>
      </div>
    </div>
  );
};

export default PluginManager;