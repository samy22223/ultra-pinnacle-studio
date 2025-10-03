import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const CollaborativeEditor = ({ token, conversationId, websocketRef }) => {
  const [documents, setDocuments] = useState([])
  const [currentDocument, setCurrentDocument] = useState(null)
  const [documentContent, setDocumentContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [newDocumentTitle, setNewDocumentTitle] = useState('')
  const [newDocumentType, setNewDocumentType] = useState('prompt')
  const [showNewDocument, setShowNewDocument] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [touchStart, setTouchStart] = useState(null)
  const [touchEnd, setTouchEnd] = useState(null)
  const textareaRef = useRef(null)
  const lastSentContent = useRef('')

  useEffect(() => {
    if (conversationId && token) {
      loadDocuments()
    }
  }, [conversationId, token])

  // Handle WebSocket document updates
  useEffect(() => {
    if (!websocketRef.current) return

    const handleMessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'document_update' && data.content.document_id === currentDocument?.id) {
        // Only update if the content is different and not currently being edited by user
        if (data.content.content !== documentContent && !isEditing) {
          setDocumentContent(data.content.content)
          lastSentContent.current = data.content.content
        }
      }
    }

    websocketRef.current.addEventListener('message', handleMessage)
    return () => {
      if (websocketRef.current) {
        websocketRef.current.removeEventListener('message', handleMessage)
      }
    }
  }, [currentDocument, documentContent, isEditing])

  const loadDocuments = async () => {
    if (!conversationId || !token) return

    try {
      setIsLoading(true)
      const res = await axios.get(`http://localhost:8000/conversations/${conversationId}/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDocuments(res.data)
    } catch (error) {
      console.error('Error loading documents:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadDocument = async (documentId) => {
    try {
      const res = await axios.get(`http://localhost:8000/documents/${documentId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setCurrentDocument(res.data)
      setDocumentContent(res.data.content)
      lastSentContent.current = res.data.content
    } catch (error) {
      console.error('Error loading document:', error)
    }
  }

  const createDocument = async () => {
    if (!newDocumentTitle.trim() || !conversationId) return

    try {
      const res = await axios.post(`http://localhost:8000/conversations/${conversationId}/documents`, {
        title: newDocumentTitle,
        document_type: newDocumentType,
        content: '',
        language: newDocumentType === 'code' ? 'javascript' : null
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      setNewDocumentTitle('')
      setNewDocumentType('prompt')
      setShowNewDocument(false)
      loadDocuments()
      loadDocument(res.data.document_id)
    } catch (error) {
      console.error('Error creating document:', error)
    }
  }

  const updateDocument = async (content) => {
    if (!currentDocument || !websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    // Send collaborative edit via WebSocket
    websocketRef.current.send(JSON.stringify({
      type: 'document_edit',
      content: {
        document_id: currentDocument.id,
        edit_type: 'replace',
        position: 0,
        content: content
      }
    }))

    lastSentContent.current = content
  }

  const handleContentChange = (e) => {
    const newContent = e.target.value
    setDocumentContent(newContent)
    setIsEditing(true)

    // Debounce the update
    clearTimeout(window.documentUpdateTimeout)
    window.documentUpdateTimeout = setTimeout(() => {
      if (newContent !== lastSentContent.current) {
        updateDocument(newContent)
      }
      setIsEditing(false)
    }, 500)
  }

  const handleKeyDown = (e) => {
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      if (documentContent !== lastSentContent.current) {
        updateDocument(documentContent)
      }
    }
  }

  // Touch gesture handlers for collaborative editing
  const handleTouchStart = (e) => {
    setTouchEnd(null)
    setTouchStart(e.targetTouches[0].clientX)
  }

  const handleTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX)
  }

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return

    const distance = touchStart - touchEnd
    const isLeftSwipe = distance > 50
    const isRightSwipe = distance < -50

    // Swipe left to open sidebar, swipe right to close
    if (isLeftSwipe && !sidebarOpen) {
      setSidebarOpen(true)
    } else if (isRightSwipe && sidebarOpen) {
      setSidebarOpen(false)
    }
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const closeSidebar = () => {
    setSidebarOpen(false)
  }

  if (!conversationId) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        Select a conversation to access collaborative documents
      </div>
    )
  }

  return (
    <div className="editor-container">
      {/* Mobile Header */}
      <div className="editor-mobile-header">
        <button className="sidebar-toggle" onClick={toggleSidebar}>
          ☰ Documents
        </button>
        <div className="editor-header-info">
          {currentDocument && (
            <span>{currentDocument.title}</span>
          )}
        </div>
      </div>

      {/* Documents Sidebar */}
      <div className={`editor-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-content">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Documents</h3>
            <div>
              <button
                onClick={() => setShowNewDocument(true)}
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

        {showNewDocument && (
          <div style={{ marginBottom: '1rem' }}>
            <input
              type="text"
              placeholder="Document title..."
              value={newDocumentTitle}
              onChange={(e) => setNewDocumentTitle(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && createDocument()}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}
            />
            <select
              value={newDocumentType}
              onChange={(e) => setNewDocumentType(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}
            >
              <option value="prompt">Prompt</option>
              <option value="code">Code</option>
              <option value="note">Note</option>
            </select>
            <div>
              <button onClick={createDocument} style={{ marginRight: '0.5rem' }}>Create</button>
              <button onClick={() => setShowNewDocument(false)}>Cancel</button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div style={{ textAlign: 'center', color: '#666' }}>Loading...</div>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#666' }}>No documents yet</div>
        ) : (
          documents.map(doc => (
            <div
              key={doc.id}
              onClick={() => {
                loadDocument(doc.id)
                closeSidebar() // Close sidebar on mobile when selecting document
              }}
              style={{
                padding: '0.5rem',
                marginBottom: '0.5rem',
                borderRadius: '4px',
                background: currentDocument?.id === doc.id ? '#e3f2fd' : '#f5f5f5',
                cursor: 'pointer'
              }}
            >
              <div style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>{doc.title}</div>
              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                {doc.document_type} • v{doc.version} • {new Date(doc.updated_at).toLocaleDateString()}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#888' }}>
                by {doc.creator_username}
              </div>
            </div>
          ))
        )}
        </div>
      </div>

      {/* Editor Area */}
      <div className="editor-main">
        {/* Header */}
        <div className="editor-header">
          <h3>
            {currentDocument ? currentDocument.title : 'Select a document'}
          </h3>
          {currentDocument && (
            <div className="editor-meta">
              {currentDocument.document_type} • Version {currentDocument.version}
            </div>
          )}
        </div>

        {/* Editor */}
        <div
          className="editor-content"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          {!currentDocument ? (
            <div className="editor-placeholder">
              Select a document to start editing collaboratively
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              value={documentContent}
              onChange={handleContentChange}
              onKeyDown={handleKeyDown}
              placeholder="Start typing... (Ctrl+S to save)"
              className={`editor-textarea ${currentDocument.document_type === 'code' ? 'code-editor' : ''}`}
            />
          )}
        </div>

        {/* Status */}
        {currentDocument && (
          <div className="editor-status">
            {isEditing ? 'Editing...' : 'Saved'} •
            Last updated: {new Date(currentDocument.updated_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && <div className="editor-sidebar-overlay" onClick={closeSidebar}></div>}
    </div>
  )
}

export default CollaborativeEditor