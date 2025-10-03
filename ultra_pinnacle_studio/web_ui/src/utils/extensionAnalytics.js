// Extension Usage Analytics and Recommendations System

class ExtensionAnalytics {
  constructor(extensionBridge, recommender) {
    this.extensionBridge = extensionBridge
    this.recommender = recommender
    this.analyticsData = this.loadAnalyticsData()
    this.sessionStartTime = Date.now()
    this.eventQueue = []
    this.reportingEnabled = true
    this.privacyLevel = 'standard' // 'minimal', 'standard', 'detailed'
  }

  // Initialize analytics system
  async initialize() {
    this.startSessionTracking()
    this.setupEventListeners()
    this.schedulePeriodicReporting()

    console.log('Extension analytics initialized')
  }

  // Load existing analytics data
  loadAnalyticsData() {
    try {
      const data = JSON.parse(localStorage.getItem('extension_analytics') || '{}')
      return {
        sessions: data.sessions || [],
        events: data.events || [],
        metrics: data.metrics || {},
        userProfile: data.userProfile || {},
        reports: data.reports || [],
        ...data
      }
    } catch (error) {
      console.error('Failed to load analytics data:', error)
      return this.getDefaultAnalyticsData()
    }
  }

  getDefaultAnalyticsData() {
    return {
      sessions: [],
      events: [],
      metrics: {
        totalSessions: 0,
        totalEvents: 0,
        avgSessionDuration: 0,
        mostUsedExtension: null,
        extensionUsageByCategory: {},
        peakUsageHours: {},
        userEngagementScore: 0
      },
      userProfile: {},
      reports: []
    }
  }

  // Save analytics data
  saveAnalyticsData() {
    try {
      localStorage.setItem('extension_analytics', JSON.stringify(this.analyticsData))
    } catch (error) {
      console.error('Failed to save analytics data:', error)
    }
  }

