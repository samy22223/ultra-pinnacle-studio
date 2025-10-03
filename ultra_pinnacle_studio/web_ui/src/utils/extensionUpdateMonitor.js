// Extension Update Monitoring and Auto-Installation System

class ExtensionUpdateMonitor {
  constructor(extensionBridge) {
    this.extensionBridge = extensionBridge
    this.updateCheckInterval = 24 * 60 * 60 * 1000 // 24 hours
    this.updateHistory = this.loadUpdateHistory()
    this.autoUpdateEnabled = true
    this.updateQueue = []
    this.checkTimer = null
  }

  loadUpdateHistory() {
    try {
      return JSON.parse(localStorage.getItem('extension_update_history') || '[]')
    } catch (error) {
      console.error('Failed to load update history:', error)
      return []
    }
  }

  saveUpdateHistory() {
    try {
      localStorage.setItem('extension_update_history', JSON.stringify(this.updateHistory))
    } catch (error) {
      console.error('Failed to save update history:', error)
    }
  }

  startMonitoring() {
    if (this.checkTimer) {
      clearInterval(this.checkTimer)
    }

    // Initial check
    this.checkForUpdates()

    // Set up periodic checks
    this.checkTimer = setInterval(() => {
      this.checkForUpdates()
    }, this.updateCheckInterval)
  }

  stopMonitoring() {
    if (this.checkTimer) {
      clearInterval(this.checkTimer)
      this.checkTimer = null
    }
  }

  async checkForUpdates() {
    console.log('Checking for extension updates...')

    const extensions = this.extensionBridge.getAllExtensions()
    const updatePromises = extensions.map(ext => this.checkExtensionUpdate(ext))

    try {
      const results = await Promise.allSettled(updatePromises)
      const updates = results
        .filter(result => result.status === 'fulfilled' && result.value)
        .map(result => result.value)

      if (updates.length > 0) {
        console.log(`Found ${updates.length} extension updates`)
        this.handleAvailableUpdates(updates)
      } else {
        console.log('All extensions are up to date')
      }

      return updates
    } catch (error) {
      console.error('Error checking for updates:', error)
      return []
    }
  }

  async checkExtensionUpdate(extension) {
    try {
      // Simulate checking for updates (in real implementation, this would check extension stores)
      const currentVersion = extension.version
      const latestVersion = await this.getLatestVersion(extension.id)

      if (this.isNewerVersion(latestVersion, currentVersion)) {
        return {
          extensionId: extension.id,
          extensionName: extension.name,
          currentVersion,
          latestVersion,
          releaseNotes: await this.getReleaseNotes(extension.id, latestVersion),
          downloadUrl: this.getDownloadUrl(extension.id, latestVersion),
          size: this.getUpdateSize(extension.id),
          priority: this.getUpdatePriority(extension),
          detectedAt: new Date().toISOString()
        }
      }

      return null
    } catch (error) {
      console.error(`Error checking update for ${extension.id}:`, error)
      return null
    }
  }

  async getLatestVersion(extensionId) {
    // Simulate API call to get latest version
    // In real implementation, this would check Chrome Web Store, Firefox Add-ons, etc.
    const versions = {
      'google-docs': '1.2.3',
      'google-sheets': '2.1.0',
      'google-drive': '1.5.2',
      'google-calendar': '1.8.1',
      'grammarly': '8.987.1234',
      'evernote': '10.45.2',
      'todoist': '8.2.1',
      'react-devtools': '4.28.5',
      'lighthouse': '11.2.0',
      'axe-devtools': '4.67.1',
      'ublock-origin': '1.54.0'
    }

    return versions[extensionId] || '1.0.0'
  }

  isNewerVersion(latest, current) {
    if (!latest || !current) return false

    const latestParts = latest.split('.').map(Number)
    const currentParts = current.split('.').map(Number)

    for (let i = 0; i < Math.max(latestParts.length, currentParts.length); i++) {
      const latestNum = latestParts[i] || 0
      const currentNum = currentParts[i] || 0

      if (latestNum > currentNum) return true
      if (latestNum < currentNum) return false
    }

    return false
  }

