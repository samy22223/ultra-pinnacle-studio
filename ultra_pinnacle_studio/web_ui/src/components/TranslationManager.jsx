import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import axios from 'axios'

const TranslationManager = () => {
  const { t, i18n } = useTranslation('common')
  const [translations, setTranslations] = useState({})
  const [languages, setLanguages] = useState([])
  const [selectedLanguage, setSelectedLanguage] = useState('en')
  const [selectedNamespace, setSelectedNamespace] = useState('common')
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(null)
  const [editValue, setEditValue] = useState('')

  useEffect(() => {
    loadLanguages()
    loadTranslations()
  }, [selectedLanguage])

  const loadLanguages = async () => {
    try {
      const response = await axios.get('/api/languages')
      setLanguages(response.data)
    } catch (error) {
      console.error('Error loading languages:', error)
    }
  }

  const loadTranslations = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/translations')
      setTranslations(response.data.translations || {})
    } catch (error) {
      console.error('Error loading translations:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (namespace, key, value) => {
    setEditing({ namespace, key })
    setEditValue(value)
  }

  const handleSave = async () => {
    if (!editing) return

    try {
      // Here you would implement the API call to update translation
      // For now, just update local state
      const updatedTranslations = { ...translations }
      if (!updatedTranslations[editing.namespace]) {
        updatedTranslations[editing.namespace] = {}
      }
      updatedTranslations[editing.namespace][editing.key] = {
        value: editValue,
        approved: true
      }
      setTranslations(updatedTranslations)
      setEditing(null)
      setEditValue('')
    } catch (error) {
      console.error('Error saving translation:', error)
    }
  }

  const handleCancel = () => {
    setEditing(null)
    setEditValue('')
  }

  const getNamespaces = () => {
    return Object.keys(translations)
  }

  const getTranslationsForNamespace = (namespace) => {
    return translations[namespace] || {}
  }

  if (loading) {
    return <div className="translation-manager-loading">{t('common.loading')}</div>
  }

  return (
    <div className="translation-manager">
      <h2>Translation Management</h2>

      <div className="translation-controls">
        <div className="control-group">
          <label>Language:</label>
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
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
          >
            {getNamespaces().map(ns => (
              <option key={ns} value={ns}>{ns}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="translations-table">
        <table>
          <thead>
            <tr>
              <th>Key</th>
              <th>Value</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(getTranslationsForNamespace(selectedNamespace)).map(([key, data]) => (
              <tr key={key}>
                <td className="key-cell">{key}</td>
                <td className="value-cell">
                  {editing && editing.namespace === selectedNamespace && editing.key === key ? (
                    <textarea
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      rows={3}
                    />
                  ) : (
                    data.value
                  )}
                </td>
                <td className="status-cell">
                  <span className={`status ${data.approved ? 'approved' : 'pending'}`}>
                    {data.approved ? 'Approved' : 'Pending'}
                  </span>
                </td>
                <td className="actions-cell">
                  {editing && editing.namespace === selectedNamespace && editing.key === key ? (
                    <div className="edit-actions">
                      <button onClick={handleSave} className="btn-save">Save</button>
                      <button onClick={handleCancel} className="btn-cancel">Cancel</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleEdit(selectedNamespace, key, data.value)}
                      className="btn-edit"
                    >
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default TranslationManager