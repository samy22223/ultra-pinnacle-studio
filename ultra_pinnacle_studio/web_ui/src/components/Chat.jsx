import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import UserPresenceIndicators from './UserPresenceIndicators'

const Chat = ({ token, onConversationChange, onWebsocketReady }) => {
  const [conversations, setConversations] = useState([])
  const [currentConversation, setCurrentConversation] = useState(null)
  const [conversationData, setConversationData] = useState(null)
  const [messages, setMessages] = useState([])
  const [message, setMessage] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [newConversationTitle, setNewConversationTitle] = useState('')
  const [showNewConversation, setShowNewConversation] = useState(false)
  const [onlineUsers, setOnlineUsers] = useState([])
  const [userPresence, setUserPresence] = useState({})
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const websocketRef = useRef(null)
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load conversations on component mount
  useEffect(() => {
    if (token) {
      loadConversations()
    }
  }, [token])

  // WebSocket connection management
  useEffect(() => {
    if (currentConversation && token) {
      connectWebSocket()
      loadConversationMessages()
    }

    return () => {
      if (websocketRef.current) {
        // Send offline presence before closing
        if (websocketRef.current.readyState === WebSocket.OPEN) {
          websocketRef.current.send(JSON.stringify({
            type: 'user_presence',
            content: { is_online: false }
          }))
        }
        websocketRef.current.close()
      }
    }
  }, [currentConversation, token])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'user_presence',
          content: { is_online: false }
        }))
      }
    }
  }, [])

  const loadConversations = async () => {
    try {
      const res = await axios.get('http://localhost:8000/conversations', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setConversations(res.data)
    } catch (error) {
      console.error('Error loading conversations:', error)
    }
  }

  const loadConversationMessages = async () => {
    if (!currentConversation) return

    try {
      const res = await axios.get(`http://localhost:8000/conversations/${currentConversation}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setMessages(res.data.messages || [])
      setConversationData(res.data)
    } catch (error) {
      console.error('Error loading messages:', error)
    }
  }

  const connectWebSocket = () => {
    if (websocketRef.current) {
      websocketRef.current.close()
    }

    const wsUrl = `ws://localhost:8000/ws/chat/${currentConversation}?token=${token}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)

      // Send presence update
      ws.send(JSON.stringify({
        type: 'user_presence',
        content: { is_online: true }
      }))

      // Notify parent component
      onWebsocketReady && onWebsocketReady(ws)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'ai_response') {
        setMessages(prev => [...prev, {
          id: data.content.message_id,
          role: 'assistant',
          content: data.content.response,
          user_id: data.content.user_id,
          created_at: data.content.timestamp
        }])
        setIsLoading(false)
      } else if (data.type === 'user_presence_update') {
        // Update user presence
        setUserPresence(prev => ({
          ...prev,
          [data.content.user_id]: {
            is_online: data.content.is_online,
            last_seen: data.content.timestamp,
            current_conversation_id: data.content.conversation_id
          }
        }))
      } else if (data.type === 'document_update') {
        // Handle collaborative document updates
        console.log('Document update received:', data.content)
        // This will be handled by document editing components
      } else if (data.type === 'error') {
        alert('Error: ' + data.content.message)
        setIsLoading(false)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)

      // Send offline presence update if possible
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'user_presence',
          content: { is_online: false }
        }))
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setIsConnected(false)
    }

    websocketRef.current = ws
  }

  const createConversation = async () => {
    if (!newConversationTitle.trim()) return

    try {
      const res = await axios.post('http://localhost:8000/conversations', {
        title: newConversationTitle
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const conversationId = res.data.conversation_id
      setCurrentConversation(conversationId)
      setNewConversationTitle('')
      setShowNewConversation(false)
      loadConversations()
      onConversationChange && onConversationChange(conversationId)
    } catch (error) {
      console.error('Error creating conversation:', error)
    }
  }

  const sendMessage = () => {
    if (!message.trim() || !websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    // Add user message to UI immediately
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    }])

    // Send via WebSocket
    websocketRef.current.send(JSON.stringify({
      type: 'chat_message',
      content: {
        message: message,
        model: 'llama-2-7b-chat'
      }
    }))

    setMessage('')
    setIsLoading(true)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!token) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>AI Chat</h2>
        <p>Please login to use the chat feature.</p>
      </div>
    )
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const closeSidebar = () => {
    setSidebarOpen(false)
  }

  return (
    <div className="chat-container">
      {/* Mobile Sidebar Toggle */}
      <div className="chat-mobile-header">
        <button className="sidebar-toggle" onClick={toggleSidebar}>
          ☰ Conversations
        </button>
        <div className="chat-header-info">
          {currentConversation && conversations.find(c => c.id === currentConversation) && (
            <span>{conversations.find(c => c.id === currentConversation).title}</span>
          )}
        </div>
      </div>

      {/* Conversations Sidebar */}
      <div className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-content">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Conversations</h3>
            <div>
              <button
                onClick={() => setShowNewConversation(true)}
                style={{ padding: '0.5rem', borderRadius: '4px', background: '#007bff', color: 'white', border: 'none', marginRight: '0.5rem' }}
              >
                New
              </button>
              <button
                className="close-sidebar-btn"
                onClick={closeSidebar}
                style={{ padding: '0.5rem', borderRadius: '4px', background: '#6c757d', color: 'white', border: 'none' }}
              >
                ×
              </button>
            </div>
          </div>

        {showNewConversation && (
          <div style={{ marginBottom: '1rem' }}>
            <input
              type="text"
              placeholder="Conversation title..."
              value={newConversationTitle}
              onChange={(e) => setNewConversationTitle(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && createConversation()}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}
            />
            <div>
              <button onClick={createConversation} style={{ marginRight: '0.5rem' }}>Create</button>
              <button onClick={() => setShowNewConversation(false)}>Cancel</button>
            </div>
          </div>
        )}

        {conversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => {
                setCurrentConversation(conv.id)
                onConversationChange && onConversationChange(conv.id)
                closeSidebar() // Close sidebar on mobile when selecting conversation
              }}
              style={{
                padding: '0.5rem',
                marginBottom: '0.5rem',
                borderRadius: '4px',
                background: currentConversation === conv.id ? '#e3f2fd' : '#f5f5f5',
                cursor: 'pointer'
              }}
            >
              <div style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>{conv.title}</div>
              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                {conv.message_count} messages • {conv.participant_count} participants
              </div>
              <div style={{ fontSize: '0.7rem', color: '#888' }}>
                {conv.permission_level} • {new Date(conv.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-main">
        {/* Header */}
        <div style={{
          padding: '1rem',
          borderBottom: '1px solid #ccc',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h3>
              {currentConversation ?
                conversations.find(c => c.id === currentConversation)?.title || 'Chat' :
                'Select a conversation'
              }
            </h3>
            {conversationData && (
              <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.25rem' }}>
                {conversationData.participants?.length || 0} participants • Your role: {conversationData.user_permission}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {/* Online users indicator */}
            {conversationData && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                {conversationData.participants?.filter(p => userPresence[p.user_id]?.is_online).map(p => (
                  <div key={p.user_id} style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: '#28a745',
                    title: `${p.username} is online`
                  }}></div>
                ))}
                <span style={{ fontSize: '0.7rem', color: '#666' }}>
                  {conversationData.participants?.filter(p => userPresence[p.user_id]?.is_online).length || 0} online
                </span>
              </div>
            )}
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: isConnected ? '#28a745' : '#dc3545'
            }}></div>
            <span style={{ fontSize: '0.8rem' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1,
          padding: '1rem',
          overflowY: 'auto',
          background: '#fafafa'
        }}>
          {currentConversation && (
            <UserPresenceIndicators token={token} conversationId={currentConversation} />
          )}
          {!currentConversation ? (
            <div style={{ textAlign: 'center', color: '#666', marginTop: '2rem' }}>
              Select a conversation to start chatting
            </div>
          ) : messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#666', marginTop: '2rem' }}>
              No messages yet. Start the conversation!
            </div>
          ) : (
            messages.map(msg => {
               const isCurrentUser = msg.user_id === (token ? JSON.parse(atob(token.split('.')[1])).sub : null)
               const userInfo = conversationData?.participants?.find(p => p.user_id === msg.user_id)

               return (
                 <div
                   key={msg.id}
                   style={{
                     marginBottom: '1rem',
                     display: 'flex',
                     justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                   }}
                 >
                   <div
                     style={{
                       maxWidth: '70%',
                       padding: '0.75rem',
                       borderRadius: '8px',
                       background: msg.role === 'user' ? (isCurrentUser ? '#007bff' : '#28a745') : '#e9ecef',
                       color: msg.role === 'user' ? 'white' : 'black',
                       whiteSpace: 'pre-wrap'
                     }}
                   >
                     {msg.role === 'user' && userInfo && (
                       <div style={{
                         fontSize: '0.8rem',
                         fontWeight: 'bold',
                         marginBottom: '0.25rem',
                         opacity: 0.9
                       }}>
                         {userInfo.username}
                       </div>
                     )}
                     {msg.content}
                     <div style={{
                       fontSize: '0.7rem',
                       opacity: 0.7,
                       marginTop: '0.25rem'
                     }}>
                       {new Date(msg.created_at).toLocaleTimeString()}
                     </div>
                   </div>
                 </div>
               )
             })
          )}
          {isLoading && (
            <div style={{ textAlign: 'center', color: '#666', marginTop: '1rem' }}>
              AI is thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        {currentConversation && (
          <div style={{
            padding: '1rem',
            borderTop: '1px solid #ccc',
            display: 'flex',
            gap: '0.5rem'
          }}>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows={2}
              style={{
                flex: 1,
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid #ccc',
                resize: 'none'
              }}
              disabled={!isConnected || isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!message.trim() || !isConnected || isLoading}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '4px',
                background: (!message.trim() || !isConnected || isLoading) ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                cursor: (!message.trim() || !isConnected || isLoading) ? 'not-allowed' : 'pointer'
              }}
            >
              Send
            </button>
          </div>
        )}
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && <div className="chat-sidebar-overlay" onClick={closeSidebar}></div>}
    </div>
  )
}

export default Chat