  async getReleaseNotes(extensionId, version) {
    // Simulate fetching release notes
    const notes = {
      'google-docs': 'Improved collaboration features and performance optimizations',
      'grammarly': 'Enhanced AI writing suggestions and new language support',
      'react-devtools': 'Better React 18 support and performance improvements',
      'lighthouse': 'Updated scoring algorithm and new audit categories'
    }

    return notes[extensionId] || 'Bug fixes and performance improvements'
  }

  getDownloadUrl(extensionId, version) {
    // Return appropriate download URLs based on browser
    const browser = this.detectBrowser()

    const urls = {
      chrome: {
        'google-docs': `https://chrome.google.com/webstore/detail/google-docs/${extensionId}`,
        'grammarly': `https://chrome.google.com/webstore/detail/grammarly/${extensionId}`,
        // ... other Chrome URLs
      },
      firefox: {
        'google-docs': `https://addons.mozilla.org/firefox/addon/google-docs/${extensionId}`,
        'grammarly': `https://addons.mozilla.org/firefox/addon/grammarly/${extensionId}`,
        // ... other Firefox URLs
      }
    }

    return urls[browser]?.[extensionId] || '#'
  }

  getUpdateSize(extensionId) {
    // Simulate update sizes in bytes
    const sizes = {
      'google-docs': 2.5 * 1024 * 1024, // 2.5 MB
      'grammarly': 15 * 1024 * 1024,    // 15 MB
      'react-devtools': 8 * 1024 * 1024, // 8 MB
      'lighthouse': 5 * 1024 * 1024     // 5 MB
    }

    return sizes[extensionId] || 1024 * 1024 // 1 MB default
  }

  getUpdatePriority(extension) {
    // Determine update priority based on extension type and usage
    const criticalExtensions = ['ublock-origin', 'axe-devtools']
    const importantExtensions = ['google-docs', 'google-sheets', 'grammarly']

    if (criticalExtensions.includes(extension.id)) return 'critical'
    if (importantExtensions.includes(extension.id)) return 'high'
    if (extension.enabled) return 'medium'
    return 'low'
  }

  detectBrowser() {
    const ua = navigator.userAgent
    if (ua.includes('Firefox/')) return 'firefox'
    if (ua.includes('Chrome/') && !ua.includes('Edg/')) return 'chrome'
    if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'safari'
    if (ua.includes('Edg/')) return 'edge'
    return 'chrome' // default
  }

