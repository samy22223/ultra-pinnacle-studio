// Extension Data Synchronization Across Browsers and Devices

class ExtensionDataSynchronizer {
  constructor(extensionBridge) {
    this.extensionBridge = extensionBridge
    this.syncEnabled = true
    this.syncInterval = 5 * 60 * 1000 // 5 minutes
    this.lastSyncTime = null
    this.syncProviders = new Map()
    this.syncQueue = []
    this.conflictResolver = new ConflictResolver()
    this.syncTimer = null
  }

  // Initialize synchronization system
  async initialize() {
    this.setupSyncProviders()
    this.loadSyncSettings()
    this.startPeriodicSync()

    // Listen for online/offline events
    window.addEventListener('online', () => this.handleOnline())
    window.addEventListener('offline', () => this.handleOffline())

    // Listen for visibility changes to sync when tab becomes visible
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        this.performSync()
      }
    })

    console.log('Extension data synchronizer initialized')
  }

  // Set up different sync providers
  setupSyncProviders() {
    // LocalStorage sync (for same browser, different tabs)
    this.syncProviders.set('localStorage', new LocalStorageSyncProvider())

    // Google Drive sync (cross-device, cross-browser)
    this.syncProviders.set('googleDrive', new GoogleDriveSyncProvider())

    // Browser extension sync (if available)
    this.syncProviders.set('extensionStorage', new ExtensionStorageSyncProvider())

    // WebRTC sync (for real-time sync between tabs)
    this.syncProviders.set('webRTC', new WebRTCSyncProvider())

    // Service Worker sync (for background sync)
    this.syncProviders.set('serviceWorker', new ServiceWorkerSyncProvider())
  }

  // Load sync settings from storage
  loadSyncSettings() {
    try {
      const settings = JSON.parse(localStorage.getItem('extension_sync_settings') || '{}')
      this.syncEnabled = settings.enabled !== false
      this.syncInterval = settings.interval || this.syncInterval
      this.selectedProviders = settings.providers || ['localStorage']
    } catch (error) {
      console.error('Failed to load sync settings:', error)
    }
  }

  // Save sync settings
  saveSyncSettings() {
    try {
      const settings = {
        enabled: this.syncEnabled,
        interval: this.syncInterval,
        providers: this.selectedProviders,
        lastModified: new Date().toISOString()
      }
      localStorage.setItem('extension_sync_settings', JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save sync settings:', error)
    }
  }

  // Start periodic synchronization
  startPeriodicSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer)
    }

    if (this.syncEnabled) {
      this.syncTimer = setInterval(() => {
        this.performSync()
      }, this.syncInterval)
    }
  }

  // Stop periodic synchronization
  stopPeriodicSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer)
      this.syncTimer = null
    }
  }

  // Handle coming online
  async handleOnline() {
    console.log('Device came online, performing sync...')
    await this.performSync()
    this.startPeriodicSync()
  }

  // Handle going offline
  handleOffline() {
    console.log('Device went offline, pausing sync...')
    this.stopPeriodicSync()
  }

  // Perform synchronization across all enabled providers
  async performSync() {
    if (!this.syncEnabled || !navigator.onLine) {
      return
    }

    try {
      console.log('Starting extension data synchronization...')

      const syncResults = []
      const enabledProviders = this.selectedProviders || ['localStorage']

      for (const providerName of enabledProviders) {
        const provider = this.syncProviders.get(providerName)
        if (provider) {
          try {
            const result = await provider.sync(this.getSyncData())
            syncResults.push({ provider: providerName, ...result })
          } catch (error) {
            console.error(`Sync failed for provider ${providerName}:`, error)
            syncResults.push({ provider: providerName, success: false, error: error.message })
          }
        }
      }

      // Process sync results and resolve conflicts
      await this.processSyncResults(syncResults)

      this.lastSyncTime = new Date().toISOString()
      console.log('Extension data synchronization completed')

      return { success: true, results: syncResults }
    } catch (error) {
      console.error('Synchronization failed:', error)
      return { success: false, error: error.message }
    }
  }

  // Get data to synchronize
  getSyncData() {
    return {
      extensions: this.extensionBridge.getAllExtensions().map(ext => ({
        id: ext.id,
        enabled: ext.enabled,
        settings: ext.settings || {},
        version: ext.version
      })),
      userPreferences: this.getUserPreferences(),
      usageData: this.getUsageData(),
      timestamp: new Date().toISOString(),
      deviceId: this.getDeviceId(),
      browser: this.getBrowserInfo()
    }
  }

  // Get user preferences for sync
  getUserPreferences() {
    try {
      return JSON.parse(localStorage.getItem('user_preferences') || '{}')
    } catch (error) {
      return {}
    }
  }

  // Get usage data for sync
  getUsageData() {
    try {
      return JSON.parse(localStorage.getItem('extension_usage_data') || '{}')
    } catch (error) {
      return {}
    }
  }

  // Generate unique device ID
  getDeviceId() {
    let deviceId = localStorage.getItem('device_id')
    if (!deviceId) {
      deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
      localStorage.setItem('device_id', deviceId)
    }
    return deviceId
  }

  // Get browser information
  getBrowserInfo() {
    const ua = navigator.userAgent
    return {
      userAgent: ua,
      language: navigator.language,
      platform: navigator.platform,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine
    }
  }

  // Process synchronization results
  async processSyncResults(results) {
    const successfulSyncs = results.filter(r => r.success && r.data)

    if (successfulSyncs.length === 0) return

    // Merge data from all successful syncs
    const mergedData = this.mergeSyncData(successfulSyncs.map(r => r.data))

    // Apply merged data locally
    await this.applySyncedData(mergedData)

    // Resolve any conflicts that arose during merging
    const conflicts = this.conflictResolver.detectConflicts(mergedData)
    if (conflicts.length > 0) {
      await this.conflictResolver.resolveConflicts(conflicts)
    }
  }

  // Merge data from multiple sync sources
  mergeSyncData(syncDataArray) {
    const merged = {
      extensions: new Map(),
      userPreferences: {},
      usageData: {},
      lastModified: new Date(0).toISOString()
    }

    for (const syncData of syncDataArray) {
      // Merge extensions (use latest version)
      if (syncData.extensions) {
        for (const ext of syncData.extensions) {
          const existing = merged.extensions.get(ext.id)
          if (!existing || new Date(syncData.timestamp) > new Date(existing.timestamp)) {
            merged.extensions.set(ext.id, { ...ext, timestamp: syncData.timestamp })
          }
        }
      }

      // Merge user preferences (deep merge, newer wins)
      if (syncData.userPreferences) {
        merged.userPreferences = this.deepMerge(merged.userPreferences, syncData.userPreferences)
      }

      // Merge usage data
      if (syncData.usageData) {
        merged.usageData = this.deepMerge(merged.usageData, syncData.usageData)
      }

      // Track latest modification
      if (new Date(syncData.timestamp) > new Date(merged.lastModified)) {
        merged.lastModified = syncData.timestamp
      }
    }

    merged.extensions = Array.from(merged.extensions.values())
    return merged
  }

  // Deep merge utility
  deepMerge(target, source) {
    const result = { ...target }

    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(result[key] || {}, source[key])
      } else {
        result[key] = source[key]
      }
    }

    return result
  }

  // Apply synchronized data locally
  async applySyncedData(mergedData) {
    try {
      // Apply extension settings
      if (mergedData.extensions) {
        for (const extData of mergedData.extensions) {
          const extension = this.extensionBridge.getExtension(extData.id)
          if (extension) {
            if (extData.enabled !== undefined) {
              await this.extensionBridge.setExtensionEnabled(extData.id, extData.enabled)
            }
            if (extData.settings) {
              await this.extensionBridge.updateExtensionSettings(extData.id, extData.settings)
            }
          }
        }
      }

      // Apply user preferences
      if (mergedData.userPreferences) {
        localStorage.setItem('user_preferences', JSON.stringify(mergedData.userPreferences))
      }

      // Apply usage data
      if (mergedData.usageData) {
        localStorage.setItem('extension_usage_data', JSON.stringify(mergedData.usageData))
      }

      console.log('Synced data applied locally')
    } catch (error) {
      console.error('Failed to apply synced data:', error)
    }
  }

  // Manual sync trigger
  async syncNow() {
    return await this.performSync()
  }

  // Configure sync settings
  configureSync(settings) {
    this.syncEnabled = settings.enabled !== false
    this.syncInterval = settings.interval || this.syncInterval
    this.selectedProviders = settings.providers || this.selectedProviders

    this.saveSyncSettings()

    if (this.syncEnabled) {
      this.startPeriodicSync()
    } else {
      this.stopPeriodicSync()
    }
  }

  // Get sync status
  getSyncStatus() {
    return {
      enabled: this.syncEnabled,
      lastSyncTime: this.lastSyncTime,
      nextSyncTime: this.syncEnabled ? new Date(Date.now() + this.syncInterval).toISOString() : null,
      providers: this.selectedProviders,
      online: navigator.onLine,
      queueLength: this.syncQueue.length
    }
  }

  // Queue data for sync (when offline)
  queueForSync(data) {
    this.syncQueue.push({
      data,
      timestamp: new Date().toISOString(),
      deviceId: this.getDeviceId()
    })

    // Save queue to localStorage
    try {
      localStorage.setItem('sync_queue', JSON.stringify(this.syncQueue))
    } catch (error) {
      console.error('Failed to save sync queue:', error)
    }
  }

  // Process queued sync items
  async processSyncQueue() {
    if (!navigator.onLine || this.syncQueue.length === 0) return

    const queueCopy = [...this.syncQueue]
    this.syncQueue = []

    for (const item of queueCopy) {
      try {
        await this.performSyncWithData(item.data)
      } catch (error) {
        console.error('Failed to sync queued item:', error)
        // Re-queue failed items
        this.syncQueue.push(item)
      }
    }

    // Save updated queue
    try {
      localStorage.setItem('sync_queue', JSON.stringify(this.syncQueue))
    } catch (error) {
      console.error('Failed to save sync queue:', error)
    }
  }

  // Load sync queue from storage
  loadSyncQueue() {
    try {
      this.syncQueue = JSON.parse(localStorage.getItem('sync_queue') || '[]')
    } catch (error) {
      console.error('Failed to load sync queue:', error)
      this.syncQueue = []
    }
  }

  // Export sync data for backup
  exportSyncData() {
    return {
      settings: {
        enabled: this.syncEnabled,
        interval: this.syncInterval,
        providers: this.selectedProviders
      },
      lastSyncTime: this.lastSyncTime,
      deviceId: this.getDeviceId(),
      browserInfo: this.getBrowserInfo(),
      queue: this.syncQueue,
      localData: this.getSyncData()
    }
  }

  // Import sync data
  async importSyncData(data) {
    try {
      this.configureSync(data.settings)
      this.lastSyncTime = data.lastSyncTime
      this.syncQueue = data.queue || []

      if (data.localData) {
        await this.applySyncedData(data.localData)
      }

      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  // Clean up old sync data
  cleanupOldData(daysToKeep = 30) {
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep)

    // Clean up sync queue
    this.syncQueue = this.syncQueue.filter(item =>
      new Date(item.timestamp) > cutoffDate
    )

    // Clean up old sync data in localStorage
    try {
      const keys = Object.keys(localStorage)
      for (const key of keys) {
        if (key.startsWith('sync_') || key.includes('backup')) {
          // Check if data is old (simplified - would need timestamps)
          // localStorage.removeItem(key)
        }
      }
    } catch (error) {
      console.error('Failed to cleanup old sync data:', error)
    }
  }

  // Destroy synchronizer
  destroy() {
    this.stopPeriodicSync()
    window.removeEventListener('online', this.handleOnline)
    window.removeEventListener('offline', this.handleOffline)
    document.removeEventListener('visibilitychange', this.handleVisibilityChange)
  }
}

