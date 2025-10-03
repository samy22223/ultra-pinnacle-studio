import React, { useState, useEffect } from 'react'
import axios from 'axios'

const UserPresenceIndicators = ({ token, conversationId }) => {
  const [onlineUsers, setOnlineUsers] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (token) {
      loadOnlineUsers()
      // Refresh online users every 30 seconds
      const interval = setInterval(loadOnlineUsers, 30000)
      return () => clearInterval(interval)
    }
  }, [token])

  const loadOnlineUsers = async () => {
    if (!token) return

    try {
      setIsLoading(true)
      const res = await axios.get('http://localhost:8000/presence/online-users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setOnlineUsers(res.data)
    } catch (error) {
      console.error('Error loading online users:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const usersInConversation = onlineUsers.filter(user =>
    user.current_conversation_id === conversationId
  )

  if (usersInConversation.length === 0) {
    return null
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem',
      background: '#f8f9fa',
      borderRadius: '4px',
      marginBottom: '1rem'
    }}>
      <div style={{ fontSize: '0.8rem', color: '#666' }}>
        Online in this conversation:
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        {usersInConversation.map(user => (
          <div key={user.user_id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            background: '#e3f2fd',
            padding: '0.25rem 0.5rem',
            borderRadius: '12px',
            fontSize: '0.8rem'
          }}>
            <div style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#28a745'
            }}></div>
            {user.username}
          </div>
        ))}
      </div>
      {isLoading && (
        <div style={{ fontSize: '0.7rem', color: '#999' }}>
          updating...
        </div>
      )}
    </div>
  )
}

export default UserPresenceIndicators