  handleAvailableUpdates(updates) {
    // Sort updates by priority
    updates.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
      return priorityOrder[b.priority] - priorityOrder[a.priority]
    })

    // Add to update queue
    this.updateQueue.push(...updates)

    // Auto-install critical updates if enabled
    if (this.autoUpdateEnabled) {
      const criticalUpdates = updates.filter(u => u.priority === 'critical')
      criticalUpdates.forEach(update => this.autoInstallUpdate(update))
    }

    // Notify user of available updates
    this.notifyUserOfUpdates(updates)
  }

  async autoInstallUpdate(update) {
    try {
      console.log(`Auto-installing update for ${update.extensionName}...`)

      const success = await this.installUpdate(update)

      if (success) {
        this.logUpdateEvent({
          type: 'auto_install',
          extensionId: update.extensionId,
          fromVersion: update.currentVersion,
          toVersion: update.latestVersion,
          timestamp: new Date().toISOString()
        })
      }

      return success
    } catch (error) {
      console.error(`Auto-install failed for ${update.extensionId}:`, error)
      return false
    }
  }

  async installUpdate(update) {
    try {
      // Simulate installation process
      // In real implementation, this would:
      // 1. Download the update
      // 2. Verify integrity
      // 3. Install/update the extension
      // 4. Restart if necessary

      await new Promise(resolve => setTimeout(resolve, 2000)) // Simulate download time

      // Update extension version in bridge
      const extensions = this.extensionBridge.getAllExtensions()
      const extIndex = extensions.findIndex(ext => ext.id === update.extensionId)

      if (extIndex !== -1) {
        extensions[extIndex].version = update.latestVersion
        // In real implementation, update the actual extension
      }

      return true
    } catch (error) {
      console.error('Update installation failed:', error)
      return false
    }
  }

  notifyUserOfUpdates(updates) {
    const criticalCount = updates.filter(u => u.priority === 'critical').length
    const highCount = updates.filter(u => u.priority === 'high').length

    if (criticalCount > 0) {
      this.showNotification(
        'Critical Extension Updates Available',
        `${criticalCount} critical extension update(s) available. Installing automatically...`,
        'critical'
      )
    } else if (highCount > 0) {
      this.showNotification(
        'Extension Updates Available',
        `${updates.length} extension update(s) available, including ${highCount} high priority.`,
        'high'
      )
    } else {
      this.showNotification(
        'Extension Updates Available',
        `${updates.length} extension update(s) available.`,
        'normal'
      )
    }
  }

  showNotification(title, message, priority) {
    // Use the service worker for notifications if available
    if ('serviceWorker' in navigator && 'Notification' in window) {
      navigator.serviceWorker.ready.then(registration => {
        registration.showNotification(title, {
          body: message,
          icon: '/icon-192.png',
          badge: '/icon-96.png',
          tag: 'extension-updates',
          requireInteraction: priority === 'critical',
          actions: [
            {
              action: 'view',
              title: 'View Updates'
            },
            {
              action: 'dismiss',
              title: 'Dismiss'
            }
          ]
        })
      })
    } else {
      // Fallback to alert
      alert(`${title}: ${message}`)
    }
  }

  logUpdateEvent(event) {
    this.updateHistory.push(event)
    this.saveUpdateHistory()
  }

  getUpdateHistory(extensionId = null) {
    if (extensionId) {
      return this.updateHistory.filter(event => event.extensionId === extensionId)
    }
    return this.updateHistory
  }

  getPendingUpdates() {
    return this.updateQueue
  }

  clearUpdateQueue() {
    this.updateQueue = []
  }

  setAutoUpdate(enabled) {
    this.autoUpdateEnabled = enabled
    localStorage.setItem('extension_auto_update', enabled.toString())
  }

  isAutoUpdateEnabled() {
    return this.autoUpdateEnabled
  }

  setUpdateCheckInterval(hours) {
    this.updateCheckInterval = hours * 60 * 60 * 1000
    this.restartMonitoring()
  }

  restartMonitoring() {
    this.stopMonitoring()
    this.startMonitoring()
  }

  // Manual update check
  async forceUpdateCheck() {
    return await this.checkForUpdates()
  }

  // Get update statistics
  getUpdateStats() {
    const history = this.updateHistory
    const last30Days = new Date()
    last30Days.setDate(last30Days.getDate() - 30)

    const recentUpdates = history.filter(event =>
      new Date(event.timestamp) > last30Days
    )

    return {
      totalUpdates: history.length,
      recentUpdates: recentUpdates.length,
      autoUpdates: history.filter(event => event.type === 'auto_install').length,
      manualUpdates: history.filter(event => event.type === 'manual_install').length,
      failedUpdates: history.filter(event => event.type === 'failed').length,
      lastUpdateCheck: this.getLastUpdateCheck(),
      nextUpdateCheck: new Date(Date.now() + this.updateCheckInterval).toISOString()
    }
  }

  getLastUpdateCheck() {
    // In real implementation, track last check time
    return new Date().toISOString()
  }

  // Export update data
  exportUpdateData() {
    return {
      history: this.updateHistory,
      queue: this.updateQueue,
      settings: {
        autoUpdateEnabled: this.autoUpdateEnabled,
        updateCheckInterval: this.updateCheckInterval
      },
      stats: this.getUpdateStats()
    }
  }
}

export default ExtensionUpdateMonitor