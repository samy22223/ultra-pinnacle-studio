// Progressive Enhancement System for Modern Browser Features

class ProgressiveEnhancementManager {
  constructor() {
    this.enhancements = new Map()
    this.featureSupport = new Map()
    this.enhancementQueue = []
    this.performanceMetrics = new Map()
  }

  // Initialize progressive enhancement system
  async initialize() {
    await this.detectFeatureSupport()
    this.registerEnhancements()
    await this.applyEnhancements()
    this.setupPerformanceMonitoring()

    console.log('Progressive enhancement system initialized')
  }

  // Detect support for modern features
  async detectFeatureSupport() {
    // Core Web APIs
    this.featureSupport.set('es6_modules', this.checkES6Modules())
    this.featureSupport.set('async_await', this.checkAsyncAwait())
    this.featureSupport.set('web_components', this.checkWebComponents())
    this.featureSupport.set('css_grid', this.checkCSSGrid())
    this.featureSupport.set('css_custom_properties', this.checkCSSCustomProperties())
    this.featureSupport.set('service_worker', this.checkServiceWorker())
    this.featureSupport.set('webgl', this.checkWebGL())
    this.featureSupport.set('web_rtc', this.checkWebRTC())
    this.featureSupport.set('indexeddb', this.checkIndexedDB())
    this.featureSupport.set('web_audio', this.checkWebAudio())
    this.featureSupport.set('web_animations', this.checkWebAnimations())
    this.featureSupport.set('intersection_observer', this.checkIntersectionObserver())
    this.featureSupport.set('resize_observer', this.checkResizeObserver())
    this.featureSupport.set('performance_observer', this.checkPerformanceObserver())

    // Advanced features
    this.featureSupport.set('webgpu', await this.checkWebGPU())
    this.featureSupport.set('webgl2', this.checkWebGL2())
    this.featureSupport.set('webassembly', this.checkWebAssembly())
    this.featureSupport.set('shared_workers', this.checkSharedWorkers())
    this.featureSupport.set('background_sync', this.checkBackgroundSync())
    this.featureSupport.set('periodic_sync', this.checkPeriodicSync())
    this.featureSupport.set('push_api', this.checkPushAPI())
    this.featureSupport.set('notification_api', this.checkNotificationAPI())
    this.featureSupport.set('geolocation_api', this.checkGeolocationAPI())
    this.featureSupport.set('device_orientation', this.checkDeviceOrientation())
    this.featureSupport.set('vibration_api', this.checkVibrationAPI())
    this.featureSupport.set('battery_api', this.checkBatteryAPI())
    this.featureSupport.set('network_info', this.checkNetworkInfo())
    this.featureSupport.set('payment_request', this.checkPaymentRequest())
    this.featureSupport.set('web_share', this.checkWebShare())
    this.featureSupport.set('web_credentials', this.checkWebCredentials())
    this.featureSupport.set('web_authn', this.checkWebAuthn())
    this.featureSupport.set('web_bluetooth', this.checkWebBluetooth())
    this.featureSupport.set('web_usb', this.checkWebUSB())
    this.featureSupport.set('web_nfc', this.checkWebNFC())
    this.featureSupport.set('web_serial', this.checkWebSerial())
    this.featureSupport.set('web_hid', this.checkWebHID())
    this.featureSupport.set('web_midi', this.checkWebMIDI())
    this.featureSupport.set('web_xr', this.checkWebXR())
    this.featureSupport.set('web_vr', this.checkWebVR())
    this.featureSupport.set('web_ar', this.checkWebAR())
  }

  // Feature support checks
  checkES6Modules() {
    return 'import' in document.createElement('script')
  }

  checkAsyncAwait() {
    try {
      new Function('async function test() { await Promise.resolve() }')
      return true
    } catch {
      return false
    }
  }

  checkWebComponents() {
    return 'customElements' in window && 'attachShadow' in document.createElement('div')
  }

  checkCSSGrid() {
    return CSS.supports('display', 'grid')
  }

  checkCSSCustomProperties() {
    return CSS.supports('--custom-property', 'value')
  }

  checkServiceWorker() {
    return 'serviceWorker' in navigator
  }

  checkWebGL() {
    try {
      const canvas = document.createElement('canvas')
      return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    } catch {
      return false
    }
  }

  checkWebRTC() {
    return 'RTCPeerConnection' in window || 'webkitRTCPeerConnection' in window
  }

  checkIndexedDB() {
    return 'indexedDB' in window
  }

  checkWebAudio() {
    return 'AudioContext' in window || 'webkitAudioContext' in window
  }

  checkWebAnimations() {
    return 'animate' in document.createElement('div')
  }

  checkIntersectionObserver() {
    return 'IntersectionObserver' in window
  }