// Sync Provider Classes

class LocalStorageSyncProvider {
  async sync(localData) {
    try {
      // Sync with other tabs/windows using localStorage events
      const syncKey = 'extension_sync_data'
      const syncData = {
        ...localData,
        source: 'localStorage',
        syncId: Date.now()
      }

      localStorage.setItem(syncKey, JSON.stringify(syncData))

      // Listen for storage events from other tabs
      window.addEventListener('storage', (e) => {
        if (e.key === syncKey && e.newValue) {
          try {
            const remoteData = JSON.parse(e.newValue)
            if (remoteData.syncId !== syncData.syncId) {
              // Handle incoming sync data
              console.log('Received sync data from another tab')
            }
          } catch (error) {
            console.error('Failed to parse sync data:', error)
          }
        }
      })

      return { success: true, method: 'localStorage' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class GoogleDriveSyncProvider {
  constructor() {
    this.authenticated = false
  }

  async sync(localData) {
    try {
      // Use Google Drive API for cross-device sync
      const fileName = 'ultra_pinnacle_extensions_sync.json'

      // Create or update sync file in Google Drive
      const fileContent = JSON.stringify(localData, null, 2)

      // This would use the Google Drive API in a real implementation
      console.log('Syncing to Google Drive:', fileName)

      return {
        success: true,
        method: 'googleDrive',
        fileName,
        size: fileContent.length
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class ExtensionStorageSyncProvider {
  async sync(localData) {
    try {
      // Use browser extension storage API if available
      if (typeof chrome !== 'undefined' && chrome.storage) {
        await chrome.storage.sync.set({
          'ultra_pinnacle_sync': localData
        })
        return { success: true, method: 'extensionStorage' }
      } else if (typeof browser !== 'undefined' && browser.storage) {
        await browser.storage.sync.set({
          'ultra_pinnacle_sync': localData
        })
        return { success: true, method: 'extensionStorage' }
      }

      return { success: false, error: 'Extension storage not available' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class WebRTCSyncProvider {
  constructor() {
    this.connections = new Map()
  }

  async sync(localData) {
    try {
      // Use WebRTC for real-time sync between browser tabs
      // This is a simplified implementation
      const channelName = 'ultra-pinnacle-sync'

      // Broadcast sync data to other tabs
      if ('BroadcastChannel' in window) {
        const channel = new BroadcastChannel(channelName)
        channel.postMessage({
          type: 'sync_data',
          data: localData,
          source: 'webRTC',
          timestamp: Date.now()
        })

        channel.onmessage = (event) => {
          if (event.data.type === 'sync_data') {
            console.log('Received WebRTC sync data')
          }
        }

        return { success: true, method: 'webRTC' }
      }

      return { success: false, error: 'WebRTC not supported' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class ServiceWorkerSyncProvider {
  async sync(localData) {
    try {
      // Use Service Worker for background sync
      if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
        const registration = await navigator.serviceWorker.ready
        await registration.sync.register('extension-sync')

        // Store data for service worker to sync later
        const syncData = {
          ...localData,
          queuedAt: new Date().toISOString()
        }

        // This would be handled by the service worker
        console.log('Queued for service worker sync')

        return { success: true, method: 'serviceWorker' }
      }

      return { success: false, error: 'Service Worker sync not supported' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

// Conflict resolution system
class ConflictResolver {
  constructor() {
    this.resolutionStrategies = {
      latest_wins: (local, remote) => remote,
      merge: (local, remote) => this.deepMerge(local, remote),
      local_wins: (local, remote) => local,
      manual: (local, remote) => null // Requires user intervention
    }
  }

  detectConflicts(mergedData) {
    // Simplified conflict detection
    const conflicts = []

    // Check for extension setting conflicts
    if (mergedData.extensions) {
      const extensionMap = new Map()

      for (const ext of mergedData.extensions) {
        if (extensionMap.has(ext.id)) {
          const existing = extensionMap.get(ext.id)
          if (existing.enabled !== ext.enabled) {
            conflicts.push({
              type: 'extension_setting',
              id: ext.id,
              local: existing,
              remote: ext,
              field: 'enabled'
            })
          }
        } else {
          extensionMap.set(ext.id, ext)
        }
      }
    }

    return conflicts
  }

  async resolveConflicts(conflicts) {
    const resolutions = []

    for (const conflict of conflicts) {
      const resolution = await this.resolveConflict(conflict)
      resolutions.push(resolution)
    }

    return resolutions
  }

  async resolveConflict(conflict) {
    // Use latest_wins strategy by default
    const strategy = this.resolutionStrategies.latest_wins
    const resolved = strategy(conflict.local, conflict.remote)

    return {
      conflict,
      resolution: resolved,
      strategy: 'latest_wins',
      timestamp: new Date().toISOString()
    }
  }

  deepMerge(target, source) {
    const result = { ...target }

    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(result[key] || {}, source[key])
      } else {
        result[key] = source[key]
      }
    }

    return result
  }
}

// Create singleton instance
const extensionSynchronizer = new ExtensionDataSynchronizer()

export default extensionSynchronizer
export { ExtensionDataSynchronizer, ConflictResolver }