// Touch Gesture Controls and Haptic Feedback System

class TouchGestureController {
  constructor() {
    this.gestureHandlers = new Map()
    this.activeGestures = new Set()
    this.hapticSupported = this.checkHapticSupport()
    this.touchStartTime = 0
    this.touchStartX = 0
    this.touchStartY = 0
    this.lastTapTime = 0
    this.tapCount = 0
  }

  checkHapticSupport() {
    return 'vibrate' in navigator ||
           'haptics' in navigator ||
           window.TapticEngine
  }

  // Initialize touch gesture handling for an element
  addGestureSupport(element, options = {}) {
    const defaultOptions = {
      enableSwipe: true,
      enablePinch: true,
      enableRotate: false,
      enableLongPress: true,
      enableDoubleTap: true,
      enableTripleTap: false,
      swipeThreshold: 50,
      longPressDelay: 500,
      doubleTapDelay: 300,
      ...options
    }

    const gestureId = this.generateGestureId(element)
    this.gestureHandlers.set(gestureId, {
      element,
      options: defaultOptions,
      touchStart: this.handleTouchStart.bind(this, gestureId),
      touchMove: this.handleTouchMove.bind(this, gestureId),
      touchEnd: this.handleTouchEnd.bind(this, gestureId)
    })

    this.attachEventListeners(element, gestureId)
    return gestureId
  }

