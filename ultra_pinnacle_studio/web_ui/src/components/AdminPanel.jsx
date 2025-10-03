import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import AdminGuard from './AdminGuard'
import UserManagement from './admin/UserManagement'
import SystemDashboard from './admin/SystemDashboard'
import PluginManagement from './admin/PluginManagement'
import BackupManagement from './admin/BackupManagement'
import TranslationManagement from './admin/TranslationManagement'
import SystemSettings from './admin/SystemSettings'
import AuditLogViewer from './admin/AuditLogViewer'
import PerformanceDashboard from './admin/PerformanceDashboard'
import APIManagement from './admin/APIManagement'

const AdminPanel = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const adminRoutes = [
    { path: '/admin', label: 'Dashboard', icon: '📊', component: SystemDashboard },
    { path: '/admin/users', label: 'User Management', icon: '👥', component: UserManagement },
    { path: '/admin/plugins', label: 'Plugin Management', icon: '🔌', component: PluginManagement },
    { path: '/admin/backup', label: 'Backup & Restore', icon: '💾', component: BackupManagement },
    { path: '/admin/translations', label: 'Translations', icon: '🌐', component: TranslationManagement },
    { path: '/admin/settings', label: 'System Settings', icon: '⚙️', component: SystemSettings },
    { path: '/admin/audit', label: 'Audit Logs', icon: '📋', component: AuditLogViewer },
    { path: '/admin/performance', label: 'Performance', icon: '📈', component: PerformanceDashboard },
    { path: '/admin/api', label: 'API Management', icon: '🔗', component: APIManagement }
  ]

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const closeSidebar = () => {
    setSidebarOpen(false)
  }

  return (
    <AdminGuard>
      <div className="admin-panel">
        {/* Admin Header */}
        <header className="admin-header">
          <button className="admin-sidebar-toggle" onClick={toggleSidebar}>
            ☰
          </button>
          <h1 className="admin-title">Ultra Pinnacle Admin Panel</h1>
          <div className="admin-header-actions">
            <Link to="/" className="admin-back-link">← Back to Studio</Link>
          </div>
        </header>

        {/* Admin Sidebar */}
        <nav className={`admin-sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="admin-sidebar-header">
            <h2>Admin Menu</h2>
            <button className="admin-sidebar-close" onClick={closeSidebar}>×</button>
          </div>
          <ul className="admin-nav-list">
            {adminRoutes.map(route => (
              <li key={route.path}>
                <Link
                  to={route.path}
                  className={`admin-nav-link ${location.pathname === route.path ? 'active' : ''}`}
                  onClick={closeSidebar}
                >
                  <span className="admin-nav-icon">{route.icon}</span>
                  <span className="admin-nav-text">{route.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sidebar Overlay */}
        {sidebarOpen && <div className="admin-sidebar-overlay" onClick={closeSidebar}></div>}

        {/* Admin Content */}
        <main className="admin-content">
          <Routes>
            {adminRoutes.map(route => (
              <Route
                key={route.path}
                path={route.path.replace('/admin', '') || '/'}
                element={<route.component />}
              />
            ))}
          </Routes>
        </main>
      </div>
    </AdminGuard>
  )
}

export default AdminPanel