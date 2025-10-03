// Browser Extension Marketplace Integration System

class ExtensionMarketplace {
  constructor(extensionBridge) {
    this.extensionBridge = extensionBridge
    this.marketplaces = new Map()
    this.installedExtensions = new Set()
    this.searchCache = new Map()
    this.reviewCache = new Map()
    this.categoryFilters = new Set()
  }

  // Initialize marketplace system
  async initialize() {
    this.setupMarketplaces()
    await this.loadInstalledExtensions()
    this.initializeCategoryFilters()

    console.log('Extension marketplace initialized')
  }

  // Set up different browser marketplaces
  setupMarketplaces() {
    this.marketplaces.set('chrome', new ChromeWebStore())
    this.marketplaces.set('firefox', new FirefoxAddons())
    this.marketplaces.set('edge', new MicrosoftEdgeAddons())
    this.marketplaces.set('opera', new OperaAddons())
    this.marketplaces.set('safari', new SafariExtensions())
  }

  // Load list of installed extensions
  async loadInstalledExtensions() {
    const extensions = this.extensionBridge.getAllExtensions()
    this.installedExtensions = new Set(extensions.map(ext => ext.id))
  }

  // Initialize category filters
  initializeCategoryFilters() {
    this.categoryFilters = new Set([
      'productivity',
      'developer',
      'accessibility',
      'privacy',
      'writing',
      'communication',
      'entertainment',
      'shopping',
      'social',
      'news',
      'education',
      'utilities'
    ])
  }

  // Get current browser marketplace
  getCurrentMarketplace() {
    const browser = this.detectBrowser()
    return this.marketplaces.get(browser) || this.marketplaces.get('chrome')
  }

  // Detect current browser
  detectBrowser() {
    const ua = navigator.userAgent
    if (ua.includes('Firefox/')) return 'firefox'
    if (ua.includes('Chrome/') && !ua.includes('Edg/')) return 'chrome'
    if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'safari'
    if (ua.includes('Edg/')) return 'edge'
    if (ua.includes('OPR/') || ua.includes('Opera/')) return 'opera'
    return 'chrome'
  }

  // Search for extensions across marketplaces
  async searchExtensions(query, options = {}) {
    const cacheKey = `${query}_${JSON.stringify(options)}`

    if (this.searchCache.has(cacheKey)) {
      return this.searchCache.get(cacheKey)
    }

    try {
      const marketplace = this.getCurrentMarketplace()
      const results = await marketplace.search(query, options)

      // Filter out already installed extensions if requested
      if (options.excludeInstalled) {
        results.items = results.items.filter(item =>
          !this.installedExtensions.has(item.id)
        )
      }

      // Add installation status
      results.items = results.items.map(item => ({
        ...item,
        installed: this.installedExtensions.has(item.id),
        compatible: this.checkCompatibility(item)
      }))

      // Cache results for 5 minutes
      this.searchCache.set(cacheKey, results)
      setTimeout(() => this.searchCache.delete(cacheKey), 5 * 60 * 1000)

      return results
    } catch (error) {
      console.error('Extension search failed:', error)
      return { items: [], total: 0, error: error.message }
    }
  }

  // Get extension details
  async getExtensionDetails(extensionId) {
    try {
      const marketplace = this.getCurrentMarketplace()
      const details = await marketplace.getDetails(extensionId)

      if (details) {
        return {
          ...details,
          installed: this.installedExtensions.has(extensionId),
          compatible: this.checkCompatibility(details),
          reviews: await this.getExtensionReviews(extensionId),
          alternatives: await this.getAlternativeExtensions(extensionId)
        }
      }

      return null
    } catch (error) {
      console.error('Failed to get extension details:', error)
      return null
    }
  }

  // Install extension from marketplace
  async installExtension(extensionId, options = {}) {
    try {
      const marketplace = this.getCurrentMarketplace()
      const installUrl = await marketplace.getInstallUrl(extensionId)

      if (installUrl) {
        if (options.openInNewTab) {
          window.open(installUrl, '_blank')
        } else {
          window.location.href = installUrl
        }

        // Track installation attempt
        this.trackInstallation(extensionId, 'initiated')

        return { success: true, installUrl }
      }

      return { success: false, error: 'Install URL not available' }
    } catch (error) {
      console.error('Extension installation failed:', error)
      return { success: false, error: error.message }
    }
  }

  // Check extension compatibility
  checkCompatibility(extension) {
    const browser = this.detectBrowser()
    const supportedBrowsers = extension.supportedBrowsers || []

    return supportedBrowsers.includes(browser) || supportedBrowsers.length === 0
  }

