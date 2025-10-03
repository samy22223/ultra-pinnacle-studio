// Browser Fallback Mechanisms and Progressive Enhancement

class BrowserFallbackManager {
  constructor() {
    this.fallbacks = new Map()
    this.enhancements = new Map()
    this.browserSupport = this.detectBrowserSupport()
    this.featureFlags = new Map()
  }

  // Initialize fallback system
  async initialize() {
    this.setupFallbacks()
    this.setupProgressiveEnhancements()
    this.applyBrowserSpecificFixes()
    this.initializeFeatureFlags()

    console.log('Browser fallback system initialized')
  }

  // Detect comprehensive browser support
  detectBrowserSupport() {
    const ua = navigator.userAgent
    const browser = this.getBrowserInfo()

    return {
      browser,
      features: {
        // Core web APIs
        fetch: 'fetch' in window,
        promises: typeof Promise !== 'undefined',
        asyncAwait: this.checkAsyncAwaitSupport(),
        modules: 'import' in document.createElement('script'),

        // Modern JavaScript features
        arrowFunctions: this.checkArrowFunctionSupport(),
        templateLiterals: this.checkTemplateLiteralSupport(),
        destructuring: this.checkDestructuringSupport(),
        spreadOperator: this.checkSpreadOperatorSupport(),
        classes: this.checkClassSupport(),
        asyncGenerators: this.checkAsyncGeneratorSupport(),

        // DOM APIs
        querySelector: 'querySelector' in document,
        addEventListener: 'addEventListener' in window,
        classList: 'classList' in document.createElement('div'),
        dataset: 'dataset' in document.createElement('div'),

        // Advanced APIs
        webgl: this.checkWebGLSupport(),
        websockets: 'WebSocket' in window,
        webworkers: 'Worker' in window,
        serviceWorker: 'serviceWorker' in navigator,
        pushManager: 'pushManager' in window,
        notification: 'Notification' in window,
        geolocation: 'geolocation' in navigator,
        localStorage: this.checkLocalStorageSupport(),
        indexedDB: 'indexedDB' in window,
        webRTC: 'RTCPeerConnection' in window,

        // CSS features
        flexbox: this.checkFlexboxSupport(),
        grid: this.checkGridSupport(),
        customProperties: this.checkCustomPropertiesSupport(),
        transforms: this.checkTransformSupport(),

        // Input APIs
        touchEvents: 'ontouchstart' in window,
        pointerEvents: 'PointerEvent' in window,
        gamepad: 'getGamepads' in navigator,

        // Media APIs
        webAudio: 'AudioContext' in window || 'webkitAudioContext' in window,
        webRTC: 'RTCPeerConnection' in window,
        mediaRecorder: 'MediaRecorder' in window,
        getUserMedia: 'getUserMedia' in navigator || 'webkitGetUserMedia' in navigator,

        // Performance APIs
        performanceObserver: 'PerformanceObserver' in window,
        intersectionObserver: 'IntersectionObserver' in window,
        resizeObserver: 'ResizeObserver' in window
      },

      // Browser-specific capabilities
      capabilities: {
        chrome: browser.name === 'chrome',
        firefox: browser.name === 'firefox',
        safari: browser.name === 'safari',
        edge: browser.name === 'edge',
        opera: browser.name === 'opera',
        mobile: this.isMobileDevice(),
        tablet: this.isTabletDevice()
      }
    }
  }

  getBrowserInfo() {
    const ua = navigator.userAgent

    if (ua.includes('Chrome') && !ua.includes('Edg/')) {
      return { name: 'chrome', version: this.getChromeVersion(ua) }
    } else if (ua.includes('Firefox/')) {
      return { name: 'firefox', version: this.getFirefoxVersion(ua) }
    } else if (ua.includes('Safari/') && !ua.includes('Chrome/')) {
      return { name: 'safari', version: this.getSafariVersion(ua) }
    } else if (ua.includes('Edg/')) {
      return { name: 'edge', version: this.getEdgeVersion(ua) }
    } else if (ua.includes('OPR/') || ua.includes('Opera/')) {
      return { name: 'opera', version: this.getOperaVersion(ua) }
    }

    return { name: 'unknown', version: '0.0' }
  }

  getChromeVersion(ua) {
    const match = ua.match(/Chrome\/(\d+)/)
    return match ? match[1] : '0'
  }

  getFirefoxVersion(ua) {
    const match = ua.match(/Firefox\/(\d+)/)
    return match ? match[1] : '0'
  }

