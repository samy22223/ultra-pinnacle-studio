const CACHE_NAME = 'ultra-pinnacle-v3'
const STATIC_CACHE = 'ultra-pinnacle-static-v3'
const DYNAMIC_CACHE = 'ultra-pinnacle-dynamic-v3'
const API_CACHE = 'ultra-pinnacle-api-v3'
const IMAGE_CACHE = 'ultra-pinnacle-images-v3'

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/sw.js',
  '/static/js/bundle.js',
  '/static/css/main.css'
]

// Additional assets to cache for offline use
const OFFLINE_ASSETS = [
  '/offline.html',
  '/static/media/logo.svg',
  '/static/media/favicon.ico'
]

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker installing')
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(cache => {
        console.log('Caching static assets')
        return cache.addAll(STATIC_ASSETS.concat(OFFLINE_ASSETS))
      }),
      // Pre-cache critical API endpoints
      caches.open(API_CACHE).then(cache => {
        return cache.addAll([
          '/api/health',
          '/api/models',
          '/api/encyclopedia/list'
        ].map(url => new Request(url, { mode: 'no-cors' })))
      })
    ]).then(() => self.skipWaiting())
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating')
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('Deleting old cache:', cacheName)
            return caches.delete(cacheName)
          }
        })
      )
    }).then(() => self.clients.claim())
  )
})

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') return

  // Handle API requests differently
  if (url.pathname.startsWith('/api/') || url.hostname !== location.hostname) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful API responses
          if (response.status === 200) {
            const responseClone = response.clone()
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(request, responseClone))
          }
          return response
        })
        .catch(() => {
          // Return cached API response if available
          return caches.match(request)
        })
    )
    return
  }

  // Handle static assets and pages
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response
        }

        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response
            }

            const responseClone = response.clone()
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(request, responseClone))

            return response
          })
          .catch(() => {
            // Return offline fallback for navigation requests
            if (request.mode === 'navigate') {
              return caches.match('/')
            }
          })
      })
  )
})

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('Background sync triggered:', event.tag)

  if (event.tag === 'background-sync-canvas') {
    event.waitUntil(syncCanvasProjects())
  }
})

async function syncCanvasProjects() {
  try {
    // Get all clients and send sync message
    const clients = await self.clients.matchAll()
    clients.forEach(client => {
      client.postMessage({
        type: 'SYNC_CANVAS_PROJECTS'
      })
    })
  } catch (error) {
    console.error('Background sync failed:', error)
  }
}

async function syncPendingAPIRequests() {
  try {
    // Get pending requests from IndexedDB
    const pendingRequests = await getPendingRequests()

    for (const request of pendingRequests) {
      try {
        const response = await fetch(request.url, request.options)
        if (response.ok) {
          await removePendingRequest(request.id)
          console.log('Synced pending request:', request.id)
        }
      } catch (error) {
        console.error('Failed to sync request:', request.id, error)
      }
    }
  } catch (error) {
    console.error('API sync failed:', error)
  }
}

async function updateCache() {
  try {
    const cache = await caches.open(STATIC_CACHE)
    // Update critical assets
    await cache.addAll([
      '/api/health',
      '/api/models'
    ].map(url => new Request(url, { mode: 'no-cors' })))
    console.log('Cache updated successfully')
  } catch (error) {
    console.error('Cache update failed:', error)
  }
}

async function cleanupOldCache() {
  try {
    const cacheNames = await caches.keys()
    const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE, IMAGE_CACHE]

    for (const cacheName of cacheNames) {
      if (!validCaches.includes(cacheName)) {
        await caches.delete(cacheName)
        console.log('Deleted old cache:', cacheName)
      }
    }
  } catch (error) {
    console.error('Cache cleanup failed:', error)
  }
}

// IndexedDB helpers for offline requests
async function getPendingRequests() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('UltraPinnacleOffline', 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const transaction = db.transaction(['pendingRequests'], 'readonly')
      const store = transaction.objectStore('pendingRequests')
      const getAllRequest = store.getAll()

      getAllRequest.onsuccess = () => resolve(getAllRequest.result)
      getAllRequest.onerror = () => reject(getAllRequest.error)
    }

    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains('pendingRequests')) {
        db.createObjectStore('pendingRequests', { keyPath: 'id', autoIncrement: true })
      }
    }
  })
}

async function removePendingRequest(id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('UltraPinnacleOffline', 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const transaction = db.transaction(['pendingRequests'], 'readwrite')
      const store = transaction.objectStore('pendingRequests')
      const deleteRequest = store.delete(id)

      deleteRequest.onsuccess = () => resolve()
      deleteRequest.onerror = () => reject(deleteRequest.error)
    }
  })
}

// Push notification event
self.addEventListener('push', event => {
  console.log('Push message received:', event)

  let notificationData = {}

  if (event.data) {
    notificationData = event.data.json()
  }

  const options = {
    body: notificationData.body || 'New notification from Ultra Pinnacle Studio',
    icon: '/icon-192.png',
    badge: '/icon-96.png',
    vibrate: [100, 50, 100],
    data: notificationData.data || {},
    actions: notificationData.actions || [
      {
        action: 'view',
        title: 'View',
        icon: '/icon-96.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ],
    requireInteraction: notificationData.requireInteraction || false,
    silent: notificationData.silent || false,
    tag: notificationData.tag || 'default'
  }

  event.waitUntil(
    self.registration.showNotification(
      notificationData.title || 'Ultra Pinnacle Studio',
      options
    )
  )
})

// Notification click event
self.addEventListener('notificationclick', event => {
  console.log('Notification click received:', event)

  event.notification.close()

  const action = event.action
  const notificationData = event.notification.data

  if (action === 'dismiss') {
    return
  }

  // Default action or 'view' action
  const urlToOpen = notificationData.url || '/'

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Check if there is already a window/tab open with the target URL
        for (let client of windowClients) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus()
          }
        }

        // If not, open a new window/tab with the target URL
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen)
        }
      })
  )
})

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('Background sync triggered:', event.tag)

  if (event.tag === 'background-sync-canvas') {
    event.waitUntil(syncCanvasProjects())
  } else if (event.tag === 'background-sync-api') {
    event.waitUntil(syncPendingAPIRequests())
  }
})

// Periodic background sync for maintenance
self.addEventListener('periodicsync', event => {
  console.log('Periodic sync triggered:', event.tag)

  if (event.tag === 'update-cache') {
    event.waitUntil(updateCache())
  } else if (event.tag === 'cleanup-cache') {
    event.waitUntil(cleanupOldCache())
  }
})

// Message handling
self.addEventListener('message', event => {
  const { type, data } = event.data

  if (type === 'SKIP_WAITING') {
    self.skipWaiting()
  } else if (type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: '3.0.0' })
  } else if (type === 'UPDATE_CACHE') {
    event.waitUntil(updateCache())
  }
})