  checkResizeObserver() {
    return 'ResizeObserver' in window
  }

  checkPerformanceObserver() {
    return 'PerformanceObserver' in window
  }

  async checkWebGPU() {
    return 'gpu' in navigator
  }

  checkWebGL2() {
    try {
      const canvas = document.createElement('canvas')
      return !!canvas.getContext('webgl2')
    } catch {
      return false
    }
  }

  checkWebAssembly() {
    return 'WebAssembly' in window
  }

  checkSharedWorkers() {
    return 'SharedWorker' in window
  }

  checkBackgroundSync() {
    return 'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype
  }

  checkPeriodicSync() {
    return 'serviceWorker' in navigator && 'periodicSync' in window.ServiceWorkerRegistration.prototype
  }

  checkPushAPI() {
    return 'pushManager' in window
  }

  checkNotificationAPI() {
    return 'Notification' in window
  }

  checkGeolocationAPI() {
    return 'geolocation' in navigator
  }

  checkDeviceOrientation() {
    return 'DeviceOrientationEvent' in window
  }

  checkVibrationAPI() {
    return 'vibrate' in navigator
  }

  checkBatteryAPI() {
    return 'getBattery' in navigator
  }

  checkNetworkInfo() {
    return 'connection' in navigator || 'mozConnection' in navigator || 'webkitConnection' in navigator
  }

  checkPaymentRequest() {
    return 'PaymentRequest' in window
  }

  checkWebShare() {
    return 'share' in navigator
  }

  checkWebCredentials() {
    return 'credentials' in navigator
  }

  checkWebAuthn() {
    return 'credentials' in navigator && 'get' in navigator.credentials
  }

  checkWebBluetooth() {
    return 'bluetooth' in navigator
  }

  checkWebUSB() {
    return 'usb' in navigator
  }

  checkWebNFC() {
    return 'nfc' in navigator
  }

  checkWebSerial() {
    return 'serial' in navigator
  }

  checkWebHID() {
    return 'hid' in navigator
  }

  checkWebMIDI() {
    return 'requestMIDIAccess' in navigator
  }

  checkWebXR() {
    return 'xr' in navigator
  }

  checkWebVR() {
    return 'getVRDisplays' in navigator
  }

  checkWebAR() {
    return 'xr' in navigator && navigator.xr?.isSessionSupported
  }

  // Register enhancement modules
  registerEnhancements() {
    // Core UI enhancements
    this.registerEnhancement('advanced_ui', {
      dependencies: ['css_custom_properties', 'css_grid'],
      priority: 'high',
      apply: () => this.applyAdvancedUI()
    })

    // WebGL enhancements
    this.registerEnhancement('webgl_accelerated', {
      dependencies: ['webgl'],
      priority: 'medium',
      apply: () => this.applyWebGLEnhancements()
    })

    // Service Worker enhancements
    this.registerEnhancement('offline_first', {
      dependencies: ['service_worker', 'indexeddb'],
      priority: 'high',
      apply: () => this.applyOfflineFirst()
    })

    // Real-time features
    this.registerEnhancement('real_time_collaboration', {
      dependencies: ['web_rtc', 'websockets'],
      priority: 'medium',
      apply: () => this.applyRealTimeFeatures()
    })

    // Advanced audio features
    this.registerEnhancement('audio_processing', {
      dependencies: ['web_audio'],
      priority: 'low',
      apply: () => this.applyAudioEnhancements()
    })

    // Device integration
    this.registerEnhancement('device_integration', {
      dependencies: ['web_bluetooth', 'web_usb', 'web_serial'],
      priority: 'low',
      apply: () => this.applyDeviceIntegration()
    })

    // Performance monitoring
    this.registerEnhancement('performance_monitoring', {
      dependencies: ['performance_observer', 'intersection_observer'],
      priority: 'medium',
      apply: () => this.applyPerformanceMonitoring()
    })

    // Modern authentication
    this.registerEnhancement('modern_auth', {
      dependencies: ['web_authn', 'web_credentials'],
      priority: 'medium',
      apply: () => this.applyModernAuth()
    })

    // Advanced sharing
    this.registerEnhancement('advanced_sharing', {
      dependencies: ['web_share', 'web_rtc'],
      priority: 'low',
      apply: () => this.applyAdvancedSharing()
    })

    // XR/VR/AR features
    this.registerEnhancement('immersive_experiences', {
      dependencies: ['web_xr', 'webgl2'],
      priority: 'low',
      apply: () => this.applyImmersiveExperiences()
    })
  }

  // Register a single enhancement
  registerEnhancement(name, config) {
    this.enhancements.set(name, {
      name,
      dependencies: config.dependencies || [],
      priority: config.priority || 'medium',
      apply: config.apply,
      enabled: false,
      applied: false
    })
  }

