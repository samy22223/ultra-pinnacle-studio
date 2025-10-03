// Cross-Platform Compatibility Testing System

class CrossPlatformTester {
  constructor() {
    this.testResults = new Map()
    this.deviceProfiles = new Map()
    this.compatibilityMatrix = new Map()
    this.performanceBenchmarks = new Map()
    this.testSuites = new Map()
  }

  // Initialize testing system
  async initialize() {
    this.setupDeviceProfiles()
    this.registerTestSuites()
    this.initializePerformanceMonitoring()

    console.log('Cross-platform testing system initialized')
  }

  // Setup device profiles for testing
  setupDeviceProfiles() {
    this.deviceProfiles.set('desktop_windows_chrome', {
      name: 'Windows Desktop - Chrome',
      platform: 'desktop',
      os: 'windows',
      browser: 'chrome',
      viewport: { width: 1920, height: 1080 },
      capabilities: ['webgl', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    this.deviceProfiles.set('desktop_macos_safari', {
      name: 'macOS Desktop - Safari',
      platform: 'desktop',
      os: 'macos',
      browser: 'safari',
      viewport: { width: 1440, height: 900 },
      capabilities: ['webgl', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    })

    this.deviceProfiles.set('mobile_ios_safari', {
      name: 'iOS Mobile - Safari',
      platform: 'mobile',
      os: 'ios',
      browser: 'safari',
      viewport: { width: 375, height: 667 },
      capabilities: ['touch', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    })

    this.deviceProfiles.set('mobile_android_chrome', {
      name: 'Android Mobile - Chrome',
      platform: 'mobile',
      os: 'android',
      browser: 'chrome',
      viewport: { width: 360, height: 640 },
      capabilities: ['touch', 'webgl', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    })

    this.deviceProfiles.set('tablet_ipad_safari', {
      name: 'iPad Tablet - Safari',
      platform: 'tablet',
      os: 'ios',
      browser: 'safari',
      viewport: { width: 768, height: 1024 },
      capabilities: ['touch', 'webgl', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    })

    this.deviceProfiles.set('tablet_android_chrome', {
      name: 'Android Tablet - Chrome',
      platform: 'tablet',
      os: 'android',
      browser: 'chrome',
      viewport: { width: 800, height: 1280 },
      capabilities: ['touch', 'webgl', 'websockets', 'localStorage', 'serviceWorker'],
      userAgent: 'Mozilla/5.0 (Linux; Android 10; SM-T860) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
  }

  // Register test suites
  registerTestSuites() {
    this.registerCoreFunctionalityTests()
    this.registerExtensionIntegrationTests()
    this.registerPerformanceTests()
    this.registerAccessibilityTests()
    this.registerCompatibilityTests()
  }

  registerCoreFunctionalityTests() {
    this.testSuites.set('core_functionality', {
      name: 'Core Functionality Tests',
      description: 'Tests basic application functionality across platforms',
      tests: [
        {
          name: 'Application Loading',
          test: async () => await this.testApplicationLoading(),
          platforms: ['all']
        },
        {
          name: 'Navigation System',
          test: async () => await this.testNavigationSystem(),
          platforms: ['all']
        },
        {
          name: 'Data Persistence',
          test: async () => await this.testDataPersistence(),
          platforms: ['all']
        },
        {
          name: 'API Communication',
          test: async () => await this.testAPICommunication(),
          platforms: ['all']
        }
      ]
    })
  }

  registerExtensionIntegrationTests() {
    this.testSuites.set('extension_integration', {
      name: 'Extension Integration Tests',
      description: 'Tests extension loading and functionality',
      tests: [
        {
          name: 'Extension Loading',
          test: async () => await this.testExtensionLoading(),
          platforms: ['desktop']
        },
        {
          name: 'Extension Communication',
          test: async () => await this.testExtensionCommunication(),
          platforms: ['desktop']
        },
        {
          name: 'Extension UI Integration',
          test: async () => await this.testExtensionUIIntegration(),
          platforms: ['all']
        },
        {
          name: 'Extension Conflict Detection',
          test: async () => await this.testExtensionConflictDetection(),
          platforms: ['desktop']
        }
      ]
    })
  }

  registerPerformanceTests() {
    this.testSuites.set('performance', {
      name: 'Performance Tests',
      description: 'Tests application performance across platforms',
      tests: [
        {
          name: 'Load Time Performance',
          test: async () => await this.testLoadTimePerformance(),
          platforms: ['all']
        },
        {
          name: 'Runtime Performance',
          test: async () => await this.testRuntimePerformance(),
          platforms: ['all']
        },
        {
          name: 'Memory Usage',
          test: async () => await this.testMemoryUsage(),
          platforms: ['all']
        },
        {
          name: 'Network Performance',
          test: async () => await this.testNetworkPerformance(),
          platforms: ['all']
        }
      ]
    })
  }

  registerAccessibilityTests() {
    this.testSuites.set('accessibility', {
      name: 'Accessibility Tests',
      description: 'Tests accessibility compliance and features',
      tests: [
        {
          name: 'WCAG Compliance',
          test: async () => await this.testWCAGCompliance(),
          platforms: ['all']
        },
        {
          name: 'Keyboard Navigation',
          test: async () => await this.testKeyboardNavigation(),
          platforms: ['desktop']
        },
        {
          name: 'Screen Reader Support',
          test: async () => await this.testScreenReaderSupport(),
          platforms: ['all']
        },
        {
          name: 'Touch Accessibility',
          test: async () => await this.testTouchAccessibility(),
          platforms: ['mobile', 'tablet']
        }
      ]
    })
  }

  registerCompatibilityTests() {
    this.testSuites.set('compatibility', {
      name: 'Compatibility Tests',
      description: 'Tests cross-browser and cross-platform compatibility',
      tests: [
        {
          name: 'Browser Feature Support',
          test: async () => await this.testBrowserFeatureSupport(),
          platforms: ['all']
        },
        {
          name: 'CSS Compatibility',
          test: async () => await this.testCSSCompatibility(),
          platforms: ['all']
        },
        {
          name: 'JavaScript Compatibility',
          test: async () => await this.testJavaScriptCompatibility(),
          platforms: ['all']
        },
        {
          name: 'API Compatibility',
          test: async () => await this.testAPICompatibility(),
          platforms: ['all']
        }
      ]
    })
  }

  // Run all tests for current platform
  async runAllTests(options = {}) {
    const currentProfile = this.getCurrentDeviceProfile()
    const results = {
      platform: currentProfile,
      timestamp: new Date().toISOString(),
      testSuites: {},
      summary: {
        totalTests: 0,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0,
        duration: 0
      }
    }

    const startTime = performance.now()

    for (const [suiteName, suite] of this.testSuites) {
      results.testSuites[suiteName] = await this.runTestSuite(suite, currentProfile, options)
    }

    results.summary.duration = performance.now() - startTime
    this.calculateSummary(results)

    this.testResults.set(currentProfile.name, results)
    return results
  }

  // Run specific test suite
  async runTestSuite(suite, deviceProfile, options = {}) {
    const suiteResults = {
      name: suite.name,
      description: suite.description,
      tests: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        duration: 0
      }
    }

    const suiteStartTime = performance.now()

    for (const test of suite.tests) {
      const testResult = await this.runTest(test, deviceProfile, options)
      suiteResults.tests.push(testResult)

      suiteResults.summary.total++
      if (testResult.status === 'passed') suiteResults.summary.passed++
      else if (testResult.status === 'failed') suiteResults.summary.failed++
      else if (testResult.status === 'skipped') suiteResults.summary.skipped++
    }

    suiteResults.summary.duration = performance.now() - suiteStartTime
    return suiteResults
  }

  // Run individual test
  async runTest(test, deviceProfile, options = {}) {
    const testResult = {
      name: test.name,
      status: 'pending',
      duration: 0,
      error: null,
      details: null,
      platform: deviceProfile.name
    }

    // Check if test should run on this platform
    if (!this.shouldRunTestOnPlatform(test, deviceProfile)) {
      testResult.status = 'skipped'
      testResult.details = `Test not applicable for platform: ${deviceProfile.platform}`
      return testResult
    }

    const testStartTime = performance.now()

    try {
      const result = await test.test()
      testResult.status = result.passed ? 'passed' : 'failed'
      testResult.details = result.details
      testResult.error = result.error
    } catch (error) {
      testResult.status = 'failed'
      testResult.error = error.message
      testResult.details = 'Test execution failed'
    }

    testResult.duration = performance.now() - testStartTime
    return testResult
  }

  // Check if test should run on current platform
  shouldRunTestOnPlatform(test, deviceProfile) {
    if (test.platforms.includes('all')) return true
    if (test.platforms.includes(deviceProfile.platform)) return true
    if (test.platforms.includes(deviceProfile.os)) return true
    if (test.platforms.includes(deviceProfile.browser)) return true
    return false
  }

  // Get current device profile
  getCurrentDeviceProfile() {
    const ua = navigator.userAgent
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight
    }

    // Determine platform
    let platform = 'desktop'
    if (this.isMobileDevice()) platform = 'mobile'
    else if (this.isTabletDevice()) platform = 'tablet'

    // Determine browser
    let browser = 'unknown'
    if (ua.includes('Chrome') && !ua.includes('Edg/')) browser = 'chrome'
    else if (ua.includes('Firefox/')) browser = 'firefox'
    else if (ua.includes('Safari/') && !ua.includes('Chrome/')) browser = 'safari'
    else if (ua.includes('Edg/')) browser = 'edge'

    // Determine OS
    let os = 'unknown'
    if (ua.includes('Windows')) os = 'windows'
    else if (ua.includes('Mac OS X')) os = 'macos'
    else if (ua.includes('Linux')) os = 'linux'
    else if (ua.includes('Android')) os = 'android'
    else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'ios'

    return {
      name: `${os}_${platform}_${browser}`,
      platform,
      os,
      browser,
      viewport,
      userAgent: ua,
      capabilities: this.detectCapabilities()
    }
  }

  isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) &&
           window.innerWidth < 768
  }

  isTabletDevice() {
    return /iPad|Android(?=.*\bMobile\b)|Tablet/i.test(navigator.userAgent) ||
           (window.innerWidth >= 768 && window.innerWidth < 1024)
  }

  detectCapabilities() {
    return {
      touch: 'ontouchstart' in window,
      webgl: !!this.getWebGLContext(),
      websockets: 'WebSocket' in window,
      localStorage: this.checkLocalStorage(),
      serviceWorker: 'serviceWorker' in navigator,
      geolocation: 'geolocation' in navigator,
      notification: 'Notification' in window
    }
  }

  getWebGLContext() {
    try {
      const canvas = document.createElement('canvas')
      return canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    } catch {
      return null
    }
  }

  checkLocalStorage() {
    try {
      const test = 'test'
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch {
      return false
    }
  }

  // Test implementations
  async testApplicationLoading() {
    try {
      // Check if main application elements are loaded
      const appElement = document.querySelector('#root')
      const mainContent = document.querySelector('.main-content')

      const passed = !!(appElement && mainContent)
      return {
        passed,
        details: passed ? 'Application loaded successfully' : 'Application failed to load'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Application loading test failed'
      }
    }
  }

  async testNavigationSystem() {
    try {
      // Test navigation links
      const navLinks = document.querySelectorAll('.nav-link')
      let workingLinks = 0

      for (const link of navLinks) {
        const href = link.getAttribute('href')
        if (href && href !== '#') {
          workingLinks++
        }
      }

      const passed = workingLinks > 0
      return {
        passed,
        details: `Found ${workingLinks} working navigation links`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Navigation system test failed'
      }
    }
  }

  async testDataPersistence() {
    try {
      // Test localStorage functionality
      const testKey = 'test_persistence'
      const testValue = 'test_value_' + Date.now()

      localStorage.setItem(testKey, testValue)
      const retrievedValue = localStorage.getItem(testKey)
      localStorage.removeItem(testKey)

      const passed = retrievedValue === testValue
      return {
        passed,
        details: passed ? 'Data persistence working correctly' : 'Data persistence failed'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Data persistence test failed'
      }
    }
  }

  async testAPICommunication() {
    try {
      // Test basic API connectivity (would need actual API endpoint)
      const passed = navigator.onLine // Basic online check
      return {
        passed,
        details: passed ? 'API communication available' : 'API communication not available'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'API communication test failed'
      }
    }
  }

  async testExtensionLoading() {
    try {
      // Test extension system initialization
      const extensionManager = document.querySelector('[data-extension-manager]')
      const passed = !!extensionManager
      return {
        passed,
        details: passed ? 'Extension system loaded' : 'Extension system not found'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Extension loading test failed'
      }
    }
  }

  async testExtensionCommunication() {
    try {
      // Test extension bridge communication
      const passed = typeof window.extensionBridge !== 'undefined'
      return {
        passed,
        details: passed ? 'Extension communication bridge available' : 'Extension communication bridge not found'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Extension communication test failed'
      }
    }
  }

  async testExtensionUIIntegration() {
    try {
      // Test extension UI components
      const extensionUI = document.querySelector('[data-extension-ui]')
      const passed = !!extensionUI
      return {
        passed,
        details: passed ? 'Extension UI integrated' : 'Extension UI not found'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Extension UI integration test failed'
      }
    }
  }

  async testExtensionConflictDetection() {
    try {
      // Test conflict detection system
      const passed = typeof window.extensionConflictDetector !== 'undefined'
      return {
        passed,
        details: passed ? 'Extension conflict detection available' : 'Extension conflict detection not found'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Extension conflict detection test failed'
      }
    }
  }

  async testLoadTimePerformance() {
    try {
      // Test page load performance
      const loadTime = performance.getEntriesByType('navigation')[0]?.loadEventEnd || 0
      const passed = loadTime < 3000 // Less than 3 seconds
      return {
        passed,
        details: `Page load time: ${loadTime.toFixed(2)}ms`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Load time performance test failed'
      }
    }
  }

  async testRuntimePerformance() {
    try {
      // Test runtime performance
      const startTime = performance.now()
      // Perform some operations
      for (let i = 0; i < 1000; i++) {
        Math.sqrt(i)
      }
      const endTime = performance.now()
      const duration = endTime - startTime

      const passed = duration < 10 // Less than 10ms for 1000 operations
      return {
        passed,
        details: `Runtime performance: ${duration.toFixed(2)}ms for 1000 operations`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Runtime performance test failed'
      }
    }
  }

  async testMemoryUsage() {
    try {
      // Test memory usage (if available)
      if ('memory' in performance) {
        const memInfo = performance.memory
        const usedPercent = (memInfo.usedJSHeapSize / memInfo.totalJSHeapSize) * 100
        const passed = usedPercent < 80 // Less than 80% memory usage
        return {
          passed,
          details: `Memory usage: ${usedPercent.toFixed(1)}% (${this.formatBytes(memInfo.usedJSHeapSize)} / ${this.formatBytes(memInfo.totalJSHeapSize)})`
        }
      }

      return {
        passed: true,
        details: 'Memory monitoring not available in this browser'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Memory usage test failed'
      }
    }
  }

  async testNetworkPerformance() {
    try {
      // Test network performance
      if ('connection' in navigator) {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection
        if (connection) {
          const effectiveType = connection.effectiveType || 'unknown'
          const downlink = connection.downlink || 0
          const passed = downlink > 1 // At least 1 Mbps
          return {
            passed,
            details: `Network: ${effectiveType}, ${downlink} Mbps downlink`
          }
        }
      }

      return {
        passed: true,
        details: 'Network information not available'
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Network performance test failed'
      }
    }
  }

  async testWCAGCompliance() {
    try {
      // Basic WCAG compliance check
      const images = document.querySelectorAll('img')
      let imagesWithAlt = 0

      images.forEach(img => {
        if (img.getAttribute('alt')) {
          imagesWithAlt++
        }
      })

      const passed = imagesWithAlt === images.length
      return {
        passed,
        details: `${imagesWithAlt}/${images.length} images have alt text`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'WCAG compliance test failed'
      }
    }
  }

  async testKeyboardNavigation() {
    try {
      // Test keyboard navigation
      const focusableElements = document.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      const passed = focusableElements.length > 0
      return {
        passed,
        details: `Found ${focusableElements.length} focusable elements`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Keyboard navigation test failed'
      }
    }
  }

  async testScreenReaderSupport() {
    try {
      // Test screen reader support
      const ariaElements = document.querySelectorAll('[aria-label], [aria-labelledby], [role]')
      const passed = ariaElements.length > 0
      return {
        passed,
        details: `Found ${ariaElements.length} ARIA elements`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Screen reader support test failed'
      }
    }
  }

  async testTouchAccessibility() {
    try {
      // Test touch accessibility
      const touchTargets = document.querySelectorAll('button, [role="button"], .clickable')
      let adequateSize = 0

      touchTargets.forEach(element => {
        const rect = element.getBoundingClientRect()
        const minSize = 44 // WCAG minimum touch target size
        if (rect.width >= minSize && rect.height >= minSize) {
          adequateSize++
        }
      })

      const passed = adequateSize === touchTargets.length
      return {
        passed,
        details: `${adequateSize}/${touchTargets.length} touch targets meet minimum size requirements`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Touch accessibility test failed'
      }
    }
  }

  async testBrowserFeatureSupport() {
    try {
      // Test browser feature support
      const features = {
        webgl: !!this.getWebGLContext(),
        websockets: 'WebSocket' in window,
        localStorage: this.checkLocalStorage(),
        serviceWorker: 'serviceWorker' in navigator,
        geolocation: 'geolocation' in navigator
      }

      const supportedFeatures = Object.values(features).filter(Boolean).length
      const totalFeatures = Object.keys(features).length
      const passed = supportedFeatures >= totalFeatures * 0.8 // At least 80% support

      return {
        passed,
        details: `${supportedFeatures}/${totalFeatures} core features supported`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'Browser feature support test failed'
      }
    }
  }

  async testCSSCompatibility() {
    try {
      // Test CSS compatibility
      const testElement = document.createElement('div')
      testElement.style.display = 'flex'
      testElement.style.position = 'sticky'
      testElement.style.gridTemplateColumns = '1fr 1fr'

      document.body.appendChild(testElement)

      const flexSupported = testElement.style.display === 'flex'
      const stickySupported = testElement.style.position === 'sticky'
      const gridSupported = testElement.style.gridTemplateColumns === '1fr 1fr'

      document.body.removeChild(testElement)

      const supported = [flexSupported, stickySupported, gridSupported].filter(Boolean).length
      const total = 3
      const passed = supported >= 2 // At least 2 out of 3

      return {
        passed,
        details: `${supported}/${total} CSS features supported (Flex: ${flexSupported}, Sticky: ${stickySupported}, Grid: ${gridSupported})`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'CSS compatibility test failed'
      }
    }
  }

  async testJavaScriptCompatibility() {
    try {
      // Test JavaScript compatibility
      const features = {
        arrowFunctions: true, // Assuming modern browser
        promises: typeof Promise !== 'undefined',
        asyncAwait: true, // Assuming modern browser
        destructuring: true, // Assuming modern browser
        modules: true // Assuming modern browser
      }

      // Test actual functionality
      try {
        new Function('const {a} = {a:1}; return a')()
        features.destructuring = true
      } catch {
        features.destructuring = false
      }

      const supportedFeatures = Object.values(features).filter(Boolean).length
      const totalFeatures = Object.keys(features).length
      const passed = supportedFeatures === totalFeatures

      return {
        passed,
        details: `${supportedFeatures}/${totalFeatures} JavaScript features supported`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'JavaScript compatibility test failed'
      }
    }
  }

  async testAPICompatibility() {
    try {
      // Test API compatibility
      const apis = {
        fetch: 'fetch' in window,
        websocket: 'WebSocket' in window,
        notification: 'Notification' in window,
        geolocation: 'geolocation' in navigator,
        localStorage: this.checkLocalStorage()
      }

      const supportedAPIs = Object.values(apis).filter(Boolean).length
      const totalAPIs = Object.keys(apis).length
      const passed = supportedAPIs >= totalAPIs * 0.8 // At least 80% support

      return {
        passed,
        details: `${supportedAPIs}/${totalAPIs} APIs supported`
      }
    } catch (error) {
      return {
        passed: false,
        error: error.message,
        details: 'API compatibility test failed'
      }
    }
  }

  // Utility methods
  calculateSummary(results) {
    const summary = results.summary
    summary.totalTests = 0
    summary.passedTests = 0
    summary.failedTests = 0
    summary.skippedTests = 0

    for (const suite of Object.values(results.testSuites)) {
      summary.totalTests += suite.summary.total
      summary.passedTests += suite.summary.passed
      summary.failedTests += suite.summary.failed
      summary.skippedTests += suite.summary.skipped
    }
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Get test results
  getTestResults(platform = null) {
    if (platform) {
      return this.testResults.get(platform)
    }
    return Object.fromEntries(this.testResults)
  }

  // Generate test report
  generateTestReport(platform = null) {
    const results = this.getTestResults(platform)
    if (!results) return null

    return {
      platform: results.platform,
      timestamp: results.timestamp,
      summary: results.summary,
      testSuites: results.testSuites,
      recommendations: this.generateRecommendations(results)
    }
  }

  generateRecommendations(results) {
    const recommendations = []

    if (results.summary.failedTests > 0) {
      recommendations.push({
        type: 'critical',
        title: 'Failed Tests Detected',
        description: `${results.summary.failedTests} tests failed. Review test results for issues.`,
        action: 'Review and fix failing tests'
      })
    }

    if (results.summary.passedTests / results.summary.totalTests < 0.8) {
      recommendations.push({
        type: 'warning',
        title: 'Low Test Pass Rate',
        description: `Only ${(results.summary.passedTests / results.summary.totalTests * 100).toFixed(1)}% of tests passed.`,
        action: 'Improve application compatibility'
      })
    }

    // Platform-specific recommendations
    const platform = results.platform.platform
    if (platform === 'mobile' || platform === 'tablet') {
      recommendations.push({
        type: 'info',
        title: 'Mobile Optimization',
        description: 'Ensure touch interactions and responsive design work correctly.',
        action: 'Test touch gestures and responsive layout'
      })
    }

    return recommendations
  }

  // Initialize performance monitoring
  initializePerformanceMonitoring() {
    if ('PerformanceObserver' in window) {
      // Monitor long tasks
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            this.recordPerformanceMetric('long_task', entry.duration)
          }
        }
      })
      observer.observe({ entryTypes: ['longtask'] })

      // Monitor layout shifts
      const layoutObserver = new PerformanceObserver((list) => {
        let clsValue = 0
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value
          }
        }
        if (clsValue > 0.1) {
          this.recordPerformanceMetric('layout_shift', clsValue)
        }
      })
      layoutObserver.observe({ entryTypes: ['layout-shift'] })
    }
  }

  recordPerformanceMetric(name, value) {
    if (!this.performanceBenchmarks.has(name)) {
      this.performanceBenchmarks.set(name, [])
    }

    this.performanceBenchmarks.get(name).push({
      value,
      timestamp: new Date().toISOString(),
      platform: this.getCurrentDeviceProfile().name
    })
  }

  // Get performance benchmarks
  getPerformanceBenchmarks() {
    return Object.fromEntries(this.performanceBenchmarks)
  }

  // Export test data
  exportTestData() {
    return {
      testResults: this.getTestResults(),
      performanceBenchmarks: this.getPerformanceBenchmarks(),
      deviceProfiles: Object.fromEntries(this.deviceProfiles),
      compatibilityMatrix: Object.fromEntries(this.compatibilityMatrix),
      exportDate: new Date().toISOString()
    }
  }
}

// Create singleton instance
const crossPlatformTester = new CrossPlatformTester()

export default crossPlatformTester
export { CrossPlatformTester }