  // Get extension reviews
  async getExtensionReviews(extensionId) {
    const cacheKey = `reviews_${extensionId}`

    if (this.reviewCache.has(cacheKey)) {
      return this.reviewCache.get(cacheKey)
    }

    try {
      const marketplace = this.getCurrentMarketplace()
      const reviews = await marketplace.getReviews(extensionId)

      // Cache reviews for 30 minutes
      this.reviewCache.set(cacheKey, reviews)
      setTimeout(() => this.reviewCache.delete(cacheKey), 30 * 60 * 1000)

      return reviews
    } catch (error) {
      console.error('Failed to get extension reviews:', error)
      return { items: [], averageRating: 0, total: 0 }
    }
  }

  // Get alternative extensions
  async getAlternativeExtensions(extensionId) {
    try {
      const details = await this.getExtensionDetails(extensionId)
      if (!details) return []

      // Search for extensions in same category
      const alternatives = await this.searchExtensions('', {
        category: details.category,
        limit: 5,
        excludeInstalled: true
      })

      return alternatives.items.filter(item => item.id !== extensionId)
    } catch (error) {
      console.error('Failed to get alternative extensions:', error)
      return []
    }
  }

  // Get featured/popular extensions
  async getFeaturedExtensions(options = {}) {
    try {
      const marketplace = this.getCurrentMarketplace()
      const featured = await marketplace.getFeatured(options)

      return featured.map(item => ({
        ...item,
        installed: this.installedExtensions.has(item.id),
        compatible: this.checkCompatibility(item)
      }))
    } catch (error) {
      console.error('Failed to get featured extensions:', error)
      return []
    }
  }

  // Get extensions by category
  async getExtensionsByCategory(category, options = {}) {
    return await this.searchExtensions('', {
      category,
      ...options
    })
  }

  // Track extension installation
  trackInstallation(extensionId, status) {
    const trackingData = {
      extensionId,
      status, // 'initiated', 'completed', 'failed'
      timestamp: new Date().toISOString(),
      browser: this.detectBrowser(),
      source: 'marketplace'
    }

    // Store in localStorage for analytics
    try {
      const installations = JSON.parse(localStorage.getItem('extension_installations') || '[]')
      installations.push(trackingData)

      // Keep only last 100 installations
      if (installations.length > 100) {
        installations.splice(0, installations.length - 100)
      }

      localStorage.setItem('extension_installations', JSON.stringify(installations))
    } catch (error) {
      console.error('Failed to track installation:', error)
    }
  }

  // Get installation analytics
  getInstallationAnalytics() {
    try {
      const installations = JSON.parse(localStorage.getItem('extension_installations') || '[]')

      const analytics = {
        total: installations.length,
        completed: installations.filter(i => i.status === 'completed').length,
        failed: installations.filter(i => i.status === 'failed').length,
        byBrowser: {},
        byCategory: {},
        recent: installations.slice(-10)
      }

      // Group by browser
      installations.forEach(inst => {
        analytics.byBrowser[inst.browser] = (analytics.byBrowser[inst.browser] || 0) + 1
      })

      return analytics
    } catch (error) {
      console.error('Failed to get installation analytics:', error)
      return { total: 0, completed: 0, failed: 0 }
    }
  }

  // Get marketplace statistics
  async getMarketplaceStats() {
    try {
      const marketplace = this.getCurrentMarketplace()
      const stats = await marketplace.getStats()

      return {
        ...stats,
        installedCount: this.installedExtensions.size,
        browser: this.detectBrowser()
      }
    } catch (error) {
      console.error('Failed to get marketplace stats:', error)
      return {
        totalExtensions: 0,
        categories: {},
        browser: this.detectBrowser()
      }
    }
  }

  // Clear caches
  clearCaches() {
    this.searchCache.clear()
    this.reviewCache.clear()
  }

  // Export marketplace data
  exportMarketplaceData() {
    return {
      installedExtensions: Array.from(this.installedExtensions),
      searchCache: Array.from(this.searchCache.entries()),
      analytics: this.getInstallationAnalytics(),
      browser: this.detectBrowser(),
      timestamp: new Date().toISOString()
    }
  }
}

// Marketplace Provider Classes

class ChromeWebStore {
  constructor() {
    this.baseUrl = 'https://chrome.google.com/webstore'
    this.apiUrl = 'https://chrome.google.com/webstore/api'
  }