  generateGestureId(element) {
    return `gesture_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  attachEventListeners(element, gestureId) {
    const handlers = this.gestureHandlers.get(gestureId)

    element.addEventListener('touchstart', handlers.touchStart, { passive: false })
    element.addEventListener('touchmove', handlers.touchMove, { passive: false })
    element.addEventListener('touchend', handlers.touchEnd, { passive: false })

    // Prevent default touch behaviors that might interfere
    element.addEventListener('touchstart', e => {
      if (handlers.options.enableSwipe || handlers.options.enablePinch) {
        e.preventDefault()
      }
    }, { passive: false })
  }

  removeGestureSupport(gestureId) {
    const handlers = this.gestureHandlers.get(gestureId)
    if (handlers) {
      const { element } = handlers
      element.removeEventListener('touchstart', handlers.touchStart)
      element.removeEventListener('touchmove', handlers.touchMove)
      element.removeEventListener('touchend', handlers.touchEnd)

      this.gestureHandlers.delete(gestureId)
    }
  }

  handleTouchStart(gestureId, event) {
    const handlers = this.gestureHandlers.get(gestureId)
    if (!handlers) return

    const touches = event.touches
    const firstTouch = touches[0]

    handlers.touchData = {
      startTime: Date.now(),
      startX: firstTouch.clientX,
      startY: firstTouch.clientY,
      touches: Array.from(touches).map(touch => ({
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY
      }))
    }

    // Handle multi-touch gestures
    if (touches.length === 2 && handlers.options.enablePinch) {
      handlers.touchData.initialDistance = this.getTouchDistance(touches[0], touches[1])
      handlers.touchData.initialAngle = this.getTouchAngle(touches[0], touches[1])
    }

    // Start long press timer
    if (handlers.options.enableLongPress) {
      handlers.longPressTimer = setTimeout(() => {
        this.triggerGesture(gestureId, 'longPress', {
          x: firstTouch.clientX,
          y: firstTouch.clientY,
          duration: Date.now() - handlers.touchData.startTime
        })
        this.vibrate('medium')
      }, handlers.options.longPressDelay)
    }
  }

  handleTouchMove(gestureId, event) {
    const handlers = this.gestureHandlers.get(gestureId)
    if (!handlers || !handlers.touchData) return

    const touches = event.touches
    const firstTouch = touches[0]

    // Clear long press timer if moved
    if (handlers.longPressTimer) {
      clearTimeout(handlers.longPressTimer)
      handlers.longPressTimer = null
    }

    const deltaX = firstTouch.clientX - handlers.touchData.startX
    const deltaY = firstTouch.clientY - handlers.touchData.startY
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

    // Handle swipe gestures
    if (handlers.options.enableSwipe && distance > handlers.options.swipeThreshold) {
      const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI
      let direction = this.getSwipeDirection(angle)

      this.triggerGesture(gestureId, 'swipe', {
        direction,
        distance,
        velocity: distance / (Date.now() - handlers.touchData.startTime),
        startX: handlers.touchData.startX,
        startY: handlers.touchData.startY,
        endX: firstTouch.clientX,
        endY: firstTouch.clientY
      })

      this.vibrate('light')
    }

    // Handle pinch gestures
    if (touches.length === 2 && handlers.options.enablePinch) {
      const currentDistance = this.getTouchDistance(touches[0], touches[1])
      const scale = currentDistance / handlers.touchData.initialDistance

      if (Math.abs(scale - 1) > 0.1) {
        this.triggerGesture(gestureId, 'pinch', {
          scale,
          center: this.getTouchCenter(touches[0], touches[1])
        })
      }
    }

    // Handle rotate gestures
    if (touches.length === 2 && handlers.options.enableRotate) {
      const currentAngle = this.getTouchAngle(touches[0], touches[1])
      const rotation = currentAngle - handlers.touchData.initialAngle

      if (Math.abs(rotation) > 5) {
        this.triggerGesture(gestureId, 'rotate', {
          rotation,
          center: this.getTouchCenter(touches[0], touches[1])
        })
      }
    }
  }

  handleTouchEnd(gestureId, event) {
    const handlers = this.gestureHandlers.get(gestureId)
    if (!handlers || !handlers.touchData) return

    const touches = event.changedTouches
    const firstTouch = touches[0]
    const duration = Date.now() - handlers.touchData.startTime

    // Clear long press timer
    if (handlers.longPressTimer) {
      clearTimeout(handlers.longPressTimer)
      handlers.longPressTimer = null
    }

    // Handle tap gestures
    const deltaX = Math.abs(firstTouch.clientX - handlers.touchData.startX)
    const deltaY = Math.abs(firstTouch.clientY - handlers.touchData.startY)
    const maxDelta = Math.max(deltaX, deltaY)

    if (maxDelta < 10 && duration < 300) {
      this.handleTap(gestureId, firstTouch)
    }

    // Clean up touch data
    handlers.touchData = null
  }

  handleTap(gestureId, touch) {
    const handlers = this.gestureHandlers.get(gestureId)
    const now = Date.now()
    const timeSinceLastTap = now - this.lastTapTime

    if (timeSinceLastTap < handlers.options.doubleTapDelay) {
      this.tapCount++
    } else {
      this.tapCount = 1
    }

    this.lastTapTime = now

    // Handle multi-tap gestures
    setTimeout(() => {
      if (this.tapCount === 1 && handlers.options.enableDoubleTap === false) {
        this.triggerGesture(gestureId, 'tap', {
          x: touch.clientX,
          y: touch.clientY,
          count: 1
        })
        this.vibrate('light')
      } else if (this.tapCount === 2 && handlers.options.enableDoubleTap) {
        this.triggerGesture(gestureId, 'doubleTap', {
          x: touch.clientX,
          y: touch.clientY
        })
        this.vibrate('medium')
      } else if (this.tapCount === 3 && handlers.options.enableTripleTap) {
        this.triggerGesture(gestureId, 'tripleTap', {
          x: touch.clientX,
          y: touch.clientY
        })
        this.vibrate('heavy')
      }

      this.tapCount = 0
    }, handlers.options.doubleTapDelay + 50)
  }

  getSwipeDirection(angle) {
    if (angle >= -45 && angle <= 45) return 'right'
    if (angle >= 45 && angle <= 135) return 'down'
    if (angle >= -135 && angle <= -45) return 'up'
    return 'left'
  }

  getTouchDistance(touch1, touch2) {
    const dx = touch1.clientX - touch2.clientX
    const dy = touch1.clientY - touch2.clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  getTouchAngle(touch1, touch2) {
    return Math.atan2(touch2.clientY - touch1.clientY, touch2.clientX - touch1.clientX) * 180 / Math.PI
  }

  getTouchCenter(touch1, touch2) {
    return {
      x: (touch1.clientX + touch2.clientX) / 2,
      y: (touch1.clientY + touch2.clientY) / 2
    }
  }

  triggerGesture(gestureId, type, data) {
    const handlers = this.gestureHandlers.get(gestureId)
    if (!handlers) return

    const gestureEvent = {
      type,
      gestureId,
      data,
      timestamp: Date.now(),
      element: handlers.element
    }

    // Trigger custom event on element
    const customEvent = new CustomEvent('gesture', {
      detail: gestureEvent,
      bubbles: true
    })
    handlers.element.dispatchEvent(customEvent)

    // Call global gesture handler if registered
    const globalHandler = this.gestureHandlers.get('global')
    if (globalHandler && globalHandler.callback) {
      globalHandler.callback(gestureEvent)
    }
  }

  // Haptic feedback methods
  vibrate(pattern) {
    if (!this.hapticSupported) return

    let vibrationPattern

    switch (pattern) {
      case 'light':
        vibrationPattern = [10]
        break
      case 'medium':
        vibrationPattern = [20]
        break
      case 'heavy':
        vibrationPattern = [50]
        break
      case 'double':
        vibrationPattern = [10, 10, 10]
        break
      case 'success':
        vibrationPattern = [20, 10, 20]
        break
      case 'error':
        vibrationPattern = [50, 10, 50, 10, 50]
        break
      default:
        vibrationPattern = pattern
    }

    // Try different haptic APIs
    if (navigator.vibrate) {
      navigator.vibrate(vibrationPattern)
    } else if (window.TapticEngine) {
      // iOS Taptic Engine
      switch (pattern) {
        case 'light':
          window.TapticEngine.impact({ style: 'light' })
          break
        case 'medium':
          window.TapticEngine.impact({ style: 'medium' })
          break
        case 'heavy':
          window.TapticEngine.impact({ style: 'heavy' })
          break
        case 'success':
          window.TapticEngine.notification({ type: 'success' })
          break
        case 'error':
          window.TapticEngine.notification({ type: 'error' })
          break
      }
    }
  }

  // Register global gesture handler
  onGesture(callback) {
    this.gestureHandlers.set('global', { callback })
  }

  // Predefined gesture combinations for common UI patterns
  addSwipeNavigation(element, callbacks = {}) {
    const gestureId = this.addGestureSupport(element, {
      enableSwipe: true,
      swipeThreshold: 30
    })

    const handler = (event) => {
      const { type, data } = event.detail

      if (type === 'swipe') {
        switch (data.direction) {
          case 'left':
            if (callbacks.onSwipeLeft) callbacks.onSwipeLeft(data)
            break
          case 'right':
            if (callbacks.onSwipeRight) callbacks.onSwipeRight(data)
            break
          case 'up':
            if (callbacks.onSwipeUp) callbacks.onSwipeUp(data)
            break
          case 'down':
            if (callbacks.onSwipeDown) callbacks.onSwipeDown(data)
            break
        }
      }
    }

    element.addEventListener('gesture', handler)
    return gestureId
  }

  addPinchToZoom(element, callbacks = {}) {
    const gestureId = this.addGestureSupport(element, {
      enablePinch: true
    })

    const handler = (event) => {
      const { type, data } = event.detail

      if (type === 'pinch') {
        if (data.scale > 1 && callbacks.onZoomIn) {
          callbacks.onZoomIn(data)
        } else if (data.scale < 1 && callbacks.onZoomOut) {
          callbacks.onZoomOut(data)
        }

        if (callbacks.onPinch) {
          callbacks.onPinch(data)
        }
      }
    }

    element.addEventListener('gesture', handler)
    return gestureId
  }

  addTapActions(element, callbacks = {}) {
    const gestureId = this.addGestureSupport(element, {
      enableDoubleTap: true,
      enableTripleTap: true
    })

    const handler = (event) => {
      const { type, data } = event.detail

      switch (type) {
        case 'tap':
          if (callbacks.onTap) callbacks.onTap(data)
          break
        case 'doubleTap':
          if (callbacks.onDoubleTap) callbacks.onDoubleTap(data)
          break
        case 'tripleTap':
          if (callbacks.onTripleTap) callbacks.onTripleTap(data)
          break
        case 'longPress':
          if (callbacks.onLongPress) callbacks.onLongPress(data)
          break
      }
    }

    element.addEventListener('gesture', handler)
    return gestureId
  }

  // Device-specific optimizations
  detectDeviceCapabilities() {
    return {
      touch: 'ontouchstart' in window,
      multiTouch: navigator.maxTouchPoints > 1,
      haptic: this.hapticSupported,
      deviceType: this.getDeviceType(),
      screenSize: {
        width: window.screen.width,
        height: window.screen.height
      }
    }
  }

  getDeviceType() {
    const ua = navigator.userAgent
    const screenWidth = window.screen.width

    if (ua.includes('Tablet') || (screenWidth >= 768 && screenWidth < 1024)) {
      return 'tablet'
    } else if (ua.includes('Mobile') || screenWidth < 768) {
      return 'mobile'
    } else {
      return 'desktop'
    }
  }

  // Cleanup method
  destroy() {
    for (const [gestureId, handlers] of this.gestureHandlers) {
      if (gestureId !== 'global') {
        this.removeGestureSupport(gestureId)
      }
    }
    this.gestureHandlers.clear()
  }
}

// Create singleton instance
const touchController = new TouchGestureController()

export default touchController
export { TouchGestureController }