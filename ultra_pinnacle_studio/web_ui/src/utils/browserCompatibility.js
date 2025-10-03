// Browser compatibility utilities and polyfills
export const detectBrowser = () => {
  const ua = navigator.userAgent

  if (ua.includes('Firefox/')) {
    return 'firefox'
  } else if (ua.includes('Chrome/') && !ua.includes('Edg/')) {
    return 'chrome'
  } else if (ua.includes('Safari/') && !ua.includes('Chrome/')) {
    return 'safari'
  } else if (ua.includes('Edg/')) {
    return 'edge'
  } else if (ua.includes('OPR/') || ua.includes('Opera/')) {
    return 'opera'
  }

  return 'unknown'
}

export const getBrowserCapabilities = () => {
  return {
    webgl: !!window.WebGLRenderingContext,
    websockets: 'WebSocket' in window,
    serviceWorker: 'serviceWorker' in navigator,
    pushManager: 'pushManager' in window && 'Notification' in window,
    vibration: 'vibrate' in navigator,
    geolocation: 'geolocation' in navigator,
    localStorage: (() => {
      try {
        localStorage.setItem('test', 'test')
        localStorage.removeItem('test')
        return true
      } catch {
        return false
      }
    })(),
    indexedDB: 'indexedDB' in window,
    webWorkers: 'Worker' in window,
    touchEvents: 'ontouchstart' in window,
    pointerEvents: 'PointerEvent' in window,
    cssGrid: CSS.supports('display', 'grid'),
    cssFlexbox: CSS.supports('display', 'flex'),
    cssCustomProperties: CSS.supports('--custom-property', 'value'),
    intersectionObserver: 'IntersectionObserver' in window,
    mutationObserver: 'MutationObserver' in window,
    resizeObserver: 'ResizeObserver' in window,
    performanceObserver: 'PerformanceObserver' in window
  }
}

export const loadPolyfills = async () => {
  const capabilities = getBrowserCapabilities()

  // Load Web Components polyfill if needed
  if (!window.customElements) {
    await loadScript('https://unpkg.com/@webcomponents/webcomponentsjs@2.6.0/webcomponents-bundle.js')
  }

  // Load Intersection Observer polyfill
  if (!capabilities.intersectionObserver) {
    await loadScript('https://polyfill.io/v3/polyfill.min.js?features=IntersectionObserver')
  }

  // Load Resize Observer polyfill
  if (!capabilities.resizeObserver) {
    await loadScript('https://unpkg.com/resize-observer-polyfill@1.5.1/dist/ResizeObserver.global.js')
  }

  // Load CSS Grid polyfill for older browsers
  if (!capabilities.cssGrid) {
    console.warn('CSS Grid not supported. Consider using flexbox fallbacks.')
  }
}

const loadScript = (src) => {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

export const applyBrowserSpecificFixes = () => {
  const browser = detectBrowser()

  switch (browser) {
    case 'firefox':
      // Firefox-specific fixes
      document.documentElement.style.setProperty('--firefox-scrollbar-width', '17px')
      break

    case 'safari':
      // Safari-specific fixes
      document.documentElement.style.setProperty('--safari-safe-area-inset', 'env(safe-area-inset-bottom)')
      // Fix for Safari's handling of flexbox
      if (CSS.supports('display', 'flex')) {
        document.documentElement.classList.add('flexbox-supported')
      }
      break

    case 'edge':
      // Edge-specific fixes
      document.documentElement.classList.add('edge-browser')
      break

    case 'opera':
      // Opera-specific fixes
      document.documentElement.classList.add('opera-browser')
      break
  }

  // Add touch device class
  if ('ontouchstart' in window) {
    document.documentElement.classList.add('touch-device')
  }

  // Add reduced motion preference
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.classList.add('reduced-motion')
  }
}

export const initializeBrowserCompatibility = async () => {
  try {
    await loadPolyfills()
    applyBrowserSpecificFixes()

    // Log browser information for debugging
    console.log('Browser:', detectBrowser())
    console.log('Capabilities:', getBrowserCapabilities())

    return true
  } catch (error) {
    console.error('Failed to initialize browser compatibility:', error)
    return false
  }
}

// Progressive enhancement utilities
export const progressiveEnhancement = {
  // Check if a feature is supported and provide fallback
  withFallback: (featureCheck, enhancedImpl, fallbackImpl) => {
    return featureCheck() ? enhancedImpl : fallbackImpl
  },

  // Load feature asynchronously with fallback
  loadFeature: async (featureLoader, fallback) => {
    try {
      return await featureLoader()
    } catch (error) {
      console.warn('Feature loading failed, using fallback:', error)
      return fallback
    }
  }
}

// Touch and gesture support
export const touchSupport = {
  isTouchDevice: () => 'ontouchstart' in window,

  addTouchGestures: (element, handlers) => {
    if (!touchSupport.isTouchDevice()) return

    let startX, startY, startTime

    const handleStart = (e) => {
      startX = e.touches[0].clientX
      startY = e.touches[0].clientY
      startTime = Date.now()
    }

    const handleEnd = (e) => {
      if (!startX || !startY) return

      const endX = e.changedTouches[0].clientX
      const endY = e.changedTouches[0].clientY
      const endTime = Date.now()

      const deltaX = endX - startX
      const deltaY = endY - startY
      const deltaTime = endTime - startTime

      // Detect swipe gestures
      if (Math.abs(deltaX) > 50 && deltaTime < 500) {
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          if (deltaX > 0 && handlers.onSwipeRight) {
            handlers.onSwipeRight(e)
          } else if (deltaX < 0 && handlers.onSwipeLeft) {
            handlers.onSwipeLeft(e)
          }
        }
      }

      // Detect tap
      if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10 && deltaTime < 300 && handlers.onTap) {
        handlers.onTap(e)
      }
    }

    element.addEventListener('touchstart', handleStart, { passive: true })
    element.addEventListener('touchend', handleEnd, { passive: true })

    return () => {
      element.removeEventListener('touchstart', handleStart)
      element.removeEventListener('touchend', handleEnd)
    }
  },

  addHapticFeedback: (pattern = [50]) => {
    if ('vibrate' in navigator) {
      navigator.vibrate(pattern)
    }
  }
}

export default {
  detectBrowser,
  getBrowserCapabilities,
  loadPolyfills,
  applyBrowserSpecificFixes,
  initializeBrowserCompatibility,
  progressiveEnhancement,
  touchSupport
}