  // Apply all available enhancements
  async applyEnhancements() {
    const applicableEnhancements = this.getApplicableEnhancements()

    // Sort by priority
    const priorityOrder = { high: 3, medium: 2, low: 1 }
    applicableEnhancements.sort((a, b) => priorityOrder[b.priority] - priorityOrder[a.priority])

    for (const enhancement of applicableEnhancements) {
      try {
        const startTime = performance.now()
        await enhancement.apply()
        const endTime = performance.now()

        enhancement.applied = true
        enhancement.loadTime = endTime - startTime

        this.performanceMetrics.set(enhancement.name, {
          loadTime: enhancement.loadTime,
          timestamp: new Date().toISOString()
        })

        console.log(`Applied enhancement: ${enhancement.name} (${enhancement.loadTime.toFixed(2)}ms)`)
      } catch (error) {
        console.error(`Failed to apply enhancement ${enhancement.name}:`, error)
      }
    }
  }

  // Get enhancements that can be applied
  getApplicableEnhancements() {
    const applicable = []

    for (const [name, enhancement] of this.enhancements) {
      const dependenciesMet = enhancement.dependencies.every(dep =>
        this.featureSupport.get(dep) !== false
      )

      if (dependenciesMet) {
        applicable.push(enhancement)
      }
    }

    return applicable
  }

  // Enhancement implementations
  async applyAdvancedUI() {
    // Apply CSS Grid and Custom Properties enhancements
    document.documentElement.classList.add('advanced-ui-enabled')

    // Dynamic CSS custom properties
    const root = document.documentElement.style
    root.setProperty('--primary-color', '#007bff')
    root.setProperty('--animation-duration', '300ms')
    root.setProperty('--border-radius', '8px')

    // Advanced layout classes
    document.body.classList.add('grid-layout-enabled')
  }

  async applyWebGLEnhancements() {
    document.documentElement.classList.add('webgl-enhanced')

    // Initialize WebGL context for advanced features
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')

    if (gl) {
      // Enable advanced WebGL features
      gl.getExtension('OES_texture_float')
      gl.getExtension('OES_standard_derivatives')
      gl.getExtension('EXT_shader_texture_lod')
    }
  }

