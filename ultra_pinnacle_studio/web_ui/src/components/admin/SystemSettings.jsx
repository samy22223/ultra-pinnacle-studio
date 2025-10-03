import React, { useState, useEffect } from 'react'
import axios from 'axios'

const SystemSettings = () => {
  const [settings, setSettings] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/admin/settings', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSettings(response.data)
    } catch (err) {
      console.error('Error fetching settings:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSettingChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
  }

  const handleSaveSettings = async () => {
    try {
      setSaving(true)
      const token = localStorage.getItem('token')
      await axios.put('http://localhost:8000/admin/settings', settings, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Settings saved successfully')
    } catch (err) {
      console.error('Error saving settings:', err)
      alert(`Failed to save settings: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const settingCategories = [
    {
      key: 'security',
      name: 'Security Settings',
      description: 'Configure security-related settings',
      fields: [
        { key: 'secret_key', label: 'Secret Key', type: 'password' },
        { key: 'algorithm', label: 'JWT Algorithm', type: 'text' },
        { key: 'access_token_expire_minutes', label: 'Token Expiration (minutes)', type: 'number' }
      ]
    },
    {
      key: 'models',
      name: 'AI Model Settings',
      description: 'Configure AI model parameters',
      fields: [
        { key: 'default_model', label: 'Default Model', type: 'text' },
        { key: 'max_tokens', label: 'Max Tokens', type: 'number' },
        { key: 'temperature', label: 'Temperature', type: 'number', step: 0.1, min: 0, max: 2 }
      ]
    },
    {
      key: 'database',
      name: 'Database Settings',
      description: 'Database configuration',
      fields: [
        { key: 'url', label: 'Database URL', type: 'text' },
        { key: 'echo', label: 'SQL Echo', type: 'checkbox' }
      ]
    },
    {
      key: 'cache',
      name: 'Cache Settings',
      description: 'Caching configuration',
      fields: [
        { key: 'enabled', label: 'Cache Enabled', type: 'checkbox' },
        { key: 'ttl', label: 'Cache TTL (seconds)', type: 'number' }
      ]
    }
  ]

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading system settings...</p>
      </div>
    )
  }

  return (
    <div className="system-settings">
      <div className="admin-section-header">
        <h2>System Settings</h2>
        <p>Configure system-wide settings and preferences</p>
      </div>

      <div className="settings-actions">
        <button
          onClick={handleSaveSettings}
          className="admin-btn primary"
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save All Settings'}
        </button>
        <button
          onClick={fetchSettings}
          className="admin-btn secondary"
        >
          Refresh
        </button>
      </div>

      {settingCategories.map(category => (
        <div key={category.key} className="settings-category">
          <h3>{category.name}</h3>
          <p className="category-description">{category.description}</p>

          <div className="settings-fields">
            {category.fields.map(field => (
              <div key={field.key} className="setting-field">
                <label htmlFor={`${category.key}_${field.key}`}>
                  {field.label}:
                </label>
                {field.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    id={`${category.key}_${field.key}`}
                    checked={settings[category.key]?.[field.key] || false}
                    onChange={(e) => handleSettingChange(category.key, field.key, e.target.checked)}
                  />
                ) : field.type === 'number' ? (
                  <input
                    type="number"
                    id={`${category.key}_${field.key}`}
                    value={settings[category.key]?.[field.key] || ''}
                    onChange={(e) => handleSettingChange(category.key, field.key,
                      field.step ? parseFloat(e.target.value) : parseInt(e.target.value))}
                    step={field.step}
                    min={field.min}
                    max={field.max}
                    className="admin-input"
                  />
                ) : (
                  <input
                    type={field.type}
                    id={`${category.key}_${field.key}`}
                    value={settings[category.key]?.[field.key] || ''}
                    onChange={(e) => handleSettingChange(category.key, field.key, e.target.value)}
                    className="admin-input"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {error && (
        <div className="settings-error">
          <h4>Error</h4>
          <p>{error}</p>
        </div>
      )}
    </div>
  )
}

export default SystemSettings