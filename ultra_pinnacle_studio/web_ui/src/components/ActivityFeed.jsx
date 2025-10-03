import React, { useState, useEffect } from 'react'
import axios from 'axios'

const ActivityFeed = ({ token, conversationId }) => {
  const [activities, setActivities] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (conversationId && token) {
      loadActivities()
      if (autoRefresh) {
        const interval = setInterval(loadActivities, 10000) // Refresh every 10 seconds
        return () => clearInterval(interval)
      }
    }
  }, [conversationId, token, autoRefresh])

  const loadActivities = async () => {
    if (!conversationId || !token) return

    try {
      setIsLoading(true)
      const res = await axios.get(`http://localhost:8000/conversations/${conversationId}/activities`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setActivities(res.data)
    } catch (error) {
      console.error('Error loading activities:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getActivityIcon = (activityType) => {
    switch (activityType) {
      case 'created': return '🆕'
      case 'joined': return '👋'
      case 'left': return '👋'
      case 'message': return '💬'
      case 'document_created': return '📄'
      case 'document_edited': return '✏️'
      case 'permission_change': return '🔐'
      default: return '📝'
    }
  }

  const getActivityDescription = (activity) => {
    switch (activity.activity_type) {
      case 'created':
        return `${activity.username} created the conversation`
      case 'joined':
        return `${activity.username} joined the conversation`
      case 'left':
        return `${activity.username} left the conversation`
      case 'message':
        return `${activity.username} sent a message`
      case 'document_created':
        return `${activity.username} created document "${activity.details?.title || 'Unknown'}"`
      case 'document_edited':
        return `${activity.username} edited document (v${activity.details?.version || '?'})`
      case 'permission_change':
        return `${activity.username} changed permissions for user ${activity.details?.target_user_id || 'Unknown'}`
      default:
        return `${activity.username} performed ${activity.activity_type}`
    }
  }

  if (!conversationId) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        Select a conversation to view activities
      </div>
    )
  }

  return (
    <div style={{
      height: '80vh',
      border: '1px solid #ccc',
      borderRadius: '8px',
      display: 'flex',
      flexDirection: 'column',
      margin: '1rem'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #ccc',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3>Activity Feed</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '0.8rem' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button
            onClick={loadActivities}
            disabled={isLoading}
            style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              background: '#007bff',
              color: 'white',
              border: 'none',
              fontSize: '0.8rem'
            }}
          >
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Activities */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem'
      }}>
        {activities.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#666', marginTop: '2rem' }}>
            No activities yet
          </div>
        ) : (
          activities.map(activity => (
            <div
              key={activity.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.75rem',
                padding: '0.75rem',
                marginBottom: '0.5rem',
                borderRadius: '6px',
                background: '#f8f9fa',
                border: '1px solid #e9ecef'
              }}
            >
              <div style={{ fontSize: '1.2rem' }}>
                {getActivityIcon(activity.activity_type)}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                  {getActivityDescription(activity)}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#666' }}>
                  {new Date(activity.created_at).toLocaleString()}
                </div>
                {activity.details && Object.keys(activity.details).length > 0 && (
                  <details style={{ marginTop: '0.25rem' }}>
                    <summary style={{ fontSize: '0.7rem', color: '#999', cursor: 'pointer' }}>
                      Details
                    </summary>
                    <pre style={{
                      fontSize: '0.7rem',
                      color: '#666',
                      background: '#f1f3f4',
                      padding: '0.25rem',
                      borderRadius: '3px',
                      marginTop: '0.25rem',
                      overflow: 'auto'
                    }}>
                      {JSON.stringify(activity.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ActivityFeed