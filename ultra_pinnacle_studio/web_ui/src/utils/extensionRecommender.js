// Extension Recommendation Engine
// Analyzes user workflow and suggests optimal extensions

class ExtensionRecommender {
  constructor(extensionBridge) {
    this.extensionBridge = extensionBridge
    this.userProfile = this.loadUserProfile()
    this.usagePatterns = this.loadUsagePatterns()
    this.recommendations = new Map()
  }

  loadUserProfile() {
    try {
      return JSON.parse(localStorage.getItem('extension_user_profile') || '{}')
    } catch (error) {
      console.error('Failed to load user profile:', error)
      return {}
    }
  }

  saveUserProfile() {
    try {
      localStorage.setItem('extension_user_profile', JSON.stringify(this.userProfile))
    } catch (error) {
      console.error('Failed to save user profile:', error)
    }
  }

  loadUsagePatterns() {
    try {
      return JSON.parse(localStorage.getItem('extension_usage_patterns') || '{}')
    } catch (error) {
      console.error('Failed to load usage patterns:', error)
      return {}
    }
  }

  saveUsagePatterns() {
    try {
      localStorage.setItem('extension_usage_patterns', JSON.stringify(this.usagePatterns))
    } catch (error) {
      console.error('Failed to save usage patterns:', error)
    }
  }

  // Analyze user behavior and update profile
  analyzeUserActivity(activity) {
    const { type, data, timestamp } = activity

    // Update usage patterns
    if (!this.usagePatterns[type]) {
      this.usagePatterns[type] = { count: 0, lastUsed: null, frequency: 0 }
    }

    this.usagePatterns[type].count++
    this.usagePatterns[type].lastUsed = timestamp

    // Calculate frequency (uses per day)
    const daysSinceFirstUse = this.calculateDaysSinceFirstUse(type)
    if (daysSinceFirstUse > 0) {
      this.usagePatterns[type].frequency = this.usagePatterns[type].count / daysSinceFirstUse
    }

    // Update user profile based on activity
    this.updateUserProfile(type, data)

    this.saveUsagePatterns()
    this.saveUserProfile()

    // Generate new recommendations based on updated profile
    this.generateRecommendations()
  }

  calculateDaysSinceFirstUse(activityType) {
    const pattern = this.usagePatterns[activityType]
    if (!pattern || !pattern.lastUsed) return 0

    const firstUse = new Date(pattern.lastUsed)
    const now = new Date()
    const diffTime = Math.abs(now - firstUse)
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  }

  updateUserProfile(activityType, data) {
    switch (activityType) {
      case 'document_editing':
        this.userProfile.contentCreator = (this.userProfile.contentCreator || 0) + 1
        if (data.format === 'google_docs') {
          this.userProfile.googleWorkspaceUser = true
        }
        break

      case 'spreadsheet_work':
        this.userProfile.dataAnalyst = (this.userProfile.dataAnalyst || 0) + 1
        this.userProfile.googleWorkspaceUser = true
        break

      case 'file_management':
        this.userProfile.fileOrganizer = (this.userProfile.fileOrganizer || 0) + 1
        break

      case 'writing':
        this.userProfile.writer = (this.userProfile.writer || 0) + 1
        if (data.length > 1000) {
          this.userProfile.longFormWriter = true
        }
        break

      case 'task_management':
        this.userProfile.taskManager = (this.userProfile.taskManager || 0) + 1
        break

      case 'code_editing':
        this.userProfile.developer = (this.userProfile.developer || 0) + 1
        if (data.language === 'javascript' || data.language === 'jsx') {
          this.userProfile.reactDeveloper = true
        }
        break

      case 'web_browsing':
        this.userProfile.webUser = (this.userProfile.webUser || 0) + 1
        if (data.adsBlocked > 10) {
          this.userProfile.privacyConscious = true
        }
        break

      case 'accessibility_check':
        this.userProfile.accessibilityAdvocate = (this.userProfile.accessibilityAdvocate || 0) + 1
        break
    }
  }

  generateRecommendations() {
    this.recommendations.clear()

    const extensions = this.extensionBridge.getAllExtensions()
    const enabledExtensions = extensions.filter(ext => ext.enabled)
    const disabledExtensions = extensions.filter(ext => !ext.enabled)

    // Generate recommendations based on user profile
    for (const extension of disabledExtensions) {
      const score = this.calculateRecommendationScore(extension)
      if (score > 0.5) { // Only recommend if score is above threshold
        this.recommendations.set(extension.id, {
          extension,
          score,
          reasons: this.getRecommendationReasons(extension),
          priority: this.getRecommendationPriority(score)
        })
      }
    }

    return Array.from(this.recommendations.values())
      .sort((a, b) => b.score - a.score)
  }

  calculateRecommendationScore(extension) {
    let score = 0
    const profile = this.userProfile

    switch (extension.id) {
      case 'google-docs':
        if (profile.contentCreator > 5) score += 0.8
        if (profile.googleWorkspaceUser) score += 0.6
        break

      case 'google-sheets':
        if (profile.dataAnalyst > 3) score += 0.8
        if (profile.googleWorkspaceUser) score += 0.6
        break

      case 'google-drive':
        if (profile.fileOrganizer > 5) score += 0.7
        if (profile.googleWorkspaceUser) score += 0.5
        break

      case 'google-calendar':
        if (profile.taskManager > 3) score += 0.6
        break

      case 'grammarly':
        if (profile.writer > 3) score += 0.8
        if (profile.longFormWriter) score += 0.4
        break

      case 'evernote':
        if (profile.contentCreator > 3) score += 0.6
        if (profile.webUser > 10) score += 0.4
        break

      case 'todoist':
        if (profile.taskManager > 2) score += 0.7
        break

      case 'react-devtools':
        if (profile.reactDeveloper) score += 0.9
        if (profile.developer > 5) score += 0.5
        break

      case 'lighthouse':
        if (profile.developer > 3) score += 0.7
        break

      case 'axe-devtools':
        if (profile.accessibilityAdvocate > 2) score += 0.8
        if (profile.developer > 2) score += 0.4
        break

      case 'ublock-origin':
        if (profile.privacyConscious) score += 0.8
        if (profile.webUser > 5) score += 0.5
        break
    }

    // Factor in usage patterns
    const usage = this.usagePatterns[extension.type]
    if (usage && usage.frequency > 1) { // More than once per day
      score += 0.2
    }

    return Math.min(score, 1.0) // Cap at 1.0
  }

  getRecommendationReasons(extension) {
    const reasons = []
    const profile = this.userProfile

    switch (extension.id) {
      case 'google-docs':
        if (profile.contentCreator > 5) {
          reasons.push('You frequently create and edit documents')
        }
        if (profile.googleWorkspaceUser) {
          reasons.push('You already use Google Workspace services')
        }
        break

      case 'grammarly':
        if (profile.writer > 3) {
          reasons.push('You write content regularly and could benefit from grammar assistance')
        }
        break

      case 'react-devtools':
        if (profile.reactDeveloper) {
          reasons.push('You work with React applications')
        }
        break

      case 'axe-devtools':
        if (profile.accessibilityAdvocate > 2) {
          reasons.push('You prioritize web accessibility')
        }
        break

      case 'ublock-origin':
        if (profile.privacyConscious) {
          reasons.push('You value online privacy and ad-free browsing')
        }
        break
    }

    return reasons
  }

  getRecommendationPriority(score) {
    if (score >= 0.8) return 'high'
    if (score >= 0.6) return 'medium'
    return 'low'
  }

  getRecommendations(limit = 5) {
    return Array.from(this.recommendations.values())
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
  }

  getRecommendationsByCategory() {
    const categorized = {
      productivity: [],
      writing: [],
      developer: [],
      accessibility: [],
      privacy: []
    }

    for (const [id, rec] of this.recommendations) {
      if (categorized[rec.extension.type]) {
        categorized[rec.extension.type].push(rec)
      }
    }

    // Sort each category by score
    Object.keys(categorized).forEach(category => {
      categorized[category].sort((a, b) => b.score - a.score)
    })

    return categorized
  }

  // Detect potential extension conflicts
  detectConflicts() {
    const enabledExtensions = this.extensionBridge.getAllExtensions()
      .filter(ext => ext.enabled)

    const conflicts = []

    // Check for known conflicts
    const conflictRules = [
      {
        extensions: ['ublock-origin', 'grammarly'],
        type: 'potential',
        description: 'uBlock Origin may interfere with Grammarly\'s content analysis',
        severity: 'low'
      },
      {
        extensions: ['react-devtools', 'axe-devtools'],
        type: 'none',
        description: 'These extensions work well together for React development',
        severity: 'none'
      }
    ]

    for (const rule of conflictRules) {
      const hasAllExtensions = rule.extensions.every(extId =>
        enabledExtensions.some(ext => ext.id === extId)
      )

      if (hasAllExtensions) {
        conflicts.push({
          type: rule.type,
          extensions: rule.extensions,
          description: rule.description,
          severity: rule.severity,
          recommendation: this.getConflictRecommendation(rule)
        })
      }
    }

    return conflicts
  }

  getConflictRecommendation(conflict) {
    switch (conflict.severity) {
      case 'high':
        return 'Consider disabling one of the conflicting extensions'
      case 'medium':
        return 'Monitor for issues and adjust settings if needed'
      case 'low':
        return 'Minor conflict detected, usually not problematic'
      default:
        return 'No action needed'
    }
  }

  // Generate usage analytics
  generateAnalytics() {
    const extensions = this.extensionBridge.getAllExtensions()
    const enabledCount = extensions.filter(ext => ext.enabled).length
    const totalUsage = Object.values(this.usagePatterns).reduce((sum, pattern) => sum + pattern.count, 0)

    return {
      totalExtensions: extensions.length,
      enabledExtensions: enabledCount,
      disabledExtensions: extensions.length - enabledCount,
      totalUsage,
      mostUsedCategory: this.getMostUsedCategory(),
      userProfile: this.userProfile,
      recommendationsCount: this.recommendations.size,
      conflictsDetected: this.detectConflicts().length
    }
  }

  getMostUsedCategory() {
    const categoryUsage = {}

    Object.entries(this.usagePatterns).forEach(([type, pattern]) => {
      categoryUsage[type] = (categoryUsage[type] || 0) + pattern.count
    })

    return Object.entries(categoryUsage)
      .sort(([,a], [,b]) => b - a)[0]?.[0] || 'none'
  }

  // Export user data for backup/sync
  exportUserData() {
    return {
      profile: this.userProfile,
      patterns: this.usagePatterns,
      recommendations: Array.from(this.recommendations.entries()),
      timestamp: new Date().toISOString()
    }
  }

  // Import user data
  importUserData(data) {
    try {
      this.userProfile = { ...this.userProfile, ...data.profile }
      this.usagePatterns = { ...this.usagePatterns, ...data.patterns }
      this.recommendations = new Map(data.recommendations || [])

      this.saveUserProfile()
      this.saveUsagePatterns()

      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

export default ExtensionRecommender