  async applyOfflineFirst() {
    // Register service worker for offline functionality
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js')
        console.log('Service Worker registered for offline-first experience')

        // Set up IndexedDB for offline data storage
        await this.initializeOfflineStorage()
      } catch (error) {
        console.error('Service Worker registration failed:', error)
      }
    }
  }

  async initializeOfflineStorage() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ultra_pinnacle_offline', 1)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        // Create object stores for offline data
        if (!db.objectStoreNames.contains('documents')) {
          db.createObjectStore('documents', { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains('user_data')) {
          db.createObjectStore('user_data', { keyPath: 'key' })
        }
        if (!db.objectStoreNames.contains('cache')) {
          db.createObjectStore('cache', { keyPath: 'url' })
        }
      }
    })
  }

  async applyRealTimeFeatures() {
    document.documentElement.classList.add('real-time-enabled')

    // Initialize WebRTC for peer-to-peer features
    this.initializeWebRTC()

    // Set up WebSocket connection for real-time updates
    this.initializeWebSocket()
  }

  initializeWebRTC() {
    // WebRTC initialization for real-time collaboration
    if (this.featureSupport.get('web_rtc')) {
      // Create RTCPeerConnection for potential P2P features
      this.peerConnection = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ]
      })
    }
  }

  initializeWebSocket() {
    // WebSocket initialization for real-time communication
    try {
      this.webSocket = new WebSocket('wss://echo.websocket.org')
      this.webSocket.onopen = () => {
        console.log('WebSocket connection established for real-time features')
      }
      this.webSocket.onclose = () => {
        console.log('WebSocket connection closed')
      }
    } catch (error) {
      console.error('WebSocket initialization failed:', error)
    }
  }

  async applyAudioEnhancements() {
    document.documentElement.classList.add('audio-enhanced')

    // Initialize Web Audio API for advanced audio features
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      this.audioContext = new AudioContext()

      // Create audio processing nodes
      this.analyser = this.audioContext.createAnalyser()
      this.gainNode = this.audioContext.createGain()

      console.log('Web Audio API initialized for enhanced audio features')
    } catch (error) {
      console.error('Web Audio API initialization failed:', error)
    }
  }

  async applyDeviceIntegration() {
    document.documentElement.classList.add('device-integration-enabled')

    // Initialize device connection APIs
    this.initializeDeviceAPIs()
  }

  async initializeDeviceAPIs() {
    // Web Bluetooth
    if (this.featureSupport.get('web_bluetooth')) {
      navigator.bluetooth.getAvailability().then(available => {
        if (available) {
          console.log('Web Bluetooth available for device integration')
        }
      })
    }

    // Web USB
    if (this.featureSupport.get('web_usb')) {
      console.log('Web USB available for device integration')
    }

    // Web Serial
    if (this.featureSupport.get('web_serial')) {
      console.log('Web Serial available for device integration')
    }
  }

  async applyPerformanceMonitoring() {
    // Set up comprehensive performance monitoring
    if (this.featureSupport.get('performance_observer')) {
      this.initializePerformanceObservers()
    }

    if (this.featureSupport.get('intersection_observer')) {
      this.initializeIntersectionObservers()
    }
  }

  initializePerformanceObservers() {
    // Monitor Core Web Vitals
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        this.recordPerformanceMetric(entry.name, entry.value)
      }
    })

    observer.observe({ entryTypes: ['measure'] })

    // Monitor long tasks
    const longTaskObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > 50) {
          console.warn('Long task detected:', entry.duration, 'ms')
          this.recordPerformanceMetric('long_task', entry.duration)
        }
      }
    })

    longTaskObserver.observe({ entryTypes: ['longtask'] })
  }

  initializeIntersectionObservers() {
    // Lazy loading and performance optimizations
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Element is visible, can trigger lazy loading
          this.handleElementVisible(entry.target)
        }
      })
    }, {
      rootMargin: '50px'
    })

    // Observe elements that can be lazy loaded
    document.querySelectorAll('[data-lazy]').forEach(el => {
      observer.observe(el)
    })
  }

  async applyModernAuth() {
    document.documentElement.classList.add('modern-auth-enabled')

    // Initialize WebAuthn for passwordless authentication
    if (this.featureSupport.get('web_authn')) {
      console.log('WebAuthn available for modern authentication')
    }
  }

  async applyAdvancedSharing() {
    document.documentElement.classList.add('advanced-sharing-enabled')

    // Initialize Web Share API
    if (this.featureSupport.get('web_share')) {
      console.log('Web Share API available for advanced sharing')
    }
  }

  async applyImmersiveExperiences() {
    document.documentElement.classList.add('immersive-enabled')

    // Initialize WebXR for VR/AR experiences
    if (this.featureSupport.get('web_xr')) {
      this.initializeWebXR()
    }
  }

  async initializeWebXR() {
    try {
      const supported = await navigator.xr.isSessionSupported('immersive-vr')
      if (supported) {
        console.log('WebXR immersive VR supported')
      }
    } catch (error) {
      console.error('WebXR initialization failed:', error)
    }
  }

  // Utility methods
  recordPerformanceMetric(name, value) {
    this.performanceMetrics.set(name, {
      value,
      timestamp: new Date().toISOString()
    })
  }

  handleElementVisible(element) {
    // Handle lazy loading when element becomes visible
    const src = element.dataset.lazySrc
    if (src) {
      element.src = src
      element.classList.remove('lazy')
      delete element.dataset.lazySrc
    }
  }

  // Get enhancement status
  getEnhancementStatus() {
    const status = {}

    for (const [name, enhancement] of this.enhancements) {
      status[name] = {
        enabled: enhancement.enabled,
        applied: enhancement.applied,
        loadTime: enhancement.loadTime,
        dependencies: enhancement.dependencies,
        priority: enhancement.priority
      }
    }

    return status
  }

  // Get feature support report
  getFeatureSupportReport() {
    return {
      features: Object.fromEntries(this.featureSupport),
      enhancements: this.getEnhancementStatus(),
      performance: Object.fromEntries(this.performanceMetrics),
      timestamp: new Date().toISOString()
    }
  }

  // Enable/disable specific enhancement
  setEnhancementEnabled(name, enabled) {
    const enhancement = this.enhancements.get(name)
    if (enhancement) {
      enhancement.enabled = enabled

      if (enabled && !enhancement.applied) {
        enhancement.apply().then(() => {
          enhancement.applied = true
        }).catch(error => {
          console.error(`Failed to apply enhancement ${name}:`, error)
        })
      }
    }
  }

  // Check if enhancement is available
  isEnhancementAvailable(name) {
    const enhancement = this.enhancements.get(name)
    if (!enhancement) return false

    return enhancement.dependencies.every(dep =>
      this.featureSupport.get(dep) !== false
    )
  }

  // Get recommended enhancements
  getRecommendedEnhancements() {
    return Array.from(this.enhancements.values())
      .filter(enhancement => this.isEnhancementAvailable(enhancement.name))
      .sort((a, b) => {
        const priorityOrder = { high: 3, medium: 2, low: 1 }
        return priorityOrder[b.priority] - priorityOrder[a.priority]
      })
  }
}

// Create singleton instance
const progressiveEnhancementManager = new ProgressiveEnhancementManager()

export default progressiveEnhancementManager
export { ProgressiveEnhancementManager }