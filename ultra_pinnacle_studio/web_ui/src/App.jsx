import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Chat from './components/Chat'
import Analytics from './components/Analytics'
import CollaborativeTools from './components/CollaborativeTools'
import AIIntegrations from './components/AIIntegrations'
import PluginManager from './components/PluginManager'
import BackupManager from './components/BackupManager'
import Auth, { AuthProvider, useAuth } from './components/Auth'
import LanguageSwitcher from './components/LanguageSwitcher'
import TranslationManager from './components/TranslationManager'
import Search from './components/Search'
import AdminPanel from './components/AdminPanel'
import ExtensionManager from './components/ExtensionManager'
import { initializeBrowserCompatibility } from './utils/browserCompatibility'
import extensionBridge from './utils/extensionBridge'
import './index.css'
import './i18n' // Initialize i18n

const AppContent = () => {
  const { t, i18n } = useTranslation('common')
  const { user, logout, isAuthenticated } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  // Initialize browser compatibility and extensions on app start
  useEffect(() => {
    const initApp = async () => {
      await initializeBrowserCompatibility()
      await extensionBridge.initialize()
    }
    initApp()
  }, [])

  // Handle OAuth callback
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search)
      const code = urlParams.get('code')
      const state = urlParams.get('state')

      if (code && state) {
        try {
          // This would be handled by the OAuth callback endpoint
          // For now, we'll redirect to auth page
          navigate('/auth')
        } catch (error) {
          console.error('OAuth callback error:', error)
          navigate('/auth')
        }
      }
    }

    handleOAuthCallback()
  }, [navigate])

  const handleLogout = () => {
    logout()
    navigate('/auth')
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const closeSidebar = () => {
    setSidebarOpen(false)
  }

  const navItems = [
    { path: '/', label: t('navigation.dashboard'), icon: '📊' },
    { path: '/search', label: t('navigation.search', 'Search'), icon: '🔍' },
    { path: '/chat', label: t('navigation.chat'), icon: '💬' },
    { path: '/analytics', label: t('navigation.analytics'), icon: '📈' },
    { path: '/ai', label: t('navigation.aiFeatures'), icon: '🤖' },
    { path: '/plugins', label: t('navigation.plugins'), icon: '🔌' },
    { path: '/extensions', label: 'Extensions', icon: '🧩' },
    { path: '/backup', label: t('navigation.backup'), icon: '💾' },
    { path: '/collaborative', label: t('navigation.collaborative'), icon: '🤝' },
    { path: '/translations', label: 'Translations', icon: '🌐' },
    { path: '/auth', label: t('navigation.auth'), icon: '🔐', auth: false },
    { path: '/admin', label: 'Admin Panel', icon: '⚙️', adminOnly: true }
  ]

  // Redirect to auth if not authenticated (except for auth page)
  if (!isAuthenticated && location.pathname !== '/auth') {
    return <Auth />
  }

  // Redirect to dashboard if authenticated and on auth page
  if (isAuthenticated && location.pathname === '/auth') {
    navigate('/')
    return null
  }

  return (
    <div className="app">
      {/* Mobile Header */}
      <header className="mobile-header">
        <button className="hamburger" onClick={toggleSidebar}>
          ☰
        </button>
        <h1 className="app-title">{t('app.title')}</h1>
        <div className="header-controls">
          <LanguageSwitcher />
          {isAuthenticated && (
            <div className="user-info">
              <span>Welcome, {user?.username}</span>
              <button className="logout-btn" onClick={handleLogout}>
                {t('buttons.logout')}
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Sidebar Navigation */}
      <nav className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>{t('navigation.navigation')}</h2>
          <button className="close-sidebar" onClick={closeSidebar}>×</button>
        </div>
        <ul className="nav-list">
           {navItems.map(item => {
             // Skip auth page if authenticated
             if (item.auth === false && isAuthenticated) return null

             // Check if user is admin for admin-only items
             if (item.adminOnly && (!user?.roles?.includes('admin') && !user?.is_superuser)) {
               return null
             }

             return (
               <li key={item.path}>
                 <Link
                   to={item.path}
                   className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                   onClick={closeSidebar}
                 >
                   <span className="nav-icon">{item.icon}</span>
                   <span className="nav-text">{item.label}</span>
                 </Link>
               </li>
             )
           })}
         </ul>
         {isAuthenticated && (
           <div className="sidebar-footer">
             <div className="user-info-sidebar">
               <p>Logged in as: {user?.username}</p>
               <p>Role: {user?.roles?.join(', ') || 'User'}</p>
             </div>
             <button className="logout-btn-full" onClick={handleLogout}>
               {t('buttons.logout')}
             </button>
           </div>
         )}
      </nav>

      {/* Overlay for mobile */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={closeSidebar}></div>}

      {/* Main Content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={
            <div className="dashboard">
              <h1>{t('app.welcome')}</h1>
              <div className="dashboard-grid">
                <div className="dashboard-card">
                  <h3>{t('dashboard.aiChat.title')}</h3>
                  <p>{t('dashboard.aiChat.description')}</p>
                  <Link to="/chat" className="card-link">{t('dashboard.aiChat.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>{t('dashboard.analytics.title')}</h3>
                  <p>{t('dashboard.analytics.description')}</p>
                  <Link to="/analytics" className="card-link">{t('dashboard.analytics.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>{t('dashboard.aiFeatures.title')}</h3>
                  <p>{t('dashboard.aiFeatures.description')}</p>
                  <Link to="/ai" className="card-link">{t('dashboard.aiFeatures.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>{t('dashboard.collaborativeTools.title')}</h3>
                  <p>{t('dashboard.collaborativeTools.description')}</p>
                  <Link to="/collaborative" className="card-link">{t('dashboard.collaborativeTools.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>{t('dashboard.pluginManager.title')}</h3>
                  <p>{t('dashboard.pluginManager.description')}</p>
                  <Link to="/plugins" className="card-link">{t('dashboard.pluginManager.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>{t('dashboard.backupManagement.title')}</h3>
                  <p>{t('dashboard.backupManagement.description')}</p>
                  <Link to="/backup" className="card-link">{t('dashboard.backupManagement.link')}</Link>
                </div>
                <div className="dashboard-card">
                  <h3>Translation Manager</h3>
                  <p>Manage translations and localization for the application</p>
                  <Link to="/translations" className="card-link">Manage Translations</Link>
                </div>
              </div>
            </div>
          } />
          <Route path="/search" element={<Search />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/ai" element={<AIIntegrations />} />
          <Route path="/plugins" element={<PluginManager />} />
          <Route path="/extensions" element={<ExtensionManager />} />
          <Route path="/backup" element={<BackupManager />} />
          <Route path="/collaborative" element={<CollaborativeTools />} />
           <Route path="/translations" element={<TranslationManager />} />
           <Route path="/auth" element={<Auth />} />
           <Route path="/admin/*" element={<AdminPanel />} />
        </Routes>
      </main>
    </div>
  )
}

const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App