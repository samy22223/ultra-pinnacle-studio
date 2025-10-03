// Extension Conflict Detection and Resolution System

class ExtensionConflictDetector {
  constructor(extensionBridge) {
    this.extensionBridge = extensionBridge
    this.conflicts = new Map()
    this.resolutions = new Map()
    this.conflictHistory = []
  }

  // Comprehensive conflict detection
  detectConflicts() {
    const extensions = this.extensionBridge.getAllExtensions()
    const enabledExtensions = extensions.filter(ext => ext.enabled)

    this.conflicts.clear()

    // Check for various types of conflicts
    this.checkResourceConflicts(enabledExtensions)
    this.checkAPIconflicts(enabledExtensions)
    this.checkPerformanceConflicts(enabledExtensions)
    this.checkSecurityConflicts(enabledExtensions)
    this.checkBrowserCompatibilityConflicts(enabledExtensions)

    return Array.from(this.conflicts.values())
  }

  checkResourceConflicts(extensions) {
    // Check for extensions that heavily use the same resources
    const resourceIntensive = ['react-devtools', 'lighthouse', 'axe-devtools', 'ublock-origin']

    const activeResourceIntensive = extensions.filter(ext =>
      resourceIntensive.includes(ext.id)
    )

    if (activeResourceIntensive.length > 2) {
      this.addConflict({
        id: 'resource_overload',
        type: 'performance',
        severity: 'medium',
        title: 'Resource Usage Conflict',
        description: `${activeResourceIntensive.length} resource-intensive extensions are active simultaneously`,
        affectedExtensions: activeResourceIntensive.map(ext => ext.id),
        impact: 'May slow down page performance and increase memory usage',
        solutions: [
          'Disable less frequently used extensions',
          'Use extensions one at a time for intensive tasks',
          'Consider browser performance settings'
        ]
      })
    }
  }

  checkAPIconflicts(extensions) {
    // Check for API conflicts
    const apiUsers = {
      google: ['google-docs', 'google-sheets', 'google-drive', 'google-calendar'],
      contentScript: ['grammarly', 'evernote', 'ublock-origin', 'axe-devtools']
    }

    Object.entries(apiUsers).forEach(([api, extIds]) => {
      const activeUsers = extensions.filter(ext => extIds.includes(ext.id))

      if (activeUsers.length > 3) {
        this.addConflict({
          id: `api_overload_${api}`,
          type: 'api',
          severity: 'low',
          title: 'API Usage Concentration',
          description: `Multiple extensions using ${api} API simultaneously`,
          affectedExtensions: activeUsers.map(ext => ext.id),
          impact: 'May hit API rate limits or cause synchronization issues',
          solutions: [
            'Space out API-intensive operations',
            'Check extension settings for API usage optimization',
            'Monitor API usage in browser developer tools'
          ]
        })
      }
    })
  }

  checkPerformanceConflicts(extensions) {
    // Check for performance-impacting combinations
    const performanceConflicts = [
      {
        trigger: ['ublock-origin', 'grammarly'],
        description: 'Ad blocker may interfere with writing assistant content analysis',
        severity: 'low',
        solutions: [
          'Add Grammarly domains to uBlock Origin whitelist',
          'Use Grammarly in focused mode when needed',
          'Consider alternative ad blocking strategies'
        ]
      },
      {
        trigger: ['react-devtools', 'axe-devtools'],
        description: 'Debugging tools may interfere with accessibility testing',
        severity: 'low',
        solutions: [
          'Run accessibility tests in production builds',
          'Use React DevTools in development only',
          'Consider accessibility testing in incognito mode'
        ]
      }
    ]

    performanceConflicts.forEach(conflict => {
      const hasAllTriggers = conflict.trigger.every(extId =>
        extensions.some(ext => ext.id === extId)
      )

      if (hasAllTriggers) {
        this.addConflict({
          id: `performance_${conflict.trigger.join('_')}`,
          type: 'performance',
          severity: conflict.severity,
          title: 'Performance Interaction Detected',
          description: conflict.description,
          affectedExtensions: conflict.trigger,
          impact: 'Potential interference between extension functionalities',
          solutions: conflict.solutions
        })
      }
    })
  }

  checkSecurityConflicts(extensions) {
    // Check for security-related conflicts
    const securityExtensions = extensions.filter(ext =>
      ['ublock-origin', 'axe-devtools'].includes(ext.id)
    )

    if (securityExtensions.length >= 2) {
      // This is actually beneficial, not a conflict
      this.addConflict({
        id: 'security_synergy',
        type: 'security',
        severity: 'none',
        title: 'Security Enhancement',
        description: 'Multiple security-focused extensions provide layered protection',
        affectedExtensions: securityExtensions.map(ext => ext.id),
        impact: 'Enhanced security and privacy protection',
        solutions: [
          'This combination is beneficial for security',
          'Consider configuring extensions to complement each other',
          'Regular security audits recommended'
        ]
      })
    }
  }

