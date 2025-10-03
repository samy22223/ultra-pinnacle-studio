import React, { useState } from 'react'
import Chat from './Chat'
import CollaborativeEditor from './CollaborativeEditor'
import ActivityFeed from './ActivityFeed'
import AIIntegrations from './AIIntegrations'
import UserPresenceIndicators from './UserPresenceIndicators'

const CollaborativeTools = ({ token }) => {
  const [activeTab, setActiveTab] = useState('chat')
  const [currentConversation, setCurrentConversation] = useState(null)
  const [websocketRef, setWebsocketRef] = useState(null)

  const tabs = [
    { id: 'chat', label: 'Chat', component: Chat },
    { id: 'editor', label: 'Documents', component: CollaborativeEditor },
    { id: 'ai', label: 'AI Tools', component: AIIntegrations },
    { id: 'activity', label: 'Activity', component: ActivityFeed }
  ]

  const handleConversationChange = (conversationId) => {
    setCurrentConversation(conversationId)
  }

  const handleWebsocketReady = (wsRef) => {
    setWebsocketRef(wsRef)
  }

  if (!token) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>Collaborative Tools</h2>
        <p>Please login to access collaborative features.</p>
      </div>
    )
  }

  return (
    <div className="collaborative-container">
      {/* Tab Navigation */}
      <div className="tab-navigation">
        <div className="tab-list">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {tabs.map(tab => {
          const Component = tab.component
          return (
            <div
              key={tab.id}
              style={{
                display: activeTab === tab.id ? 'block' : 'none',
                height: '100%'
              }}
            >
              {tab.id === 'chat' ? (
                <Chat
                  token={token}
                  onConversationChange={handleConversationChange}
                  onWebsocketReady={handleWebsocketReady}
                />
              ) : tab.id === 'editor' ? (
                <CollaborativeEditor
                  token={token}
                  conversationId={currentConversation}
                  websocketRef={websocketRef}
                />
              ) : tab.id === 'ai' ? (
                <AIIntegrations token={token} />
              ) : (
                <ActivityFeed
                  token={token}
                  conversationId={currentConversation}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Global Presence Indicator */}
      <div className="presence-indicator">
        <UserPresenceIndicators token={token} conversationId={currentConversation} />
      </div>
    </div>
  )
}

export default CollaborativeTools