import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import './SupportChat.css';

const SupportChat = ({ isOpen, onClose }) => {
  const { t } = useTranslation('common');
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showNewChatForm, setShowNewChatForm] = useState(false);
  const [newChatSubject, setNewChatSubject] = useState('');
  const [newChatCategory, setNewChatCategory] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      loadChats();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedChat) {
      loadMessages(selectedChat.id);
      markMessagesAsRead(selectedChat.id);
    }
  }, [selectedChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadChats = async () => {
    try {
      const response = await fetch('/api/support/chats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setChats(data);
    } catch (error) {
      console.error('Error loading chats:', error);
    }
  };

  const loadMessages = async (chatId) => {
    try {
      const response = await fetch(`/api/support/chats/${chatId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const markMessagesAsRead = async (chatId) => {
    // This is handled automatically when loading messages
    // The API marks agent messages as read when fetching
  };

  const createNewChat = async () => {
    if (!newChatSubject.trim()) return;

    try {
      const response = await fetch('/api/support/chats', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subject: newChatSubject,
          category: newChatCategory || null
        })
      });

      const data = await response.json();
      setShowNewChatForm(false);
      setNewChatSubject('');
      setNewChatCategory('');
      loadChats(); // Refresh chat list

      // Select the new chat
      setSelectedChat({
        id: data.chat_id,
        subject: newChatSubject,
        category: newChatCategory,
        status: 'open'
      });
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedChat) return;

    setIsLoading(true);
    try {
      await fetch(`/api/support/chats/${selectedChat.id}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: newMessage,
          message_type: 'text'
        })
      });

      // Add message to local state immediately
      const message = {
        id: Date.now(), // Temporary ID
        content: newMessage,
        is_from_user: true,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, message]);
      setNewMessage('');

      // Refresh messages to get server response
      setTimeout(() => loadMessages(selectedChat.id), 1000);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return '#10b981';
      case 'in_progress': return '#f59e0b';
      case 'resolved': return '#3b82f6';
      case 'closed': return '#6b7280';
      default: return '#6b7280';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="support-chat-overlay">
      <div className="support-chat">
        <div className="chat-header">
          <div className="chat-title">
            <h2>{t('support.title', 'Support Chat')}</h2>
            <p>{t('support.subtitle', 'Get help from our support team')}</p>
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="chat-content">
          <div className="chat-sidebar">
            <div className="sidebar-header">
              <h3>{t('support.yourChats', 'Your Chats')}</h3>
              <button
                className="new-chat-button"
                onClick={() => setShowNewChatForm(true)}
              >
                + {t('support.newChat', 'New Chat')}
              </button>
            </div>

            <div className="chat-list">
              {chats.map(chat => (
                <div
                  key={chat.id}
                  className={`chat-item ${selectedChat?.id === chat.id ? 'active' : ''}`}
                  onClick={() => setSelectedChat(chat)}
                >
                  <div className="chat-item-header">
                    <span className="chat-subject">{chat.subject || t('support.noSubject', 'No Subject')}</span>
                    <span
                      className="chat-status"
                      style={{ backgroundColor: getStatusColor(chat.status) }}
                    >
                      {chat.status}
                    </span>
                  </div>
                  <div className="chat-preview">
                    {chat.latest_message?.content ? (
                      <span className="last-message">
                        {chat.latest_message.content.length > 50
                          ? chat.latest_message.content.substring(0, 50) + '...'
                          : chat.latest_message.content
                        }
                      </span>
                    ) : (
                      <span className="no-messages">{t('support.noMessages', 'No messages yet')}</span>
                    )}
                  </div>
                  <div className="chat-meta">
                    <span className="last-activity">
                      {chat.updated_at ? formatTime(chat.updated_at) : ''}
                    </span>
                    {chat.unread_count > 0 && (
                      <span className="unread-badge">{chat.unread_count}</span>
                    )}
                  </div>
                </div>
              ))}

              {chats.length === 0 && (
                <div className="no-chats">
                  <p>{t('support.noChats', 'No support chats yet')}</p>
                  <button
                    className="start-chat-button"
                    onClick={() => setShowNewChatForm(true)}
                  >
                    {t('support.startFirstChat', 'Start your first chat')}
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="chat-main">
            {showNewChatForm ? (
              <div className="new-chat-form">
                <h3>{t('support.startNewChat', 'Start a New Support Chat')}</h3>
                <div className="form-group">
                  <label>{t('support.subject', 'Subject')}</label>
                  <input
                    type="text"
                    value={newChatSubject}
                    onChange={(e) => setNewChatSubject(e.target.value)}
                    placeholder={t('support.subjectPlaceholder', 'Brief description of your issue')}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label>{t('support.category', 'Category (Optional)')}</label>
                  <select
                    value={newChatCategory}
                    onChange={(e) => setNewChatCategory(e.target.value)}
                    className="form-select"
                  >
                    <option value="">{t('support.selectCategory', 'Select a category')}</option>
                    <option value="technical">Technical Issue</option>
                    <option value="billing">Billing</option>
                    <option value="feature">Feature Request</option>
                    <option value="bug">Bug Report</option>
                    <option value="general">General</option>
                  </select>
                </div>
                <div className="form-actions">
                  <button
                    className="cancel-button"
                    onClick={() => setShowNewChatForm(false)}
                  >
                    {t('support.cancel', 'Cancel')}
                  </button>
                  <button
                    className="create-button"
                    onClick={createNewChat}
                    disabled={!newChatSubject.trim()}
                  >
                    {t('support.createChat', 'Create Chat')}
                  </button>
                </div>
              </div>
            ) : selectedChat ? (
              <div className="chat-conversation">
                <div className="conversation-header">
                  <h3>{selectedChat.subject || t('support.chat', 'Chat')}</h3>
                  <div className="chat-info">
                    <span className="chat-status-display" style={{ color: getStatusColor(selectedChat.status) }}>
                      {selectedChat.status.replace('_', ' ').toUpperCase()}
                    </span>
                    {selectedChat.category && (
                      <span className="chat-category">{selectedChat.category}</span>
                    )}
                  </div>
                </div>

                <div className="messages-container">
                  {messages.length === 0 ? (
                    <div className="no-messages">
                      <p>{t('support.startConversation', 'Start the conversation by sending a message')}</p>
                    </div>
                  ) : (
                    messages.map(message => (
                      <div
                        key={message.id}
                        className={`message ${message.is_from_user ? 'user' : 'agent'}`}
                      >
                        <div className="message-content">
                          <p>{message.content}</p>
                          <span className="message-time">
                            {formatTime(message.created_at)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {selectedChat.status !== 'closed' && (
                  <div className="message-input">
                    <textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder={t('support.typeMessage', 'Type your message...')}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                      className="message-textarea"
                      rows="3"
                    />
                    <button
                      className="send-button"
                      onClick={sendMessage}
                      disabled={!newMessage.trim() || isLoading}
                    >
                      {isLoading ? '...' : t('support.send', 'Send')}
                    </button>
                  </div>
                )}

                {selectedChat.status === 'closed' && (
                  <div className="chat-closed-notice">
                    <p>{t('support.chatClosed', 'This chat has been closed')}</p>
                    <button
                      className="new-chat-button"
                      onClick={() => setShowNewChatForm(true)}
                    >
                      {t('support.startNewChat', 'Start New Chat')}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="no-chat-selected">
                <div className="empty-state">
                  <div className="empty-icon">💬</div>
                  <h3>{t('support.selectChat', 'Select a Chat')}</h3>
                  <p>{t('support.selectChatDesc', 'Choose a chat from the sidebar or start a new one')}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupportChat;