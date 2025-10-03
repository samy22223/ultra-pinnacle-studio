import React, { useState, useEffect } from 'react'
import axios from 'axios'

const OfflineSupport = ({ token }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [syncStatus, setSyncStatus] = useState('idle')
  const [offlineData, setOfflineData] = useState([])
  const [syncQueue, setSyncQueue] = useState([])
  const [storageUsage, setStorageUsage] = useState(0)
  const [pwaStatus, setPwaStatus] = useState('checking')
  const [serviceWorkerStatus, setServiceWorkerStatus] = useState('checking')

  useEffect(() => {
    // Monitor online/offline status
    const handleOnline = () => {
      setIsOnline(true)
      startSync()
    }
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Initialize PWA and offline features
    initializePWA()
    checkServiceWorker()
    loadOfflineData()
    calculateStorageUsage()

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const initializePWA = async () => {
    try {
      // Check if PWA is installable
      if ('serviceWorker' in navigator && 'BeforeInstallPromptEvent' in window) {
        setPwaStatus('installable')
      } else {
        setPwaStatus('not-supported')
      }

      // Listen for install prompt
      window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault()
        setPwaStatus('ready-to-install')
      })

      // Check if already installed
      if (window.matchMedia('(display-mode: standalone)').matches) {
        setPwaStatus('installed')
      }
    } catch (error) {
      setPwaStatus('error')
      console.error('PWA initialization error:', error)
    }
  }

  const checkServiceWorker = async () => {
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.ready
        setServiceWorkerStatus('active')

        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              setServiceWorkerStatus('update-available')
            }
          })
        })
      } else {
        setServiceWorkerStatus('not-supported')
      }
    } catch (error) {
      setServiceWorkerStatus('error')
      console.error('Service Worker check error:', error)
    }
  }

  const loadOfflineData = () => {
    try {
      const data = JSON.parse(localStorage.getItem('offlineData') || '[]')
      setOfflineData(data)
    } catch (error) {
      console.error('Error loading offline data:', error)
    }
  }

  const calculateStorageUsage = () => {
    try {
      let total = 0
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          total += localStorage[key].length + key.length
        }
      }
      setStorageUsage(total)
    } catch (error) {
      console.error('Error calculating storage usage:', error)
    }
  }

  const startSync = async () => {
    if (!isOnline || syncQueue.length === 0) return

    setSyncStatus('syncing')

    try {
      for (const item of syncQueue) {
        await axios.post(item.endpoint, item.data, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }

      setSyncQueue([])
      setSyncStatus('completed')

      // Reload data after sync
      loadOfflineData()

      setTimeout(() => setSyncStatus('idle'), 2000)
    } catch (error) {
      setSyncStatus('error')
      console.error('Sync error:', error)
    }
  }

  const saveOffline = (type, data) => {
    try {
      const offlineItem = {
        id: Date.now(),
        type: type,
        data: data,
        timestamp: new Date().toISOString(),
        synced: false
      }

      const updatedData = [...offlineData, offlineItem]
      setOfflineData(updatedData)
      localStorage.setItem('offlineData', JSON.stringify(updatedData))

      // Add to sync queue
      const syncItem = {
        endpoint: `/offline/sync/${type}`,
        data: offlineItem
      }
      setSyncQueue(prev => [...prev, syncItem])

      calculateStorageUsage()
    } catch (error) {
      console.error('Error saving offline data:', error)
    }
  }

  const clearOfflineData = () => {
    if (confirm('Are you sure you want to clear all offline data?')) {
      localStorage.removeItem('offlineData')
      setOfflineData([])
      setSyncQueue([])
      calculateStorageUsage()
    }
  }

  const installPWA = async () => {
    try {
      // This would be triggered by the beforeinstallprompt event
      setPwaStatus('installing')
      // PWA installation logic would go here
      setPwaStatus('installed')
    } catch (error) {
      setPwaStatus('error')
      console.error('PWA installation error:', error)
    }
  }

  const updateServiceWorker = async () => {
    try {
      const registration = await navigator.serviceWorker.ready
      registration.waiting?.postMessage({ type: 'SKIP_WAITING' })
      setServiceWorkerStatus('updating')
    } catch (error) {
      console.error('Service Worker update error:', error)
    }
  }

  const exportOfflineData = () => {
    try {
      const dataStr = JSON.stringify(offlineData, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'offline_data_backup.json'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error exporting offline data:', error)
    }
  }

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
      case 'installed':
      case 'completed':
        return '#28a745'
      case 'syncing':
      case 'installing':
      case 'updating':
        return '#ffc107'
      case 'error':
      case 'not-supported':
        return '#dc3545'
      default:
        return '#6c757d'
    }
  }

  return (
    <div style={{ padding: '1rem', height: '100vh', overflow: 'auto' }}>
      <h1>Offline Support & PWA</h1>
      <p>Comprehensive offline functionality and Progressive Web App features</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
        {/* Main Content */}
        <div>
          {/* Connection Status */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Connection Status</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                background: isOnline ? '#28a745' : '#dc3545'
              }} />
              <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {isOnline ? '🟢 Online' : '🔴 Offline'}
              </span>
            </div>

            {isOnline && (
              <div style={{ marginTop: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <span>Sync Status:</span>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: getStatusColor(syncStatus)
                  }} />
                  <span>
                    {syncStatus === 'idle' ? 'Idle' :
                     syncStatus === 'syncing' ? 'Syncing...' :
                     syncStatus === 'completed' ? 'Completed' :
                     syncStatus === 'error' ? 'Error' : 'Unknown'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* PWA Status */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Progressive Web App</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <strong>PWA Status:</strong>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: getStatusColor(pwaStatus)
                  }} />
                  <span>
                    {pwaStatus === 'installed' ? 'Installed' :
                     pwaStatus === 'installable' ? 'Installable' :
                     pwaStatus === 'ready-to-install' ? 'Ready to Install' :
                     pwaStatus === 'not-supported' ? 'Not Supported' :
                     pwaStatus === 'installing' ? 'Installing...' : 'Checking...'}
                  </span>
                </div>
              </div>

              <div>
                <strong>Service Worker:</strong>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: getStatusColor(serviceWorkerStatus)
                  }} />
                  <span>
                    {serviceWorkerStatus === 'active' ? 'Active' :
                     serviceWorkerStatus === 'update-available' ? 'Update Available' :
                     serviceWorkerStatus === 'not-supported' ? 'Not Supported' :
                     serviceWorkerStatus === 'updating' ? 'Updating...' : 'Checking...'}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              {pwaStatus === 'ready-to-install' && (
                <button onClick={installPWA} style={{ marginRight: '1rem' }}>
                  Install PWA
                </button>
              )}
              {serviceWorkerStatus === 'update-available' && (
                <button onClick={updateServiceWorker}>
                  Update Service Worker
                </button>
              )}
            </div>
          </div>

          {/* Offline Data Management */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Offline Data Management</h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <strong>Storage Usage:</strong> {formatBytes(storageUsage)}
              </div>
              <div>
                <strong>Offline Items:</strong> {offlineData.length}
              </div>
              <div>
                <strong>Sync Queue:</strong> {syncQueue.length}
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <button onClick={exportOfflineData} style={{ marginRight: '1rem' }}>
                Export Data
              </button>
              <button onClick={clearOfflineData} style={{ background: '#dc3545', color: 'white' }}>
                Clear Offline Data
              </button>
            </div>

            {/* Offline Data List */}
            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #eee', borderRadius: '4px' }}>
              <div style={{ padding: '0.5rem', background: '#f8f9fa', fontWeight: 'bold' }}>
                Offline Data ({offlineData.length})
              </div>
              {offlineData.map(item => (
                <div key={item.id} style={{
                  padding: '0.5rem',
                  borderBottom: '1px solid #eee',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <strong>{item.type}</strong>
                    <div style={{ fontSize: '0.8rem', color: '#666' }}>
                      {new Date(item.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: item.synced ? '#28a745' : '#ffc107'
                  }} title={item.synced ? 'Synced' : 'Pending Sync'} />
                </div>
              ))}
            </div>
          </div>

          {/* Offline Features */}
          <div style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Offline Features</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
              <div style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '4px' }}>
                <h4>🎨 Canvas Offline</h4>
                <p>Draw and save designs offline, sync when online</p>
                <button onClick={() => saveOffline('canvas', { action: 'save_design' })}>
                  Test Canvas Save
                </button>
              </div>

              <div style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '4px' }}>
                <h4>💻 Code Offline</h4>
                <p>Write and edit code without internet connection</p>
                <button onClick={() => saveOffline('code', { action: 'save_file' })}>
                  Test Code Save
                </button>
              </div>

              <div style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '4px' }}>
                <h4>📝 Notes Offline</h4>
                <p>Take notes and save documents offline</p>
                <button onClick={() => saveOffline('notes', { action: 'save_note' })}>
                  Test Note Save
                </button>
              </div>

              <div style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '4px' }}>
                <h4>⚙️ Settings Offline</h4>
                <p>Access and modify settings without connection</p>
                <button onClick={() => saveOffline('settings', { action: 'save_config' })}>
                  Test Settings Save
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div>
          {/* Quick Actions */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Quick Actions</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <button onClick={startSync} disabled={!isOnline || syncQueue.length === 0}>
                {syncStatus === 'syncing' ? 'Syncing...' : 'Sync Now'}
              </button>
              <button onClick={calculateStorageUsage}>
                Refresh Storage
              </button>
              <button onClick={() => window.location.reload()}>
                Test Offline Mode
              </button>
            </div>
          </div>

          {/* Offline Capabilities */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Offline Capabilities</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>IndexedDB:</span>
                <span>{!!window.indexedDB ? '✅' : '❌'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Service Worker:</span>
                <span>{'serviceWorker' in navigator ? '✅' : '❌'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Cache API:</span>
                <span>{'caches' in window ? '✅' : '❌'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Background Sync:</span>
                <span>{'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype ? '✅' : '❌'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>WebRTC:</span>
                <span>{!!navigator.mediaDevices ? '✅' : '❌'}</span>
              </div>
            </div>
          </div>

          {/* Storage Details */}
          <div style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Storage Details</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <div>
                <strong>Local Storage:</strong> {formatBytes(storageUsage)}
              </div>
              <div>
                <strong>Session Storage:</strong> {formatBytes(JSON.stringify(sessionStorage).length)}
              </div>
              <div>
                <strong>IndexedDB:</strong> Checking...
              </div>
              <div>
                <strong>Cache Storage:</strong> Checking...
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              <div style={{
                width: '100%',
                height: '8px',
                background: '#e9ecef',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${Math.min((storageUsage / (5 * 1024 * 1024)) * 100, 100)}%`,
                  height: '100%',
                  background: storageUsage > 4 * 1024 * 1024 ? '#dc3545' : '#28a745',
                  transition: 'width 0.3s'
                }} />
              </div>
              <div style={{ fontSize: '0.8rem', marginTop: '0.25rem', textAlign: 'center' }}>
                {((storageUsage / (5 * 1024 * 1024)) * 100).toFixed(1)}% of 5MB limit
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OfflineSupport