  async search(query, options = {}) {
    // Simulate Chrome Web Store search
    // In real implementation, would use Chrome Web Store API or scraping
    const mockResults = [
      {
        id: 'grammarly',
        name: 'Grammarly',
        description: 'Writing assistant that helps you write clearly and error-free',
        category: 'writing',
        rating: 4.5,
        users: '10,000,000+',
        supportedBrowsers: ['chrome', 'firefox', 'edge', 'safari'],
        icon: '/icons/grammarly.png',
        installUrl: 'https://chrome.google.com/webstore/detail/grammarly/kbfnbcaeplbcioakkpcpgfkobkghlhen'
      },
      {
        id: 'ublock-origin',
        name: 'uBlock Origin',
        description: 'Efficient ad blocker that blocks ads and trackers',
        category: 'privacy',
        rating: 4.8,
        users: '5,000,000+',
        supportedBrowsers: ['chrome', 'firefox', 'edge'],
        icon: '/icons/ublock.png',
        installUrl: 'https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm'
      }
    ]

    return {
      items: mockResults.filter(item =>
        item.name.toLowerCase().includes(query.toLowerCase()) ||
        item.description.toLowerCase().includes(query.toLowerCase())
      ),
      total: mockResults.length,
      query,
      marketplace: 'chrome'
    }
  }

  async getDetails(extensionId) {
    // Simulate getting extension details
    const extensions = {
      'grammarly': {
        id: 'grammarly',
        name: 'Grammarly',
        description: 'Writing assistant that helps you write clearly and error-free',
        category: 'writing',
        rating: 4.5,
        users: '10,000,000+',
        version: '8.987.1234',
        lastUpdated: '2024-01-15',
        size: '15 MB',
        permissions: ['storage', 'activeTab', 'contextMenus'],
        supportedBrowsers: ['chrome', 'firefox', 'edge', 'safari']
      },
      'ublock-origin': {
        id: 'ublock-origin',
        name: 'uBlock Origin',
        description: 'Efficient ad blocker that blocks ads and trackers',
        category: 'privacy',
        rating: 4.8,
        users: '5,000,000+',
        version: '1.54.0',
        lastUpdated: '2024-01-10',
        size: '2 MB',
        permissions: ['storage', 'webRequest', 'webRequestBlocking'],
        supportedBrowsers: ['chrome', 'firefox', 'edge']
      }
    }

    return extensions[extensionId] || null
  }

  async getInstallUrl(extensionId) {
    const urls = {
      'grammarly': 'https://chrome.google.com/webstore/detail/grammarly/kbfnbcaeplbcioakkpcpgfkobkghlhen',
      'ublock-origin': 'https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm'
    }

    return urls[extensionId] || null
  }

  async getReviews(extensionId) {
    // Mock reviews data
    return {
      items: [
        {
          user: 'John D.',
          rating: 5,
          comment: 'Excellent writing assistant!',
          date: '2024-01-20'
        },
        {
          user: 'Sarah M.',
          rating: 4,
          comment: 'Very helpful for catching errors',
          date: '2024-01-18'
        }
      ],
      averageRating: 4.5,
      total: 1250
    }
  }

  async getFeatured(options = {}) {
    // Return featured extensions
    return [
      {
        id: 'grammarly',
        name: 'Grammarly',
        category: 'writing',
        featured: true
      },
      {
        id: 'ublock-origin',
        name: 'uBlock Origin',
        category: 'privacy',
        featured: true
      }
    ]
  }

  async getStats() {
    return {
      totalExtensions: 180000,
      categories: {
        productivity: 25000,
        developer: 15000,
        privacy: 8000,
        writing: 5000
      }
    }
  }
}

class FirefoxAddons extends ChromeWebStore {
  constructor() {
    super()
    this.baseUrl = 'https://addons.mozilla.org'
  }

  async getInstallUrl(extensionId) {
    const urls = {
      'grammarly': 'https://addons.mozilla.org/firefox/addon/grammarly-1/',
      'ublock-origin': 'https://addons.mozilla.org/firefox/addon/ublock-origin/'
    }

    return urls[extensionId] || null
  }
}

class MicrosoftEdgeAddons extends ChromeWebStore {
  constructor() {
    super()
    this.baseUrl = 'https://microsoftedge.microsoft.com/addons'
  }

  async getInstallUrl(extensionId) {
    const urls = {
      'grammarly': 'https://microsoftedge.microsoft.com/addons/detail/grammarly/kbfnbcaeplbcioakkpcpgfkobkghlhen',
      'ublock-origin': 'https://microsoftedge.microsoft.com/addons/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm'
    }

    return urls[extensionId] || null
  }
}

class OperaAddons extends ChromeWebStore {
  constructor() {
    super()
    this.baseUrl = 'https://addons.opera.com'
  }
}

class SafariExtensions extends ChromeWebStore {
  constructor() {
    super()
    this.baseUrl = 'https://apps.apple.com'
  }

  async getInstallUrl(extensionId) {
    // Safari extensions are installed through the App Store
    return `https://apps.apple.com/app/safari-extension-${extensionId}`
  }
}

// Create singleton instance
const extensionMarketplace = new ExtensionMarketplace()

export default extensionMarketplace
export { ExtensionMarketplace }