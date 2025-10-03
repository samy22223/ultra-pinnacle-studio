import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './NotificationCenter.css'

const NotificationCenter = ({ token, isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('all') // all, unread, system, chat, collaborative
  const [preferences, setPreferences] = useState([])
  const [showPreferences, setShowPreferences] = useState(false)
  const websocketRef = useRef(null)

  useEffect(() => {
    if (token && isOpen) {
      loadNotifications()
      loadUnreadCount()
      loadPreferences()
      connectWebSocket()
    }

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
    }
  }, [token, isOpen])

  const connectWebSocket = () => {
    if (websocketRef.current) {
      websocketRef.current.close()
    }

    const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`)
    ws.onopen = () => {
      console.log('Notification WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'notification') {
        handleNewNotification(data.data)
      } else if (data.type === 'notification_updated') {
        // Handle notification updates (e.g., marked as read)
        const updatedId = data.content.notification_id
        if (data.content.status === 'read') {
          setNotifications(prev =>
            prev.map(n => n.id === updatedId ? { ...n, is_read: true } : n)
          )
          setUnreadCount(prev => Math.max(0, prev - 1))
        }
      } else if (data.type === 'bulk_update') {
        // Handle bulk updates
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
        setUnreadCount(0)
      }
    }

    ws.onclose = () => {
      console.log('Notification WebSocket disconnected')
      // Reconnect after delay
      setTimeout(connectWebSocket, 5000)
    }

    ws.onerror = (error) => {
      console.error('Notification WebSocket error:', error)
    }

    websocketRef.current = ws
  }

  const loadNotifications = async (category = null) => {
    setLoading(true)
    try {
      const params = { limit: 50 }
      if (activeTab === 'unread') params.unread_only = true
      if (category && activeTab !== 'all' && activeTab !== 'unread') params.category = activeTab

      const response = await axios.get('http://localhost:8000/api/notifications', {
        headers: { Authorization: `Bearer ${token}` },
        params
      })
      setNotifications(response.data)
    } catch (error) {
      console.error('Error loading notifications:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadUnreadCount = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/notifications/unread-count', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUnreadCount(response.data.unread_count)
    } catch (error) {
      console.error('Error loading unread count:', error)
    }
  }

  const loadPreferences = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/notifications/preferences', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setPreferences(response.data)
    } catch (error) {
      console.error('Error loading preferences:', error)
    }
  }

  const handleNewNotification = (notification) => {
    setNotifications(prev => [notification, ...prev])
    setUnreadCount(prev => prev + 1)
    // Show browser notification if permitted
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico'
      })
    }
  }

  const markAsRead = async (notificationId) => {
    try {
      await axios.post(`http://localhost:8000/api/notifications/${notificationId}/read`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      )
      setUnreadCount(prev => Math.max(0, prev - 1))

      // Send WebSocket message to sync with other clients
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'mark_read',
          notification_id: notificationId
        }))
      }
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      await axios.post('http://localhost:8000/api/notifications/mark-all-read', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)

      // Send WebSocket message to sync with other clients
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'mark_all_read'
        }))
      }
    } catch (error) {
      console.error('Error marking all as read:', error)
    }
  }

  const deleteNotification = async (notificationId) => {
    try {
      await axios.delete(`http://localhost:8000/api/notifications/${notificationId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(prev => prev.filter(n => n.id !== notificationId))
      // Update unread count if deleted notification was unread
      const deleted = notifications.find(n => n.id === notificationId)
      if (deleted && !deleted.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1))
      }
    } catch (error) {
      console.error('Error deleting notification:', error)
    }
  }

  const updatePreferences = async (newPreferences) => {
    try {
      await axios.put('http://localhost:8000/api/notifications/preferences', newPreferences, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setPreferences(newPreferences)
    } catch (error) {
      console.error('Error updating preferences:', error)
    }
  }

  const handleActionClick = (notification) => {
    if (notification.action_url) {
      window.open(notification.action_url, '_blank')
      markAsRead(notification.id)
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return '#dc3545'
      case 'high': return '#fd7e14'
      case 'normal': return '#007bff'
      case 'low': return '#6c757d'
      default: return '#6c757d'
    }
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'system': return '⚙️'
      case 'chat': return '💬'
      case 'collaborative': return '👥'
      case 'security': return '🔒'
      case 'backup': return '💾'
      default: return '📢'
    }
  }

  const formatTime = (isoString) => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const filteredNotifications = notifications.filter(notification => {
    if (activeTab === 'all') return true
    if (activeTab === 'unread') return !notification.is_read
    return notification.category === activeTab
  })

  if (!isOpen) return null

  return (
    <div className="notification-center">
      {/* Header */}
      <div className="notification-header">
        <div className="header-actions">
          <h3 className="notification-title">
            Notifications {unreadCount > 0 && <span className="unread-count">({unreadCount})</span>}
          </h3>
          <div>
            <button
              onClick={() => setShowPreferences(!showPreferences)}
              className="settings-button"
              title="Settings"
            >
              ⚙️
            </button>
            <button
              onClick={onClose}
              className="close-button"
              title="Close"
            >
              ×
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="tabs">
          {[
            { key: 'all', label: 'All' },
            { key: 'unread', label: 'Unread' },
            { key: 'system', label: 'System' },
            { key: 'chat', label: 'Chat' },
            { key: 'collaborative', label: 'Collaborative' }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key)
                loadNotifications(tab.key)
              }}
              className={`tab-button ${activeTab === tab.key ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="action-buttons">
          <button
            onClick={markAllAsRead}
            disabled={unreadCount === 0}
            className="btn-mark-all"
          >
            Mark All Read
          </button>
        </div>
      </div>

      {/* Preferences Panel */}
      {showPreferences && (
        <div className="preferences-panel">
          <h4 className="preferences-title">Notification Preferences</h4>
          <div className="preferences-list">
            {preferences.map((pref, index) => (
              <div key={index} className="preference-item">
                <label className="preference-label">
                  <input
                    type="checkbox"
                    checked={pref.enabled}
                    onChange={(e) => {
                      const newPrefs = [...preferences]
                      newPrefs[index].enabled = e.target.checked
                      updatePreferences(newPrefs)
                    }}
                    className="preference-checkbox"
                  />
                  {pref.category || pref.template_key || 'General'} {pref.channel && `(${pref.channel})`}
                </label>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notifications List */}
      <div className="notifications-list">
        {loading ? (
          <div className="loading-message">Loading...</div>
        ) : filteredNotifications.length === 0 ? (
          <div className="empty-message">
            No notifications found
          </div>
        ) : (
          filteredNotifications.map(notification => (
            <div
              key={notification.id}
              className={`notification-item ${!notification.is_read ? 'unread' : ''}`}
            >
              {/* Priority indicator */}
              <div className={`priority-indicator priority-${notification.priority}`} />

              {/* Category icon */}
              <div className="category-icon">
                {getCategoryIcon(notification.category)}
              </div>

              {/* Delete button */}
              <button
                onClick={() => deleteNotification(notification.id)}
                className="delete-button"
                title="Delete notification"
              >
                ×
              </button>

              <div className="notification-content">
                <div className="notification-title">
                  {notification.title}
                </div>
                <div className="notification-message">
                  {notification.message}
                </div>
                <div className="notification-footer">
                  <span className="notification-time">
                    {formatTime(notification.created_at)}
                  </span>
                  <div className="notification-actions">
                    {notification.action_url && (
                      <button
                        onClick={() => handleActionClick(notification)}
                        className="btn-action"
                      >
                        {notification.action_text || 'View'}
                      </button>
                    )}
                    {!notification.is_read && (
                      <button
                        onClick={() => markAsRead(notification.id)}
                        className="btn-mark-read"
                      >
                        Mark Read
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default NotificationCenter