import React, { useState, useEffect } from 'react'
import axios from 'axios'

const TranslationManagement = () => {
  const [languages, setLanguages] = useState([])
  const [translations, setTranslations] = useState({})
  const [selectedLanguage, setSelectedLanguage] = useState('en')
  const [selectedNamespace, setSelectedNamespace] = useState('common')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLanguages()
  }, [])

  useEffect(() => {
    if (selectedLanguage) {
      fetchTranslations()
    }
  }, [selectedLanguage, selectedNamespace])

  const fetchLanguages = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/api/languages', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setLanguages(response.data)
    } catch (err) {
      console.error('Error fetching languages:', err)
      setError(err.message)
    }
  }

  const fetchTranslations = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const response = await axios.get(`http://localhost:8000/api/translations/${selectedNamespace}`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { language: selectedLanguage }
      })
      setTranslations(response.data.translations || {})
    } catch (err) {
      console.error('Error fetching translations:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTranslationUpdate = async (key, value) => {
    try {
      const token = localStorage.getItem('token')
      await axios.put(`http://localhost:8000/admin/translations/${selectedNamespace}/${key}`, {
        value,
        language_code: selectedLanguage
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      // Update local state
      setTranslations(prev => ({
        ...prev,
        [key]: value
      }))

      alert('Translation updated successfully')
    } catch (err) {
      console.error('Error updating translation:', err)
      alert(`Failed to update translation: ${err.message}`)
    }
  }

  const getNamespaces = () => {
    return ['common', 'auth', 'chat', 'admin', 'plugins', 'backup']
  }

  if (loading && !translations) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading translations...</p>
      </div>
    )
  }

  return (
    <div className="translation-management">
      <div className="admin-section-header">
        <h2>Translation Management</h2>
        <p>Manage translations for multi-language support</p>
      </div>

      {/* Language and Namespace Selection */}
      <div className="translation-controls">
        <div className="control-group">
          <label>Language:</label>
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="admin-select"
          >
            {languages.map(lang => (
              <option key={lang.code} value={lang.code}>
                {lang.native_name} ({lang.name})
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Namespace:</label>
          <select
            value={selectedNamespace}
            onChange={(e) => setSelectedNamespace(e.target.value)}
            className="admin-select"
          >
            {getNamespaces().map(ns => (
              <option key={ns} value={ns}>
                {ns.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Translations List */}
      <div className="translations-list">
        {Object.entries(translations).map(([key, value]) => (
          <div key={key} className="translation-item">
            <div className="translation-key">
              <code>{key}</code>
            </div>
            <div className="translation-value">
              <textarea
                value={value}
                onChange={(e) => {
                  const newTranslations = { ...translations }
                  newTranslations[key] = e.target.value
                  setTranslations(newTranslations)
                }}
                onBlur={(e) => handleTranslationUpdate(key, e.target.value)}
                className="translation-input"
                rows={Math.max(1, value.split('\n').length)}
              />
            </div>
          </div>
        ))}

        {Object.keys(translations).length === 0 && (
          <div className="no-translations">
            <p>No translations found for {selectedLanguage} in namespace {selectedNamespace}</p>
          </div>
        )}
      </div>

      {/* Translation Statistics */}
      <div className="translation-stats">
        <div className="stat-card">
          <h4>Total Languages</h4>
          <span className="stat-number">{languages.length}</span>
        </div>
        <div className="stat-card">
          <h4>Keys in {selectedNamespace}</h4>
          <span className="stat-number">{Object.keys(translations).length}</span>
        </div>
        <div className="stat-card">
          <h4>Completion Rate</h4>
          <span className="stat-number">
            {Object.keys(translations).length > 0 ?
              Math.round((Object.values(translations).filter(v => v && v.trim()).length / Object.keys(translations).length) * 100) : 0}%
          </span>
        </div>
      </div>
    </div>
  )
}

export default TranslationManagement