  // Start session tracking
  startSessionTracking() {
    const session = {
      id: 'session_' + Date.now(),
      startTime: new Date().toISOString(),
      duration: 0,
      events: 0,
      extensionsUsed: new Set(),
      userAgent: navigator.userAgent,
      referrer: document.referrer,
      pageViews: 1
    }

    this.analyticsData.sessions.push(session)
    this.currentSession = session
    this.analyticsData.metrics.totalSessions++

    // Track session end
    window.addEventListener('beforeunload', () => {
      this.endSession()
    })

    // Track visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pauseSession()
      } else {
        this.resumeSession()
      }
    })
  }

  // End current session
  endSession() {
    if (this.currentSession) {
      this.currentSession.endTime = new Date().toISOString()
      this.currentSession.duration = Date.now() - this.sessionStartTime
      this.saveAnalyticsData()
    }
  }

  // Pause session (when tab becomes hidden)
  pauseSession() {
    if (this.currentSession) {
      this.currentSession.lastPauseTime = Date.now()
    }
  }

  // Resume session (when tab becomes visible)
  resumeSession() {
    if (this.currentSession && this.currentSession.lastPauseTime) {
      const pauseDuration = Date.now() - this.currentSession.lastPauseTime
      this.currentSession.duration -= pauseDuration
      delete this.currentSession.lastPauseTime
    }
  }

  // Set up event listeners for user interactions
  setupEventListeners() {
    // Extension usage events
    document.addEventListener('extensionEnabled', (e) => {
      this.trackEvent('extension_enabled', { extensionId: e.detail.extensionId })
    })

    document.addEventListener('extensionDisabled', (e) => {
      this.trackEvent('extension_disabled', { extensionId: e.detail.extensionId })
    })

    document.addEventListener('extensionUpdated', (e) => {
      this.trackEvent('extension_updated', { extensionId: e.detail.extensionId })
    })

    // User interaction events
    document.addEventListener('click', (e) => {
      const target = e.target.closest('[data-extension-id]')
      if (target) {
        this.trackEvent('extension_ui_interaction', {
          extensionId: target.dataset.extensionId,
          action: 'click',
          element: target.tagName.toLowerCase()
        })
      }
    })

    // Page navigation events
    window.addEventListener('popstate', () => {
      this.trackEvent('page_navigation', {
        from: window.location.pathname,
        to: window.location.pathname
      })
    })

    // Error tracking
    window.addEventListener('error', (e) => {
      this.trackEvent('javascript_error', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno
      })
    })

    // Performance tracking
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'measure') {
            this.trackEvent('performance_metric', {
              name: entry.name,
              duration: entry.duration,
              startTime: entry.startTime
            })
          }
        }
      })
      observer.observe({ entryTypes: ['measure'] })
    }
  }

  // Track user event
  trackEvent(eventType, data = {}) {
    if (!this.reportingEnabled) return

    const event = {
      id: 'event_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
      type: eventType,
      timestamp: new Date().toISOString(),
      sessionId: this.currentSession?.id,
      data: this.filterEventData(data),
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    this.analyticsData.events.push(event)
    this.analyticsData.metrics.totalEvents++

    // Update session data
    if (this.currentSession) {
      this.currentSession.events++
      if (data.extensionId) {
        this.currentSession.extensionsUsed.add(data.extensionId)
      }
    }

    // Process event for real-time analytics
    this.processEvent(event)

    // Queue for batch processing
    this.eventQueue.push(event)

    // Auto-save periodically
    if (this.analyticsData.events.length % 10 === 0) {
      this.saveAnalyticsData()
    }
  }

  // Filter event data based on privacy level
  filterEventData(data) {
    if (this.privacyLevel === 'minimal') {
      // Remove sensitive data
      const filtered = { ...data }
      delete filtered.userId
      delete filtered.email
      delete filtered.location
      return filtered
    }

    if (this.privacyLevel === 'standard') {
      // Keep essential data only
      const allowedKeys = ['extensionId', 'action', 'category', 'duration', 'count']
      const filtered = {}
      for (const key of allowedKeys) {
        if (data[key] !== undefined) {
          filtered[key] = data[key]
        }
      }
      return filtered
    }

    // Detailed level - keep all data
    return data
  }

  // Process event for real-time analytics
  processEvent(event) {
    // Update user profile based on event
    this.updateUserProfile(event)

    // Update metrics
    this.updateMetrics(event)

    // Check for patterns that trigger recommendations
    this.checkForRecommendationTriggers(event)
  }

  // Update user profile based on events
  updateUserProfile(event) {
    const profile = this.analyticsData.userProfile

    switch (event.type) {
      case 'extension_enabled':
        profile.extensionsEnabled = (profile.extensionsEnabled || 0) + 1
        break

      case 'extension_disabled':
        profile.extensionsDisabled = (profile.extensionsDisabled || 0) + 1
        break

      case 'javascript_error':
        profile.errorCount = (profile.errorCount || 0) + 1
        break

      case 'page_navigation':
        profile.pageViews = (profile.pageViews || 0) + 1
        break
    }

    // Update time-based metrics
    const hour = new Date(event.timestamp).getHours()
    profile.usageByHour = profile.usageByHour || {}
    profile.usageByHour[hour] = (profile.usageByHour[hour] || 0) + 1
  }

  // Update analytics metrics
  updateMetrics(event) {
    const metrics = this.analyticsData.metrics

    // Update extension usage
    if (event.data.extensionId) {
      metrics.extensionUsage = metrics.extensionUsage || {}
      metrics.extensionUsage[event.data.extensionId] =
        (metrics.extensionUsage[event.data.extensionId] || 0) + 1
    }

    // Update category usage
    if (event.data.category) {
      metrics.extensionUsageByCategory = metrics.extensionUsageByCategory || {}
      metrics.extensionUsageByCategory[event.data.category] =
        (metrics.extensionUsageByCategory[event.data.category] || 0) + 1
    }

    // Calculate most used extension
    if (metrics.extensionUsage) {
      const mostUsed = Object.entries(metrics.extensionUsage)
        .sort(([,a], [,b]) => b - a)[0]
      metrics.mostUsedExtension = mostUsed ? mostUsed[0] : null
    }

    // Calculate user engagement score
    metrics.userEngagementScore = this.calculateEngagementScore()
  }

  // Calculate user engagement score
  calculateEngagementScore() {
    const metrics = this.analyticsData.metrics
    const profile = this.analyticsData.userProfile

    let score = 0

    // Session frequency and duration
    if (metrics.totalSessions > 10) score += 20
    if (metrics.avgSessionDuration > 300000) score += 15 // 5 minutes

    // Extension usage
    if (Object.keys(metrics.extensionUsage || {}).length > 5) score += 25

    // Feature adoption
    if ((profile.extensionsEnabled || 0) > 3) score += 20

    // Error rate (inverse)
    const errorRate = (profile.errorCount || 0) / Math.max(metrics.totalEvents, 1)
    if (errorRate < 0.01) score += 20

    return Math.min(100, score)
  }

  // Check for patterns that should trigger recommendations
  checkForRecommendationTriggers(event) {
    // Trigger recommendations based on usage patterns
    if (event.type === 'javascript_error' && event.data.message?.includes('extension')) {
      // Recommend troubleshooting extensions
      this.recommender.generateRecommendations()
    }

    if (event.type === 'extension_disabled' &&
        this.analyticsData.metrics.extensionUsage?.[event.data.extensionId] > 50) {
      // User frequently uses but disabled an extension - might need attention
      console.log('Frequently used extension disabled:', event.data.extensionId)
    }
  }

  // Schedule periodic reporting
  schedulePeriodicReporting() {
    // Generate daily reports
    setInterval(() => {
      this.generateDailyReport()
    }, 24 * 60 * 60 * 1000) // Daily

    // Generate weekly reports
    setInterval(() => {
      this.generateWeeklyReport()
    }, 7 * 24 * 60 * 60 * 1000) // Weekly
  }

  // Generate daily analytics report
  generateDailyReport() {
    const today = new Date().toISOString().split('T')[0]
    const todaysEvents = this.analyticsData.events.filter(event =>
      event.timestamp.startsWith(today)
    )

    const report = {
      date: today,
      type: 'daily',
      metrics: {
        sessions: this.analyticsData.sessions.filter(s =>
          s.startTime.startsWith(today)
        ).length,
        events: todaysEvents.length,
        extensionsUsed: new Set(todaysEvents
          .filter(e => e.data.extensionId)
          .map(e => e.data.extensionId)
        ).size,
        errors: todaysEvents.filter(e => e.type === 'javascript_error').length,
        avgSessionDuration: this.calculateAverageSessionDuration(today)
      },
      topExtensions: this.getTopExtensions(5, today),
      recommendations: this.recommender.generateRecommendations()
    }

    this.analyticsData.reports.push(report)
    this.saveAnalyticsData()

    return report
  }

  // Generate weekly analytics report
  generateWeeklyReport() {
    const weekAgo = new Date()
    weekAgo.setDate(weekAgo.getDate() - 7)
    const weekStart = weekAgo.toISOString().split('T')[0]

    const weeklyEvents = this.analyticsData.events.filter(event =>
      event.timestamp >= weekStart
    )

    const report = {
      date: new Date().toISOString().split('T')[0],
      type: 'weekly',
      period: 'last_7_days',
      metrics: {
        totalEvents: weeklyEvents.length,
        uniqueExtensions: new Set(weeklyEvents
          .filter(e => e.data.extensionId)
          .map(e => e.data.extensionId)
        ).size,
        avgDailyEvents: weeklyEvents.length / 7,
        userEngagementScore: this.analyticsData.metrics.userEngagementScore,
        errorRate: weeklyEvents.filter(e => e.type === 'javascript_error').length / weeklyEvents.length
      },
      trends: this.calculateTrends(weeklyEvents),
      insights: this.generateInsights(weeklyEvents)
    }

    this.analyticsData.reports.push(report)
    this.saveAnalyticsData()

    return report
  }

  // Calculate average session duration for a date
  calculateAverageSessionDuration(date) {
    const sessions = this.analyticsData.sessions.filter(s =>
      s.startTime.startsWith(date) && s.duration
    )

    if (sessions.length === 0) return 0

    const totalDuration = sessions.reduce((sum, s) => sum + s.duration, 0)
    return totalDuration / sessions.length
  }

  // Get top used extensions
  getTopExtensions(limit = 5, dateFilter = null) {
    let events = this.analyticsData.events

    if (dateFilter) {
      events = events.filter(e => e.timestamp.startsWith(dateFilter))
    }

    const usage = {}
    events.forEach(event => {
      if (event.data.extensionId) {
        usage[event.data.extensionId] = (usage[event.data.extensionId] || 0) + 1
      }
    })

    return Object.entries(usage)
      .sort(([,a], [,b]) => b - a)
      .slice(0, limit)
      .map(([id, count]) => ({ extensionId: id, usageCount: count }))
  }

  // Calculate usage trends
  calculateTrends(events) {
    const days = {}
    events.forEach(event => {
      const day = event.timestamp.split('T')[0]
      days[day] = (days[day] || 0) + 1
    })

    const sortedDays = Object.keys(days).sort()
    const trend = sortedDays.length >= 2 ?
      (days[sortedDays[sortedDays.length - 1]] - days[sortedDays[0]]) / sortedDays.length : 0

    return {
      direction: trend > 0 ? 'increasing' : trend < 0 ? 'decreasing' : 'stable',
      changePercent: sortedDays.length >= 2 ?
        ((days[sortedDays[sortedDays.length - 1]] - days[sortedDays[0]]) / days[sortedDays[0]]) * 100 : 0,
      dataPoints: sortedDays.length
    }
  }

  // Generate insights from analytics data
  generateInsights(events) {
    const insights = []

    // Check for high error rates
    const errorRate = events.filter(e => e.type === 'javascript_error').length / events.length
    if (errorRate > 0.05) {
      insights.push({
        type: 'warning',
        title: 'High Error Rate Detected',
        description: `${(errorRate * 100).toFixed(1)}% of events are errors. Consider reviewing extension configurations.`,
        priority: 'high'
      })
    }

    // Check for low engagement
    if (this.analyticsData.metrics.userEngagementScore < 30) {
      insights.push({
        type: 'suggestion',
        title: 'Low User Engagement',
        description: 'Consider exploring more extensions or reviewing current setup.',
        priority: 'medium'
      })
    }

    // Check for extension over-reliance
    const topExtensionUsage = Math.max(...Object.values(this.analyticsData.metrics.extensionUsage || { 0: 0 }))
    const totalUsage = Object.values(this.analyticsData.metrics.extensionUsage || {}).reduce((a, b) => a + b, 0)

    if (topExtensionUsage / totalUsage > 0.7) {
      insights.push({
        type: 'info',
        title: 'Extension Usage Concentration',
        description: 'One extension is being used significantly more than others. Consider diversifying your workflow.',
        priority: 'low'
      })
    }

    return insights
  }

  // Get analytics summary
  getAnalyticsSummary() {
    return {
      metrics: this.analyticsData.metrics,
      userProfile: this.analyticsData.userProfile,
      recentActivity: this.analyticsData.events.slice(-10),
      recommendations: this.recommender.generateRecommendations(),
      insights: this.generateInsights(this.analyticsData.events.slice(-100))
    }
  }

  // Export analytics data
  exportAnalyticsData() {
    return {
      ...this.analyticsData,
      exportDate: new Date().toISOString(),
      privacyLevel: this.privacyLevel,
      version: '1.0'
    }
  }

  // Configure analytics settings
  configureAnalytics(settings) {
    this.reportingEnabled = settings.enabled !== false
    this.privacyLevel = settings.privacyLevel || 'standard'

    // Save settings
    try {
      localStorage.setItem('analytics_settings', JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save analytics settings:', error)
    }
  }

  // Clear old analytics data
  clearOldData(daysToKeep = 90) {
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep)

    // Filter events
    this.analyticsData.events = this.analyticsData.events.filter(event =>
      new Date(event.timestamp) > cutoffDate
    )

    // Filter sessions
    this.analyticsData.sessions = this.analyticsData.sessions.filter(session =>
      new Date(session.startTime) > cutoffDate
    )

    // Filter reports
    this.analyticsData.reports = this.analyticsData.reports.filter(report =>
      new Date(report.date) > cutoffDate
    )

    this.saveAnalyticsData()
  }

  // Reset analytics data
  resetAnalytics() {
    this.analyticsData = this.getDefaultAnalyticsData()
    this.saveAnalyticsData()
  }
}

// Create singleton instance
const extensionAnalytics = new ExtensionAnalytics()

export default extensionAnalytics
export { ExtensionAnalytics }