  getSafariVersion(ua) {
    const match = ua.match(/Version\/(\d+)/)
    return match ? match[1] : '0'
  }

  getEdgeVersion(ua) {
    const match = ua.match(/Edg\/(\d+)/)
    return match ? match[1] : '0'
  }

  getOperaVersion(ua) {
    const match = ua.match(/OPR\/(\d+)/)
    return match ? match[1] : '0'
  }

  isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
  }

  isTabletDevice() {
    return /iPad|Android(?=.*\bMobile\b)|Tablet/i.test(navigator.userAgent)
  }

  // Feature support checks
  checkAsyncAwaitSupport() {
    try {
      new Function('async function test() { await Promise.resolve() }')
      return true
    } catch {
      return false
    }
  }

  checkArrowFunctionSupport() {
    try {
      new Function('() => {}')
      return true
    } catch {
      return false
    }
  }

  checkTemplateLiteralSupport() {
    try {
      new Function('`test`')
      return true
    } catch {
      return false
    }
  }

  checkDestructuringSupport() {
    try {
      new Function('const {a} = {a:1}')
      return true
    } catch {
      return false
    }
  }

  checkSpreadOperatorSupport() {
    try {
      new Function('[...[1,2,3]]')
      return true
    } catch {
      return false
    }
  }

  checkClassSupport() {
    try {
      new Function('class Test {}')
      return true
    } catch {
      return false
    }
  }

  checkAsyncGeneratorSupport() {
    try {
      new Function('async function* test() { yield await Promise.resolve() }')
      return true
    } catch {
      return false
    }
  }

  checkWebGLSupport() {
    try {
      const canvas = document.createElement('canvas')
      return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    } catch {
      return false
    }
  }

  checkLocalStorageSupport() {
    try {
      const test = 'test'
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch {
      return false
    }
  }

  checkFlexboxSupport() {
    const div = document.createElement('div')
    div.style.display = 'flex'
    return div.style.display === 'flex'
  }

  checkGridSupport() {
    const div = document.createElement('div')
    div.style.display = 'grid'
    return div.style.display === 'grid'
  }

  checkCustomPropertiesSupport() {
    return CSS.supports('--custom-property', 'value')
  }

  checkTransformSupport() {
    const div = document.createElement('div')
    div.style.transform = 'translateX(10px)'
    return div.style.transform === 'translateX(10px)'
  }

  // Setup fallback mechanisms
  setupFallbacks() {
    // Promise polyfill
    if (!this.browserSupport.features.promises) {
      this.loadPolyfill('https://cdn.jsdelivr.net/npm/es6-promise@4.2.8/dist/es6-promise.auto.min.js')
    }

    // Fetch API polyfill
    if (!this.browserSupport.features.fetch) {
      this.loadPolyfill('https://cdn.jsdelivr.net/npm/whatwg-fetch@3.6.2/dist/fetch.umd.js')
    }

    // Web Components polyfill
    if (!window.customElements) {
      this.loadPolyfill('https://unpkg.com/@webcomponents/webcomponentsjs@2.6.0/webcomponents-bundle.js')
    }

    // Intersection Observer polyfill
    if (!this.browserSupport.features.intersectionObserver) {
      this.loadPolyfill('https://polyfill.io/v3/polyfill.min.js?features=IntersectionObserver')
    }

    // Resize Observer polyfill
    if (!this.browserSupport.features.resizeObserver) {
      this.loadPolyfill('https://unpkg.com/resize-observer-polyfill@1.5.1/dist/ResizeObserver.global.js')
    }

    // LocalStorage fallback
    if (!this.browserSupport.features.localStorage) {
      this.setupLocalStorageFallback()
    }

    // ClassList polyfill
    if (!this.browserSupport.features.classList) {
      this.loadPolyfill('https://cdn.jsdelivr.net/npm/classlist-polyfill@1.2.0/src/index.js')
    }
  }

  // Load polyfill script
  loadPolyfill(url) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = url
      script.onload = resolve
      script.onerror = reject
      document.head.appendChild(script)
    })
  }

  // Setup localStorage fallback
  setupLocalStorageFallback() {
    if (!window.localStorage) {
      const data = {}
      window.localStorage = {
        getItem: (key) => data[key] || null,
        setItem: (key, value) => { data[key] = value },
        removeItem: (key) => { delete data[key] },
        clear: () => { Object.keys(data).forEach(key => delete data[key]) }
      }
    }
  }

  // Setup progressive enhancements
  setupProgressiveEnhancements() {
    // Service Worker enhancement
    if (this.browserSupport.features.serviceWorker) {
      this.registerServiceWorker()
    }

    // WebGL enhancement
    if (this.browserSupport.features.webgl) {
      this.enableWebGLEnhancements()
    }

    // Touch enhancements
    if (this.browserSupport.features.touchEvents) {
      this.enableTouchEnhancements()
    }

    // Performance monitoring
    if (this.browserSupport.features.performanceObserver) {
      this.enablePerformanceMonitoring()
    }

    // CSS Grid enhancement
    if (this.browserSupport.features.grid) {
      document.documentElement.classList.add('css-grid-supported')
    }

    // Custom Properties enhancement
    if (this.browserSupport.features.customProperties) {
      document.documentElement.classList.add('css-custom-properties-supported')
    }
  }

  // Register service worker
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js')
        console.log('Service Worker registered:', registration.scope)

        // Handle updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                this.notifyUserOfUpdate()
              }
            })
          }
        })
      } catch (error) {
        console.error('Service Worker registration failed:', error)
      }
    }
  }

  // Enable WebGL enhancements
  enableWebGLEnhancements() {
    document.documentElement.classList.add('webgl-supported')
    // Additional WebGL-specific enhancements can be added here
  }

  // Enable touch enhancements
  enableTouchEnhancements() {
    document.documentElement.classList.add('touch-supported')

    // Prevent zoom on double-tap (iOS)
    if (this.browserSupport.capabilities.safari && this.browserSupport.capabilities.mobile) {
      let lastTouchEnd = 0
      document.addEventListener('touchend', (event) => {
        const now = Date.now()
        if (now - lastTouchEnd <= 300) {
          event.preventDefault()
        }
        lastTouchEnd = now
      }, false)
    }
  }

  // Enable performance monitoring
  enablePerformanceMonitoring() {
    if ('PerformanceObserver' in window) {
      // Monitor long tasks
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) { // Long task > 50ms
            console.warn('Long task detected:', entry)
            this.reportPerformanceIssue('long_task', entry)
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
          console.warn('High CLS detected:', clsValue)
          this.reportPerformanceIssue('layout_shift', { value: clsValue })
        }
      })
      layoutObserver.observe({ entryTypes: ['layout-shift'] })
    }
  }

  // Apply browser-specific fixes
  applyBrowserSpecificFixes() {
    const browser = this.browserSupport.browser.name

    switch (browser) {
      case 'firefox':
        this.applyFirefoxFixes()
        break
      case 'safari':
        this.applySafariFixes()
        break
      case 'edge':
        this.applyEdgeFixes()
        break
      case 'opera':
        this.applyOperaFixes()
        break
    }

    // Mobile-specific fixes
    if (this.browserSupport.capabilities.mobile) {
      this.applyMobileFixes()
    }
  }

  applyFirefoxFixes() {
    // Firefox-specific CSS fixes
    const style = document.createElement('style')
    style.textContent = `
      /* Firefox scrollbar styling */
      * {
        scrollbar-width: thin;
        scrollbar-color: #888 #f1f1f1;
      }
    `
    document.head.appendChild(style)
  }

  applySafariFixes() {
    // Safari-specific fixes
    const style = document.createElement('style')
    style.textContent = `
      /* Safari touch scrolling fix */
      * {
        -webkit-overflow-scrolling: touch;
      }

      /* Safari input zoom fix */
      input[type="text"],
      input[type="email"],
      input[type="password"],
      textarea {
        font-size: 16px;
      }
    `
    document.head.appendChild(style)
  }

  applyEdgeFixes() {
    // Edge-specific fixes
    document.documentElement.classList.add('edge-browser')
  }

  applyOperaFixes() {
    // Opera-specific fixes
    document.documentElement.classList.add('opera-browser')
  }

  applyMobileFixes() {
    // Mobile-specific enhancements
    document.documentElement.classList.add('mobile-device')

    // Viewport meta tag
    if (!document.querySelector('meta[name="viewport"]')) {
      const viewport = document.createElement('meta')
      viewport.name = 'viewport'
      viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes'
      document.head.appendChild(viewport)
    }

    // Prevent pull-to-refresh on mobile
    document.addEventListener('touchmove', (e) => {
      if (e.touches.length > 1) {
        e.preventDefault()
      }
    }, { passive: false })
  }

  // Initialize feature flags
  initializeFeatureFlags() {
    // Define feature flags based on browser support
    this.featureFlags.set('advanced_ui', this.browserSupport.features.customProperties && this.browserSupport.features.grid)
    this.featureFlags.set('webgl_features', this.browserSupport.features.webgl)
    this.featureFlags.set('offline_support', this.browserSupport.features.serviceWorker)
    this.featureFlags.set('push_notifications', this.browserSupport.features.pushManager && this.browserSupport.features.notification)
    this.featureFlags.set('touch_gestures', this.browserSupport.features.touchEvents)
    this.featureFlags.set('performance_monitoring', this.browserSupport.features.performanceObserver)
    this.featureFlags.set('real_time_sync', this.browserSupport.features.websockets)
  }

  // Check if feature is enabled
  isFeatureEnabled(featureName) {
    return this.featureFlags.get(featureName) || false
  }

  // Enable/disable feature
  setFeatureEnabled(featureName, enabled) {
    this.featureFlags.set(featureName, enabled)

    // Apply feature-specific changes
    const featureClass = `feature-${featureName.replace(/_/g, '-')}`
    if (enabled) {
      document.documentElement.classList.add(featureClass)
    } else {
      document.documentElement.classList.remove(featureClass)
    }
  }

  // Get fallback for unsupported feature
  getFallback(featureName) {
    const fallbacks = {
      fetch: () => {
        // XMLHttpRequest fallback
        window.fetch = function(url, options = {}) {
          return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest()
            xhr.open(options.method || 'GET', url)

            if (options.headers) {
              Object.entries(options.headers).forEach(([key, value]) => {
                xhr.setRequestHeader(key, value)
              })
            }

            xhr.onload = () => {
              resolve({
                ok: xhr.status >= 200 && xhr.status < 300,
                status: xhr.status,
                statusText: xhr.statusText,
                text: () => Promise.resolve(xhr.responseText),
                json: () => Promise.resolve(JSON.parse(xhr.responseText))
              })
            }

            xhr.onerror = reject
            xhr.send(options.body)
          })
        }
      },

      promises: () => {
        // Very basic Promise polyfill (would normally use a proper polyfill)
        if (!window.Promise) {
          console.warn('Promise polyfill not loaded - some features may not work')
        }
      },

      localStorage: () => {
        // Already handled in setupLocalStorageFallback
      }
    }

    return fallbacks[featureName]
  }

  // Report performance issue
  reportPerformanceIssue(type, data) {
    // In a real implementation, this would send to analytics
    console.warn(`Performance issue detected: ${type}`, data)

    // Could trigger fallback mechanisms or user notifications
    if (type === 'long_task') {
      // Suggest performance optimizations
      this.suggestPerformanceOptimization()
    }
  }

  // Suggest performance optimization
  suggestPerformanceOptimization() {
    // Could show user notification or automatically apply optimizations
    console.log('Consider implementing performance optimizations')
  }

  // Notify user of service worker update
  notifyUserOfUpdate() {
    // Create update notification
    const notification = document.createElement('div')
    notification.className = 'update-notification'
    notification.innerHTML = `
      <div class="update-content">
        <h4>Application Updated</h4>
        <p>A new version is available. Refresh to update.</p>
        <button onclick="window.location.reload()">Refresh Now</button>
        <button onclick="this.parentElement.parentElement.remove()">Later</button>
      </div>
    `
    document.body.appendChild(notification)
  }

  // Get comprehensive browser report
  getBrowserReport() {
    return {
      browser: this.browserSupport.browser,
      features: this.browserSupport.features,
      capabilities: this.browserSupport.capabilities,
      featureFlags: Object.fromEntries(this.featureFlags),
      fallbacks: Array.from(this.fallbacks.keys()),
      enhancements: Array.from(this.enhancements.keys())
    }
  }

  // Export fallback configuration
  exportConfiguration() {
    return {
      browserSupport: this.browserSupport,
      featureFlags: Object.fromEntries(this.featureFlags),
      timestamp: new Date().toISOString()
    }
  }

  // Import fallback configuration
  importConfiguration(config) {
    if (config.featureFlags) {
      Object.entries(config.featureFlags).forEach(([feature, enabled]) => {
        this.setFeatureEnabled(feature, enabled)
      })
    }
  }
}

// Create singleton instance
const browserFallbackManager = new BrowserFallbackManager()

export default browserFallbackManager
export { BrowserFallbackManager }