  checkBrowserCompatibilityConflicts(extensions) {
    // Check for browser-specific conflicts
    const browser = this.detectBrowser()

    extensions.forEach(ext => {
      if (ext.supportedBrowsers && !ext.supportedBrowsers.includes(browser)) {
        this.addConflict({
          id: `browser_${ext.id}`,
          type: 'compatibility',
          severity: 'high',
          title: 'Browser Compatibility Issue',
          description: `${ext.name} may not work optimally in ${browser}`,
          affectedExtensions: [ext.id],
          impact: 'Extension functionality may be limited or unavailable',
          solutions: [
            `Switch to a supported browser: ${ext.supportedBrowsers.join(', ')}`,
            'Check for browser-specific versions of the extension',
            'Contact extension developer for browser support updates'
          ]
        })
      }
    })
  }

  detectBrowser() {
    const ua = navigator.userAgent
    if (ua.includes('Firefox/')) return 'firefox'
    if (ua.includes('Chrome/') && !ua.includes('Edg/')) return 'chrome'
    if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'safari'
    if (ua.includes('Edg/')) return 'edge'
    return 'unknown'
  }

  addConflict(conflict) {
    this.conflicts.set(conflict.id, {
      ...conflict,
      detectedAt: new Date().toISOString(),
      status: 'active'
    })

    // Log conflict history
    this.conflictHistory.push({
      ...conflict,
      timestamp: new Date().toISOString()
    })
  }

  resolveConflict(conflictId, resolution) {
    const conflict = this.conflicts.get(conflictId)
    if (conflict) {
      conflict.status = 'resolved'
      conflict.resolution = resolution
      conflict.resolvedAt = new Date().toISOString()

      this.resolutions.set(conflictId, resolution)
    }
  }

  getActiveConflicts() {
    return Array.from(this.conflicts.values())
      .filter(conflict => conflict.status === 'active')
  }

  getResolvedConflicts() {
    return Array.from(this.conflicts.values())
      .filter(conflict => conflict.status === 'resolved')
  }

  getConflictsBySeverity(severity) {
    return Array.from(this.conflicts.values())
      .filter(conflict => conflict.severity === severity)
  }

  getConflictsByType(type) {
    return Array.from(this.conflicts.values())
      .filter(conflict => conflict.type === type)
  }

  // Generate conflict resolution suggestions
  suggestResolutions(conflict) {
    const suggestions = []

    switch (conflict.type) {
      case 'performance':
        suggestions.push({
          action: 'disable_temporarily',
          description: 'Temporarily disable conflicting extensions',
          automatic: true
        })
        suggestions.push({
          action: 'adjust_settings',
          description: 'Modify extension settings to reduce conflicts',
          automatic: false
        })
        break

      case 'api':
        suggestions.push({
          action: 'stagger_usage',
          description: 'Use extensions at different times to avoid API limits',
          automatic: false
        })
        break

      case 'compatibility':
        suggestions.push({
          action: 'switch_browser',
          description: 'Use a compatible browser for this extension',
          automatic: false
        })
        break

      case 'security':
        if (conflict.severity === 'none') {
          suggestions.push({
            action: 'optimize_settings',
            description: 'Configure extensions for optimal security synergy',
            automatic: false
          })
        }
        break
    }

    return suggestions
  }

  // Auto-resolve certain conflicts
  autoResolveConflicts() {
    const activeConflicts = this.getActiveConflicts()
    const resolved = []

    activeConflicts.forEach(conflict => {
      if (this.canAutoResolve(conflict)) {
        const resolution = this.generateAutoResolution(conflict)
        this.resolveConflict(conflict.id, resolution)
        resolved.push(conflict.id)
      }
    })

    return resolved
  }

  canAutoResolve(conflict) {
    // Only auto-resolve low-severity performance conflicts
    return conflict.severity === 'low' && conflict.type === 'performance'
  }

  generateAutoResolution(conflict) {
    return {
      type: 'automatic',
      action: 'logged_warning',
      description: 'Conflict logged for monitoring, no action taken',
      timestamp: new Date().toISOString()
    }
  }

  // Export conflict data for analysis
  exportConflictData() {
    return {
      activeConflicts: this.getActiveConflicts(),
      resolvedConflicts: this.getResolvedConflicts(),
      conflictHistory: this.conflictHistory,
      resolutions: Array.from(this.resolutions.entries()),
      summary: {
        totalConflicts: this.conflicts.size,
        activeConflicts: this.getActiveConflicts().length,
        resolvedConflicts: this.getResolvedConflicts().length,
        bySeverity: {
          high: this.getConflictsBySeverity('high').length,
          medium: this.getConflictsBySeverity('medium').length,
          low: this.getConflictsBySeverity('low').length,
          none: this.getConflictsBySeverity('none').length
        },
        byType: {
          performance: this.getConflictsByType('performance').length,
          api: this.getConflictsByType('api').length,
          compatibility: this.getConflictsByType('compatibility').length,
          security: this.getConflictsByType('security').length
        }
      }
    }
  }

  // Get conflict statistics
  getConflictStats() {
    const data = this.exportConflictData()
    return {
      total: data.summary.totalConflicts,
      active: data.summary.activeConflicts,
      resolved: data.summary.resolvedConflicts,
      resolutionRate: data.summary.totalConflicts > 0
        ? (data.summary.resolvedConflicts / data.summary.totalConflicts) * 100
        : 0,
      mostCommonType: Object.entries(data.summary.byType)
        .sort(([,a], [,b]) => b - a)[0]?.[0] || 'none'
    }
  }
}

export default ExtensionConflictDetector