// Browser Extension API Bridge
// Provides a unified interface for communicating with browser extensions

class ExtensionBridge {
  constructor() {
    this.extensions = new Map()
    this.messageHandlers = new Map()
    this.initialized = false
    this.browserAPI = this.detectBrowserAPI()
  }

  detectBrowserAPI() {
    // Detect available browser extension APIs
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      return 'chrome'
    } else if (typeof browser !== 'undefined' && browser.runtime) {
      return 'firefox'
    } else if (typeof safari !== 'undefined' && safari.extension) {
      return 'safari'
    }
    return null
  }

  async initialize() {
    if (this.initialized) return true

    try {
      // Initialize browser-specific APIs
      await this.initializeBrowserAPI()

      // Register built-in extensions
      await this.registerBuiltInExtensions()

      // Set up message listeners
      this.setupMessageListeners()

      this.initialized = true
      console.log('Extension bridge initialized for:', this.browserAPI)
      return true
    } catch (error) {
      console.error('Failed to initialize extension bridge:', error)
      return false
    }
  }

  async initializeBrowserAPI() {
    switch (this.browserAPI) {
      case 'chrome':
        // Chrome extension API initialization
        if (chrome.runtime && chrome.runtime.connect) {
          this.port = chrome.runtime.connect({ name: 'ultra-pinnacle-bridge' })
        }
        break

      case 'firefox':
        // Firefox WebExtension API initialization
        if (browser.runtime && browser.runtime.connect) {
          this.port = browser.runtime.connect({ name: 'ultra-pinnacle-bridge' })
        }
        break

      case 'safari':
        // Safari extension API initialization
        // Note: Safari extensions have different APIs
        break
    }
  }

  async registerBuiltInExtensions() {
    const builtInExtensions = [
      {
        id: 'google-docs',
        name: 'Google Docs',
        type: 'productivity',
        api: new GoogleDocsExtension()
      },
      {
        id: 'google-sheets',
        name: 'Google Sheets',
        type: 'productivity',
        api: new GoogleSheetsExtension()
      },
      {
        id: 'google-drive',
        name: 'Google Drive',
        type: 'storage',
        api: new GoogleDriveExtension()
      },
      {
        id: 'google-calendar',
        name: 'Google Calendar',
        type: 'productivity',
        api: new GoogleCalendarExtension()
      },
      {
        id: 'grammarly',
        name: 'Grammarly',
        type: 'writing',
        api: new GrammarlyExtension()
      },
      {
        id: 'evernote',
        name: 'Evernote Web Clipper',
        type: 'productivity',
        api: new EvernoteExtension()
      },
      {
        id: 'todoist',
        name: 'Todoist',
        type: 'productivity',
        api: new TodoistExtension()
      },
      {
        id: 'react-devtools',
        name: 'React DevTools',
        type: 'developer',
        api: new ReactDevToolsExtension()
      },
      {
        id: 'lighthouse',
        name: 'Lighthouse',
        type: 'developer',
        api: new LighthouseExtension()
      },
      {
        id: 'axe-devtools',
        name: 'axe DevTools',
        type: 'accessibility',
        api: new AxeDevToolsExtension()
      },
      {
        id: 'ublock-origin',
        name: 'uBlock Origin',
        type: 'privacy',
        api: new UBlockOriginExtension()
      }
    ]

    for (const ext of builtInExtensions) {
      await this.registerExtension(ext.id, ext.api)
    }
  }

  setupMessageListeners() {
    // Set up listeners for different browser APIs
    if (this.port) {
      this.port.onMessage.addListener((message) => {
        this.handleIncomingMessage(message)
      })
    }

    // Fallback for content script communication
    window.addEventListener('message', (event) => {
      if (event.source !== window) return

      if (event.data.type && event.data.type.startsWith('EXTENSION_')) {
        this.handleIncomingMessage(event.data)
      }
    })
  }

  async registerExtension(id, api) {
    try {
      this.extensions.set(id, api)

      // Initialize the extension if it has an init method
      if (api.initialize) {
        await api.initialize()
      }

      console.log(`Extension registered: ${id}`)
      return true
    } catch (error) {
      console.error(`Failed to register extension ${id}:`, error)
      return false
    }
  }

  async sendMessage(extensionId, message) {
    const extension = this.extensions.get(extensionId)
    if (!extension) {
      throw new Error(`Extension ${extensionId} not found`)
    }

    try {
      // Try direct API call first
      if (extension.sendMessage) {
        return await extension.sendMessage(message)
      }

      // Fallback to browser-specific messaging
      return await this.sendBrowserMessage(extensionId, message)
    } catch (error) {
      console.error(`Failed to send message to ${extensionId}:`, error)
      throw error
    }
  }

  async sendBrowserMessage(extensionId, message) {
    const fullMessage = {
      type: 'FROM_ULTRA_PINNACLE',
      extensionId,
      data: message,
      timestamp: Date.now()
    }

    switch (this.browserAPI) {
      case 'chrome':
        return new Promise((resolve, reject) => {
          chrome.runtime.sendMessage(fullMessage, (response) => {
            if (chrome.runtime.lastError) {
              reject(chrome.runtime.lastError)
            } else {
              resolve(response)
            }
          })
        })

      case 'firefox':
        return browser.runtime.sendMessage(fullMessage)

      case 'safari':
        // Safari extension messaging
        return new Promise((resolve) => {
          window.postMessage(fullMessage, '*')
          resolve({ success: true })
        })

      default:
        // Fallback to window messaging
        window.postMessage(fullMessage, '*')
        return { success: true }
    }
  }

  handleIncomingMessage(message) {
    const { extensionId, type, data } = message

    if (type === 'EXTENSION_RESPONSE') {
      // Handle response to a sent message
      this.handleExtensionResponse(extensionId, data)
    } else if (type === 'EXTENSION_EVENT') {
      // Handle extension-initiated events
      this.handleExtensionEvent(extensionId, data)
    }
  }

  handleExtensionResponse(extensionId, data) {
    // Handle responses from extensions
    console.log(`Response from ${extensionId}:`, data)
  }

  handleExtensionEvent(extensionId, data) {
    // Handle events initiated by extensions
    const handlers = this.messageHandlers.get(extensionId) || []
    handlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        console.error(`Error in event handler for ${extensionId}:`, error)
      }
    })
  }

  onMessage(extensionId, handler) {
    if (!this.messageHandlers.has(extensionId)) {
      this.messageHandlers.set(extensionId, [])
    }
    this.messageHandlers.get(extensionId).push(handler)
  }

  offMessage(extensionId, handler) {
    const handlers = this.messageHandlers.get(extensionId) || []
    const index = handlers.indexOf(handler)
    if (index > -1) {
      handlers.splice(index, 1)
    }
  }

  getExtension(id) {
    return this.extensions.get(id)
  }

  getAllExtensions() {
    return Array.from(this.extensions.entries()).map(([id, api]) => ({
      id,
      name: api.name || id,
      type: api.type || 'unknown',
      version: api.version || '1.0.0',
      enabled: api.enabled !== false
    }))
  }

  async checkExtensionCompatibility(extensionId) {
    const extension = this.extensions.get(extensionId)
    if (!extension) return false

    // Check if extension is compatible with current browser
    if (extension.supportedBrowsers) {
      return extension.supportedBrowsers.includes(this.browserAPI)
    }

    return true // Assume compatible if not specified
  }

  async enableExtension(extensionId) {
    const extension = this.extensions.get(extensionId)
    if (!extension) return false

    try {
      if (extension.enable) {
        await extension.enable()
      }
      extension.enabled = true
      return true
    } catch (error) {
      console.error(`Failed to enable extension ${extensionId}:`, error)
      return false
    }
  }

  async disableExtension(extensionId) {
    const extension = this.extensions.get(extensionId)
    if (!extension) return false

    try {
      if (extension.disable) {
        await extension.disable()
      }
      extension.enabled = false
      return true
    } catch (error) {
      console.error(`Failed to disable extension ${extensionId}:`, error)
      return false
    }
  }
}

// Extension base class
class BaseExtension {
  constructor(config = {}) {
    this.name = config.name || 'Unknown Extension'
    this.version = config.version || '1.0.0'
    this.type = config.type || 'unknown'
    this.enabled = config.enabled !== false
    this.supportedBrowsers = config.supportedBrowsers || ['chrome', 'firefox', 'safari', 'edge']
  }

  async initialize() {
    // Override in subclasses
    return true
  }

  async sendMessage(message) {
    // Override in subclasses
    throw new Error('sendMessage not implemented')
  }

  async enable() {
    this.enabled = true
  }

  async disable() {
    this.enabled = false
  }
}

// Google Workspace API integrations
class GoogleDocsExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Google Docs',
      type: 'productivity',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.apiKey = null
    this.clientId = null
    this.isAuthenticated = false
  }

  async initialize() {
    // Load Google APIs
    await this.loadGoogleAPIs()
    return true
  }

  async loadGoogleAPIs() {
    return new Promise((resolve, reject) => {
      // Load Google API script
      const script = document.createElement('script')
      script.src = 'https://apis.google.com/js/api.js'
      script.onload = () => {
        // Initialize Google API client
        window.gapi.load('auth2', () => {
          window.gapi.auth2.init({
            client_id: this.clientId || 'your-google-client-id.apps.googleusercontent.com'
          }).then(() => {
            console.log('Google API initialized')
            resolve()
          }).catch(reject)
        })
      }
      script.onerror = reject
      document.head.appendChild(script)
    })
  }

  async authenticate() {
    try {
      const authInstance = window.gapi.auth2.getAuthInstance()
      await authInstance.signIn()
      this.isAuthenticated = true
      return { success: true, user: authInstance.currentUser.get() }
    } catch (error) {
      console.error('Google authentication failed:', error)
      return { success: false, error: error.message }
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Google' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate()

      case 'createDocument':
        return await this.createDocument(data)

      case 'getDocument':
        return await this.getDocument(data.id)

      case 'updateDocument':
        return await this.updateDocument(data.id, data.updates)

      case 'listDocuments':
        return await this.listDocuments(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async createDocument(data) {
    try {
      const response = await window.gapi.client.docs.documents.create({
        title: data.title || 'New Document'
      })
      return { success: true, document: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getDocument(documentId) {
    try {
      const response = await window.gapi.client.docs.documents.get({
        documentId
      })
      return { success: true, document: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async updateDocument(documentId, updates) {
    try {
      const requests = updates.map(update => ({
        insertText: {
          location: { index: update.index || 1 },
          text: update.text
        }
      }))

      const response = await window.gapi.client.docs.documents.batchUpdate({
        documentId,
        requests
      })
      return { success: true, result: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async listDocuments(options = {}) {
    try {
      // Note: This would typically use Google Drive API
      const response = await window.gapi.client.drive.files.list({
        q: "mimeType='application/vnd.google-apps.document'",
        orderBy: 'modifiedTime desc',
        pageSize: options.limit || 10
      })
      return { success: true, documents: response.result.files }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class GoogleSheetsExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Google Sheets',
      type: 'productivity',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isAuthenticated = false
  }

  async initialize() {
    // Google APIs are loaded by GoogleDocsExtension
    return true
  }

  async authenticate() {
    try {
      const authInstance = window.gapi.auth2.getAuthInstance()
      await authInstance.signIn()
      this.isAuthenticated = true
      return { success: true, user: authInstance.currentUser.get() }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Google' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate()

      case 'createSpreadsheet':
        return await this.createSpreadsheet(data)

      case 'getSpreadsheet':
        return await this.getSpreadsheet(data.id)

      case 'updateCells':
        return await this.updateCells(data.id, data.range, data.values)

      case 'getValues':
        return await this.getValues(data.id, data.range)

      case 'appendValues':
        return await this.appendValues(data.id, data.range, data.values)

      case 'listSpreadsheets':
        return await this.listSpreadsheets(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async createSpreadsheet(data) {
    try {
      const response = await window.gapi.client.sheets.spreadsheets.create({
        properties: {
          title: data.title || 'New Spreadsheet'
        }
      })
      return { success: true, spreadsheet: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getSpreadsheet(spreadsheetId) {
    try {
      const response = await window.gapi.client.sheets.spreadsheets.get({
        spreadsheetId
      })
      return { success: true, spreadsheet: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async updateCells(spreadsheetId, range, values) {
    try {
      const response = await window.gapi.client.sheets.spreadsheets.values.update({
        spreadsheetId,
        range,
        valueInputOption: 'RAW',
        resource: { values }
      })
      return { success: true, result: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getValues(spreadsheetId, range) {
    try {
      const response = await window.gapi.client.sheets.spreadsheets.values.get({
        spreadsheetId,
        range
      })
      return { success: true, values: response.result.values }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async appendValues(spreadsheetId, range, values) {
    try {
      const response = await window.gapi.client.sheets.spreadsheets.values.append({
        spreadsheetId,
        range,
        valueInputOption: 'RAW',
        insertDataOption: 'INSERT_ROWS',
        resource: { values }
      })
      return { success: true, result: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async listSpreadsheets(options = {}) {
    try {
      const response = await window.gapi.client.drive.files.list({
        q: "mimeType='application/vnd.google-apps.spreadsheet'",
        orderBy: 'modifiedTime desc',
        pageSize: options.limit || 10
      })
      return { success: true, spreadsheets: response.result.files }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class GoogleDriveExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Google Drive',
      type: 'storage',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isAuthenticated = false
  }

  async initialize() {
    return true
  }

  async authenticate() {
    try {
      const authInstance = window.gapi.auth2.getAuthInstance()
      await authInstance.signIn()
      this.isAuthenticated = true
      return { success: true, user: authInstance.currentUser.get() }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Google' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate()

      case 'uploadFile':
        return await this.uploadFile(data)

      case 'downloadFile':
        return await this.downloadFile(data.fileId)

      case 'listFiles':
        return await this.listFiles(data)

      case 'createFolder':
        return await this.createFolder(data)

      case 'deleteFile':
        return await this.deleteFile(data.fileId)

      case 'getFileMetadata':
        return await this.getFileMetadata(data.fileId)

      case 'shareFile':
        return await this.shareFile(data.fileId, data.permissions)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async uploadFile(data) {
    try {
      const boundary = '-------314159265358979323846'
      const delimiter = "\r\n--" + boundary + "\r\n"
      const close_delim = "\r\n--" + boundary + "--"

      const contentType = data.contentType || 'application/octet-stream'
      const metadata = {
        name: data.name,
        mimeType: contentType,
        parents: data.parentId ? [data.parentId] : undefined
      }

      const multipartRequestBody =
        delimiter +
        'Content-Type: application/json\r\n\r\n' +
        JSON.stringify(metadata) +
        delimiter +
        'Content-Type: ' + contentType + '\r\n\r\n' +
        data.content +
        close_delim

      const request = window.gapi.client.request({
        path: '/upload/drive/v3/files',
        method: 'POST',
        params: { uploadType: 'multipart' },
        headers: { 'Content-Type': 'multipart/related; boundary="' + boundary + '"' },
        body: multipartRequestBody
      })

      const response = await request
      return { success: true, file: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async downloadFile(fileId) {
    try {
      const response = await window.gapi.client.drive.files.get({
        fileId,
        alt: 'media'
      })
      return { success: true, content: response.body, metadata: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async listFiles(options = {}) {
    try {
      const query = options.folderId
        ? `'${options.folderId}' in parents`
        : undefined

      const response = await window.gapi.client.drive.files.list({
        q: query,
        orderBy: options.orderBy || 'modifiedTime desc',
        pageSize: options.limit || 50,
        fields: 'files(id,name,mimeType,modifiedTime,size,parents)'
      })
      return { success: true, files: response.result.files }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createFolder(data) {
    try {
      const response = await window.gapi.client.drive.files.create({
        resource: {
          name: data.name,
          mimeType: 'application/vnd.google-apps.folder',
          parents: data.parentId ? [data.parentId] : undefined
        }
      })
      return { success: true, folder: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async deleteFile(fileId) {
    try {
      await window.gapi.client.drive.files.delete({
        fileId
      })
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getFileMetadata(fileId) {
    try {
      const response = await window.gapi.client.drive.files.get({
        fileId,
        fields: 'id,name,mimeType,modifiedTime,size,parents,webViewLink,downloadUrl'
      })
      return { success: true, metadata: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async shareFile(fileId, permissions) {
    try {
      const response = await window.gapi.client.drive.permissions.create({
        fileId,
        resource: {
          type: permissions.type || 'anyone',
          role: permissions.role || 'reader'
        }
      })
      return { success: true, permission: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class GoogleCalendarExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Google Calendar',
      type: 'productivity',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isAuthenticated = false
  }

  async initialize() {
    return true
  }

  async authenticate() {
    try {
      const authInstance = window.gapi.auth2.getAuthInstance()
      await authInstance.signIn()
      this.isAuthenticated = true
      return { success: true, user: authInstance.currentUser.get() }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Google' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate()

      case 'listCalendars':
        return await this.listCalendars()

      case 'createEvent':
        return await this.createEvent(data)

      case 'getEvent':
        return await this.getEvent(data.eventId, data.calendarId)

      case 'updateEvent':
        return await this.updateEvent(data.eventId, data.calendarId, data.updates)

      case 'deleteEvent':
        return await this.deleteEvent(data.eventId, data.calendarId)

      case 'listEvents':
        return await this.listEvents(data.calendarId, data.options)

      case 'createCalendar':
        return await this.createCalendar(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async listCalendars() {
    try {
      const response = await window.gapi.client.calendar.calendarList.list()
      return { success: true, calendars: response.result.items }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createEvent(data) {
    try {
      const event = {
        summary: data.summary,
        description: data.description,
        start: {
          dateTime: data.startTime,
          timeZone: data.timeZone || 'UTC'
        },
        end: {
          dateTime: data.endTime,
          timeZone: data.timeZone || 'UTC'
        },
        attendees: data.attendees || [],
        location: data.location,
        reminders: {
          useDefault: true
        }
      }

      const response = await window.gapi.client.calendar.events.insert({
        calendarId: data.calendarId || 'primary',
        resource: event
      })
      return { success: true, event: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getEvent(eventId, calendarId = 'primary') {
    try {
      const response = await window.gapi.client.calendar.events.get({
        calendarId,
        eventId
      })
      return { success: true, event: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async updateEvent(eventId, calendarId = 'primary', updates) {
    try {
      const response = await window.gapi.client.calendar.events.patch({
        calendarId,
        eventId,
        resource: updates
      })
      return { success: true, event: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async deleteEvent(eventId, calendarId = 'primary') {
    try {
      await window.gapi.client.calendar.events.delete({
        calendarId,
        eventId
      })
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async listEvents(calendarId = 'primary', options = {}) {
    try {
      const params = {
        calendarId,
        timeMin: options.timeMin || new Date().toISOString(),
        maxResults: options.maxResults || 10,
        singleEvents: true,
        orderBy: 'startTime'
      }

      if (options.timeMax) params.timeMax = options.timeMax
      if (options.q) params.q = options.q

      const response = await window.gapi.client.calendar.events.list(params)
      return { success: true, events: response.result.items }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createCalendar(data) {
    try {
      const calendar = {
        summary: data.summary,
        description: data.description,
        timeZone: data.timeZone || 'UTC'
      }

      const response = await window.gapi.client.calendar.calendars.insert({
        resource: calendar
      })
      return { success: true, calendar: response.result }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class GrammarlyExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Grammarly',
      type: 'writing',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isInitialized = false
  }

  async initialize() {
    // Load Grammarly SDK if available
    if (window.Grammarly) {
      this.isInitialized = true
    } else {
      // Try to load Grammarly script
      try {
        await this.loadGrammarlySDK()
        this.isInitialized = true
      } catch (error) {
        console.warn('Grammarly SDK not available:', error)
      }
    }
    return true
  }

  async loadGrammarlySDK() {
    return new Promise((resolve, reject) => {
      // Grammarly typically injects its own script
      // This is a placeholder for actual SDK loading
      setTimeout(() => {
        if (window.Grammarly) {
          resolve()
        } else {
          reject(new Error('Grammarly SDK not loaded'))
        }
      }, 1000)
    })
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isInitialized) {
      return { success: false, error: 'Grammarly not initialized' }
    }

    switch (action) {
      case 'checkText':
        return await this.checkText(data.text)

      case 'getSuggestions':
        return await this.getSuggestions(data.text)

      case 'setTone':
        return await this.setTone(data.tone)

      case 'getStats':
        return await this.getStats(data.text)

      case 'addToDictionary':
        return await this.addToDictionary(data.word)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async checkText(text) {
    try {
      // Simulate Grammarly API call
      const suggestions = await this.analyzeText(text)
      return {
        success: true,
        suggestions,
        score: this.calculateScore(suggestions)
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async analyzeText(text) {
    // Placeholder for actual Grammarly analysis
    const suggestions = []

    // Basic grammar checks (simplified)
    if (text.includes('teh ')) {
      suggestions.push({
        type: 'spelling',
        original: 'teh',
        suggestion: 'the',
        offset: text.indexOf('teh'),
        length: 3
      })
    }

    if (text.split(' ').length > 20 && !text.includes('.')) {
      suggestions.push({
        type: 'grammar',
        message: 'Consider adding punctuation',
        offset: text.length - 10,
        length: 10
      })
    }

    return suggestions
  }

  calculateScore(suggestions) {
    const baseScore = 100
    const penalties = {
      spelling: 5,
      grammar: 10,
      style: 3
    }

    return Math.max(0, baseScore - suggestions.reduce((total, suggestion) => {
      return total + (penalties[suggestion.type] || 1)
    }, 0))
  }

  async getSuggestions(text) {
    const result = await this.checkText(text)
    return result
  }

  async setTone(tone) {
    // Placeholder for tone setting
    console.log('Setting Grammarly tone to:', tone)
    return { success: true, tone }
  }

  async getStats(text) {
    const words = text.split(/\s+/).length
    const characters = text.length
    const sentences = text.split(/[.!?]+/).length - 1
    const readingTime = Math.ceil(words / 200) // words per minute

    return {
      success: true,
      stats: {
        words,
        characters,
        sentences,
        readingTime: `${readingTime} min read`,
        readability: this.calculateReadability(text)
      }
    }
  }

  calculateReadability(text) {
    // Simplified readability score
    const words = text.split(/\s+/).length
    const sentences = text.split(/[.!?]+/).length
    const avgWordsPerSentence = words / sentences

    if (avgWordsPerSentence < 10) return 'Easy'
    if (avgWordsPerSentence < 20) return 'Medium'
    return 'Hard'
  }

  async addToDictionary(word) {
    // Placeholder for dictionary management
    console.log('Adding to Grammarly dictionary:', word)
    return { success: true, word }
  }
}

class EvernoteExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Evernote Web Clipper',
      type: 'productivity',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isAuthenticated = false
    this.apiKey = null
  }

  async initialize() {
    // Check if Evernote SDK is available
    if (window.Evernote) {
      this.isAuthenticated = true
    }
    return true
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Evernote' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate()

      case 'clipContent':
        return await this.clipContent(data)

      case 'createNote':
        return await this.createNote(data)

      case 'getNotes':
        return await this.getNotes(data)

      case 'searchNotes':
        return await this.searchNotes(data)

      case 'getNotebooks':
        return await this.getNotebooks()

      case 'createNotebook':
        return await this.createNotebook(data)

      case 'clipWebPage':
        return await this.clipWebPage(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async authenticate() {
    try {
      // Simplified authentication - in real implementation would use OAuth
      this.isAuthenticated = true
      return {
        success: true,
        user: {
          id: 'user123',
          name: 'Test User',
          email: 'user@example.com'
        }
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async clipContent(data) {
    try {
      const noteData = {
        title: data.title || 'Clipped Content',
        content: this.formatContent(data.content, data.type),
        tags: data.tags || [],
        notebook: data.notebook || 'default',
        created: new Date().toISOString()
      }

      const note = await this.createNote(noteData)
      return { success: true, note }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  formatContent(content, type) {
    switch (type) {
      case 'article':
        return this.formatArticle(content)
      case 'image':
        return this.formatImage(content)
      case 'video':
        return this.formatVideo(content)
      case 'text':
      default:
        return this.formatText(content)
    }
  }

  formatArticle(content) {
    return `
      <div class="evernote-article">
        <h1>${content.title || 'Untitled Article'}</h1>
        <div class="article-meta">
          <p>Source: ${content.url || 'Unknown'}</p>
          <p>Clipped: ${new Date().toLocaleDateString()}</p>
        </div>
        <div class="article-content">
          ${content.content || content.text || ''}
        </div>
      </div>
    `
  }

  formatImage(content) {
    return `
      <div class="evernote-image">
        <h2>${content.title || 'Clipped Image'}</h2>
        <img src="${content.src}" alt="${content.alt || 'Clipped image'}" />
        <p>Source: ${content.url || 'Unknown'}</p>
      </div>
    `
  }

  formatVideo(content) {
    return `
      <div class="evernote-video">
        <h2>${content.title || 'Clipped Video'}</h2>
        <p>Video URL: ${content.url}</p>
        <p>Duration: ${content.duration || 'Unknown'}</p>
        <p>Description: ${content.description || ''}</p>
      </div>
    `
  }

  formatText(content) {
    return `
      <div class="evernote-text">
        <pre>${content.text || content}</pre>
        <p>Source: ${content.url || 'Unknown'}</p>
      </div>
    `
  }

  async createNote(data) {
    try {
      // Simulate API call to Evernote
      const note = {
        id: 'note_' + Date.now(),
        title: data.title,
        content: data.content,
        tags: data.tags || [],
        notebook: data.notebook || 'default',
        created: data.created || new Date().toISOString(),
        updated: new Date().toISOString()
      }

      // Store in localStorage for demo (would be API call in real implementation)
      const notes = JSON.parse(localStorage.getItem('evernote_notes') || '[]')
      notes.push(note)
      localStorage.setItem('evernote_notes', JSON.stringify(notes))

      return { success: true, note }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getNotes(options = {}) {
    try {
      const notes = JSON.parse(localStorage.getItem('evernote_notes') || '[]')
      const filtered = notes.filter(note => {
        if (options.notebook && note.notebook !== options.notebook) return false
        if (options.tag && !note.tags.includes(options.tag)) return false
        return true
      })

      const sorted = filtered.sort((a, b) =>
        new Date(b.updated) - new Date(a.updated)
      )

      return {
        success: true,
        notes: sorted.slice(0, options.limit || 50)
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async searchNotes(query) {
    try {
      const notes = JSON.parse(localStorage.getItem('evernote_notes') || '[]')
      const results = notes.filter(note =>
        note.title.toLowerCase().includes(query.toLowerCase()) ||
        note.content.toLowerCase().includes(query.toLowerCase()) ||
        note.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
      )

      return { success: true, results }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getNotebooks() {
    try {
      const notebooks = JSON.parse(localStorage.getItem('evernote_notebooks') || '["default"]')
      return { success: true, notebooks }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createNotebook(data) {
    try {
      const notebooks = JSON.parse(localStorage.getItem('evernote_notebooks') || '["default"]')
      if (!notebooks.includes(data.name)) {
        notebooks.push(data.name)
        localStorage.setItem('evernote_notebooks', JSON.stringify(notebooks))
      }
      return { success: true, notebook: data.name }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async clipWebPage(data) {
    try {
      // Get current page content
      const pageData = {
        title: document.title,
        url: window.location.href,
        content: document.body.innerHTML,
        type: 'article',
        tags: ['web-clip', 'auto-clip']
      }

      return await this.clipContent({ ...pageData, ...data })
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class TodoistExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Todoist',
      type: 'productivity',
      supportedBrowsers: ['chrome', 'firefox', 'safari', 'edge']
    })
    this.isAuthenticated = false
    this.apiToken = null
  }

  async initialize() {
    // Check for stored API token
    this.apiToken = localStorage.getItem('todoist_token')
    if (this.apiToken) {
      this.isAuthenticated = true
    }
    return true
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isAuthenticated && action !== 'authenticate') {
      return { success: false, error: 'Not authenticated with Todoist' }
    }

    switch (action) {
      case 'authenticate':
        return await this.authenticate(data)

      case 'getTasks':
        return await this.getTasks(data)

      case 'createTask':
        return await this.createTask(data)

      case 'updateTask':
        return await this.updateTask(data.id, data.updates)

      case 'completeTask':
        return await this.completeTask(data.id)

      case 'deleteTask':
        return await this.deleteTask(data.id)

      case 'getProjects':
        return await this.getProjects()

      case 'createProject':
        return await this.createProject(data)

      case 'getLabels':
        return await this.getLabels()

      case 'createLabel':
        return await this.createLabel(data)

      case 'getProductivityStats':
        return await this.getProductivityStats()

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async authenticate(credentials) {
    try {
      // In real implementation, this would validate with Todoist API
      if (credentials.token) {
        this.apiToken = credentials.token
        localStorage.setItem('todoist_token', this.apiToken)
        this.isAuthenticated = true
        return { success: true }
      }
      return { success: false, error: 'Invalid credentials' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getTasks(filters = {}) {
    try {
      // Simulate API call - in real implementation would use Todoist REST API
      const tasks = JSON.parse(localStorage.getItem('todoist_tasks') || '[]')

      let filteredTasks = tasks

      if (filters.project) {
        filteredTasks = filteredTasks.filter(task => task.project_id === filters.project)
      }

      if (filters.completed !== undefined) {
        filteredTasks = filteredTasks.filter(task => task.completed === filters.completed)
      }

      if (filters.due_date) {
        filteredTasks = filteredTasks.filter(task => task.due?.date === filters.due_date)
      }

      // Sort by priority and due date
      filteredTasks.sort((a, b) => {
        if (a.priority !== b.priority) return b.priority - a.priority
        if (a.due?.date && b.due?.date) {
          return new Date(a.due.date) - new Date(b.due.date)
        }
        return 0
      })

      return {
        success: true,
        tasks: filteredTasks.slice(0, filters.limit || 100)
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createTask(taskData) {
    try {
      const task = {
        id: 'task_' + Date.now(),
        content: taskData.content,
        description: taskData.description || '',
        project_id: taskData.project_id || 'inbox',
        labels: taskData.labels || [],
        priority: taskData.priority || 1,
        due: taskData.due ? {
          date: taskData.due,
          string: taskData.due_string || taskData.due,
          lang: 'en'
        } : null,
        completed: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      const tasks = JSON.parse(localStorage.getItem('todoist_tasks') || '[]')
      tasks.push(task)
      localStorage.setItem('todoist_tasks', JSON.stringify(tasks))

      return { success: true, task }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async updateTask(taskId, updates) {
    try {
      const tasks = JSON.parse(localStorage.getItem('todoist_tasks') || '[]')
      const taskIndex = tasks.findIndex(task => task.id === taskId)

      if (taskIndex === -1) {
        return { success: false, error: 'Task not found' }
      }

      tasks[taskIndex] = {
        ...tasks[taskIndex],
        ...updates,
        updated_at: new Date().toISOString()
      }

      localStorage.setItem('todoist_tasks', JSON.stringify(tasks))
      return { success: true, task: tasks[taskIndex] }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async completeTask(taskId) {
    return await this.updateTask(taskId, { completed: true })
  }

  async deleteTask(taskId) {
    try {
      const tasks = JSON.parse(localStorage.getItem('todoist_tasks') || '[]')
      const filteredTasks = tasks.filter(task => task.id !== taskId)

      if (filteredTasks.length === tasks.length) {
        return { success: false, error: 'Task not found' }
      }

      localStorage.setItem('todoist_tasks', JSON.stringify(filteredTasks))
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getProjects() {
    try {
      const projects = JSON.parse(localStorage.getItem('todoist_projects') || '[{"id": "inbox", "name": "Inbox", "color": "grey"}]')
      return { success: true, projects }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createProject(projectData) {
    try {
      const projects = JSON.parse(localStorage.getItem('todoist_projects') || '[{"id": "inbox", "name": "Inbox", "color": "grey"}]')
      const project = {
        id: 'project_' + Date.now(),
        name: projectData.name,
        color: projectData.color || 'blue',
        created_at: new Date().toISOString()
      }

      projects.push(project)
      localStorage.setItem('todoist_projects', JSON.stringify(projects))

      return { success: true, project }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getLabels() {
    try {
      const labels = JSON.parse(localStorage.getItem('todoist_labels') || '[]')
      return { success: true, labels }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async createLabel(labelData) {
    try {
      const labels = JSON.parse(localStorage.getItem('todoist_labels') || '[]')
      const label = {
        id: 'label_' + Date.now(),
        name: labelData.name,
        color: labelData.color || 'blue'
      }

      labels.push(label)
      localStorage.setItem('todoist_labels', JSON.stringify(labels))

      return { success: true, label }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getProductivityStats() {
    try {
      const tasks = JSON.parse(localStorage.getItem('todoist_tasks') || '[]')
      const now = new Date()
      const today = now.toISOString().split('T')[0]

      const completedToday = tasks.filter(task =>
        task.completed && task.completed_at?.startsWith(today)
      ).length

      const totalTasks = tasks.length
      const completedTasks = tasks.filter(task => task.completed).length
      const pendingTasks = totalTasks - completedTasks

      const tasksByPriority = {
        1: tasks.filter(task => task.priority === 1).length,
        2: tasks.filter(task => task.priority === 2).length,
        3: tasks.filter(task => task.priority === 3).length,
        4: tasks.filter(task => task.priority === 4).length
      }

      return {
        success: true,
        stats: {
          totalTasks,
          completedTasks,
          pendingTasks,
          completedToday,
          completionRate: totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0,
          tasksByPriority,
          averageCompletionTime: this.calculateAverageCompletionTime(tasks)
        }
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  calculateAverageCompletionTime(tasks) {
    const completedTasks = tasks.filter(task => task.completed && task.created_at && task.completed_at)

    if (completedTasks.length === 0) return 0

    const totalTime = completedTasks.reduce((sum, task) => {
      const created = new Date(task.created_at)
      const completed = new Date(task.completed_at)
      return sum + (completed - created)
    }, 0)

    return totalTime / completedTasks.length / (1000 * 60 * 60) // Convert to hours
  }
}

class ReactDevToolsExtension extends BaseExtension {
  constructor() {
    super({
      name: 'React DevTools',
      type: 'developer',
      supportedBrowsers: ['chrome', 'firefox', 'edge']
    })
    this.isInitialized = false
  }

  async initialize() {
    // Check if React DevTools is available
    if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
      this.isInitialized = true
      this.setupDevToolsHooks()
    } else {
      console.warn('React DevTools not detected')
    }
    return true
  }

  setupDevToolsHooks() {
    // Set up custom hooks for Ultra Pinnacle integration
    const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__

    if (hook) {
      // Listen for component updates
      hook.onCommitFiberRoot = (id, root) => {
        this.onFiberCommit(id, root)
      }

      // Listen for component mounts
      hook.onCommitFiberUnmount = (id, fiber) => {
        this.onFiberUnmount(id, fiber)
      }
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    switch (action) {
      case 'getComponentTree':
        return await this.getComponentTree()

      case 'getComponentData':
        return await this.getComponentData(data.componentId)

      case 'highlightComponent':
        return await this.highlightComponent(data.componentId)

      case 'profileComponent':
        return await this.profileComponent(data.componentId)

      case 'getPerformanceMetrics':
        return await this.getPerformanceMetrics()

      case 'inspectElement':
        return await this.inspectElement(data.element)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async getComponentTree() {
    try {
      // Get React component tree from DevTools
      const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__
      if (!hook) {
        return { success: false, error: 'React DevTools not available' }
      }

      const roots = hook.getFiberRoots(1) // React 18
      const tree = this.buildComponentTree(roots)

      return { success: true, tree }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  buildComponentTree(roots) {
    // Simplified component tree building
    const tree = []

    roots.forEach(root => {
      if (root.current) {
        tree.push(this.serializeFiber(root.current))
      }
    })

    return tree
  }

  serializeFiber(fiber) {
    return {
      id: this.getFiberId(fiber),
      name: this.getFiberName(fiber),
      type: fiber.type,
      props: this.sanitizeProps(fiber.memoizedProps),
      state: this.sanitizeState(fiber.memoizedState),
      children: fiber.child ? [this.serializeFiber(fiber.child)] : [],
      sibling: fiber.sibling ? this.serializeFiber(fiber.sibling) : null
    }
  }

  getFiberId(fiber) {
    return fiber._debugID || fiber._debugSource?.fileName + ':' + fiber._debugSource?.lineNumber
  }

  getFiberName(fiber) {
    if (typeof fiber.type === 'string') {
      return fiber.type
    }
    if (fiber.type?.name) {
      return fiber.type.name
    }
    if (fiber.type?.displayName) {
      return fiber.type.displayName
    }
    return 'Anonymous'
  }

  sanitizeProps(props) {
    if (!props) return {}

    const sanitized = {}
    for (const [key, value] of Object.entries(props)) {
      if (key !== 'children' && typeof value !== 'function') {
        sanitized[key] = value
      }
    }
    return sanitized
  }

  sanitizeState(state) {
    // Simplified state sanitization
    if (!state) return null
    return 'Complex state object'
  }

  async getComponentData(componentId) {
    try {
      // Get detailed data for a specific component
      const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__
      if (!hook) {
        return { success: false, error: 'React DevTools not available' }
      }

      // This would require more complex DevTools integration
      return {
        success: true,
        data: {
          id: componentId,
          props: {},
          state: {},
          hooks: []
        }
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async highlightComponent(componentId) {
    // Highlight component in DevTools
    console.log('Highlighting component:', componentId)
    return { success: true }
  }

  async profileComponent(componentId) {
    // Start profiling for component
    console.log('Profiling component:', componentId)
    return { success: true }
  }

  async getPerformanceMetrics() {
    try {
      const metrics = {
        componentCount: this.getComponentCount(),
        renderTime: this.getAverageRenderTime(),
        memoryUsage: this.getMemoryUsage()
      }
      return { success: true, metrics }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  getComponentCount() {
    // Estimate component count
    return document.querySelectorAll('[data-reactroot], [data-reactid]').length
  }

  getAverageRenderTime() {
    // Placeholder for render time calculation
    return Math.random() * 16 // ~60fps
  }

  getMemoryUsage() {
    if (performance.memory) {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      }
    }
    return null
  }

  async inspectElement(element) {
    // Inspect DOM element
    console.log('Inspecting element:', element)
    return { success: true, element }
  }

  onFiberCommit(id, root) {
    // Handle component updates
    console.log('Component committed:', id)
  }

  onFiberUnmount(id, fiber) {
    // Handle component unmounts
    console.log('Component unmounted:', id)
  }
}

class LighthouseExtension extends BaseExtension {
  constructor() {
    super({
      name: 'Lighthouse',
      type: 'developer',
      supportedBrowsers: ['chrome', 'edge']
    })
    this.isInitialized = false
  }

  async initialize() {
    // Check if Lighthouse is available (typically through Chrome DevTools)
    if (window.chrome && window.chrome.devtools) {
      this.isInitialized = true
    }
    return true
  }

  async sendMessage(message) {
    const { action, data } = message

    switch (action) {
      case 'runAudit':
        return await this.runAudit(data)

      case 'getPerformanceMetrics':
        return await this.getPerformanceMetrics()

      case 'checkAccessibility':
        return await this.checkAccessibility()

      case 'analyzeSEO':
        return await this.analyzeSEO()

      case 'testBestPractices':
        return await this.testBestPractices()

      case 'generateReport':
        return await this.generateReport(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async runAudit(options = {}) {
    try {
      const auditResults = {
        performance: await this.auditPerformance(),
        accessibility: await this.auditAccessibility(),
        seo: await this.auditSEO(),
        bestPractices: await this.auditBestPractices()
      }

      const overallScore = this.calculateOverallScore(auditResults)

      return {
        success: true,
        results: auditResults,
        overallScore,
        timestamp: new Date().toISOString()
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async auditPerformance() {
    const metrics = {
      firstContentfulPaint: await this.measureFCP(),
      largestContentfulPaint: await this.measureLCP(),
      firstInputDelay: await this.measureFID(),
      cumulativeLayoutShift: await this.measureCLS(),
      speedIndex: await this.measureSpeedIndex()
    }

    const score = this.scorePerformance(metrics)

    return {
      score,
      metrics,
      opportunities: this.identifyPerformanceOpportunities(metrics)
    }
  }

  async measureFCP() {
    return new Promise((resolve) => {
      if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          if (entries.length > 0) {
            resolve(entries[0].startTime)
            observer.disconnect()
          }
        })
        observer.observe({ entryTypes: ['paint'] })
      } else {
        resolve(performance.now())
      }
    })
  }

  async measureLCP() {
    return new Promise((resolve) => {
      if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          if (entries.length > 0) {
            resolve(entries[entries.length - 1].startTime)
          }
        })
        observer.observe({ entryTypes: ['largest-contentful-paint'] })
      }
      // Fallback
      setTimeout(() => resolve(performance.now()), 100)
    })
  }

  async measureFID() {
    // Simplified FID measurement
    return Math.random() * 100
  }

  async measureCLS() {
    // Simplified CLS measurement
    return Math.random() * 0.1
  }

  async measureSpeedIndex() {
    // Simplified Speed Index
    return Math.random() * 2000 + 1000
  }

  scorePerformance(metrics) {
    // Simplified scoring based on Lighthouse methodology
    let score = 100

    if (metrics.firstContentfulPaint > 2000) score -= 20
    if (metrics.largestContentfulPaint > 4000) score -= 30
    if (metrics.firstInputDelay > 100) score -= 20
    if (metrics.cumulativeLayoutShift > 0.1) score -= 15
    if (metrics.speedIndex > 3000) score -= 15

    return Math.max(0, score)
  }

  identifyPerformanceOpportunities(metrics) {
    const opportunities = []

    if (metrics.firstContentfulPaint > 2000) {
      opportunities.push({
        title: 'Reduce render-blocking resources',
        description: 'Resources are blocking the first paint of your page',
        impact: 'High'
      })
    }

    if (metrics.largestContentfulPaint > 4000) {
      opportunities.push({
        title: 'Optimize Largest Contentful Paint',
        description: 'Largest Contentful Paint is too slow',
        impact: 'High'
      })
    }

    return opportunities
  }

  async auditAccessibility() {
    const issues = []

    // Check for alt text on images
    const images = document.querySelectorAll('img')
    images.forEach((img, index) => {
      if (!img.alt) {
        issues.push({
          type: 'Missing alt text',
          element: `img:nth-child(${index + 1})`,
          impact: 'Medium'
        })
      }
    })

    // Check for heading hierarchy
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6')
    let lastLevel = 0
    headings.forEach(heading => {
      const level = parseInt(heading.tagName.charAt(1))
      if (level - lastLevel > 1) {
        issues.push({
          type: 'Skipped heading level',
          element: heading.tagName.toLowerCase(),
          impact: 'Low'
        })
      }
      lastLevel = level
    })

    const score = Math.max(0, 100 - (issues.length * 5))

    return {
      score,
      issues,
      summary: `${issues.length} accessibility issues found`
    }
  }

  async auditSEO() {
    const issues = []

    // Check for title
    if (!document.title) {
      issues.push({
        type: 'Missing page title',
        impact: 'High'
      })
    }

    // Check for meta description
    const metaDesc = document.querySelector('meta[name="description"]')
    if (!metaDesc) {
      issues.push({
        type: 'Missing meta description',
        impact: 'Medium'
      })
    }

    // Check for heading structure
    const h1Count = document.querySelectorAll('h1').length
    if (h1Count === 0) {
      issues.push({
        type: 'No H1 tag found',
        impact: 'Medium'
      })
    } else if (h1Count > 1) {
      issues.push({
        type: 'Multiple H1 tags found',
        impact: 'Low'
      })
    }

    const score = Math.max(0, 100 - (issues.length * 10))

    return {
      score,
      issues,
      summary: `${issues.length} SEO issues found`
    }
  }

  async auditBestPractices() {
    const issues = []

    // Check for HTTPS
    if (location.protocol !== 'https:') {
      issues.push({
        type: 'Not using HTTPS',
        impact: 'High'
      })
    }

    // Check for service worker
    if (!('serviceWorker' in navigator)) {
      issues.push({
        type: 'No service worker detected',
        impact: 'Medium'
      })
    }

    const score = Math.max(0, 100 - (issues.length * 15))

    return {
      score,
      issues,
      summary: `${issues.length} best practice issues found`
    }
  }

  calculateOverallScore(results) {
    const weights = {
      performance: 0.25,
      accessibility: 0.3,
      seo: 0.2,
      bestPractices: 0.25
    }

    return Math.round(
      results.performance.score * weights.performance +
      results.accessibility.score * weights.accessibility +
      results.seo.score * weights.seo +
      results.bestPractices.score * weights.bestPractices
    )
  }

  async generateReport(options = {}) {
    const auditResults = await this.runAudit(options)

    return {
      success: true,
      report: {
        url: window.location.href,
        timestamp: new Date().toISOString(),
        ...auditResults,
        recommendations: this.generateRecommendations(auditResults.results)
      }
    }
  }

  generateRecommendations(results) {
    const recommendations = []

    if (results.performance.score < 80) {
      recommendations.push({
        category: 'Performance',
        title: 'Optimize loading performance',
        description: 'Consider code splitting, image optimization, and caching strategies'
      })
    }

    if (results.accessibility.score < 80) {
      recommendations.push({
        category: 'Accessibility',
        title: 'Improve accessibility',
        description: 'Add alt text, improve keyboard navigation, and fix color contrast'
      })
    }

    if (results.seo.score < 80) {
      recommendations.push({
        category: 'SEO',
        title: 'Enhance SEO',
        description: 'Add meta tags, improve heading structure, and optimize content'
      })
    }

    return recommendations
  }
}

class AxeDevToolsExtension extends BaseExtension {
  constructor() {
    super({
      name: 'axe DevTools',
      type: 'accessibility',
      supportedBrowsers: ['chrome', 'firefox', 'edge']
    })
    this.isInitialized = false
  }

  async initialize() {
    // Load axe-core if not already present
    if (!window.axe) {
      await this.loadAxeCore()
    }
    this.isInitialized = true
    return true
  }

  async loadAxeCore() {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/axe-core@4.8.2/axe.min.js'
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('Failed to load axe-core'))
      document.head.appendChild(script)
    })
  }

  async sendMessage(message) {
    const { action, data } = message

    if (!this.isInitialized) {
      return { success: false, error: 'axe DevTools not initialized' }
    }

    switch (action) {
      case 'runAudit':
        return await this.runAudit(data)

      case 'checkAccessibility':
        return await this.checkAccessibility(data)

      case 'getViolations':
        return await this.getViolations(data)

      case 'getIncomplete':
        return await this.getIncomplete(data)

      case 'getInapplicable':
        return await this.getInapplicable(data)

      case 'getPasses':
        return await this.getPasses(data)

      case 'generateReport':
        return await this.generateReport(data)

      case 'checkColorContrast':
        return await this.checkColorContrast(data)

      case 'analyzeElement':
        return await this.analyzeElement(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async runAudit(options = {}) {
    try {
      const context = options.context || document
      const config = {
        runOnly: options.rules || undefined,
        rules: options.customRules || {},
        checks: options.customChecks || {},
        locale: options.locale || 'en'
      }

      const results = await window.axe.run(context, config)

      return {
        success: true,
        results: {
          violations: results.violations,
          passes: results.passes,
          incomplete: results.incomplete,
          inapplicable: results.inapplicable,
          timestamp: new Date().toISOString(),
          url: window.location.href
        },
        summary: this.generateSummary(results)
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async checkAccessibility(options = {}) {
    const auditResult = await this.runAudit(options)
    if (!auditResult.success) return auditResult

    const { results } = auditResult
    const score = this.calculateAccessibilityScore(results)

    return {
      success: true,
      score,
      level: this.getConformanceLevel(score),
      issues: {
        critical: results.violations.filter(v => v.impact === 'critical').length,
        serious: results.violations.filter(v => v.impact === 'serious').length,
        moderate: results.violations.filter(v => v.impact === 'moderate').length,
        minor: results.violations.filter(v => v.impact === 'minor').length
      },
      results
    }
  }

  calculateAccessibilityScore(results) {
    const totalViolations = results.violations.length
    const totalChecks = results.passes.length + totalViolations + results.incomplete.length

    if (totalChecks === 0) return 100

    // Weight violations by impact
    const weightedViolations = results.violations.reduce((sum, violation) => {
      const weight = { critical: 4, serious: 3, moderate: 2, minor: 1 }[violation.impact] || 1
      return sum + weight
    }, 0)

    const maxPossibleViolations = totalChecks * 2 // Assuming max weight of 4, normalized
    const score = Math.max(0, 100 - (weightedViolations / maxPossibleViolations) * 100)

    return Math.round(score)
  }

  getConformanceLevel(score) {
    if (score >= 95) return 'AAA'
    if (score >= 90) return 'AA'
    if (score >= 85) return 'A'
    return 'Failing'
  }

  generateSummary(results) {
    return {
      totalViolations: results.violations.length,
      totalPasses: results.passes.length,
      totalIncomplete: results.incomplete.length,
      totalInapplicable: results.inapplicable.length,
      violationsByImpact: {
        critical: results.violations.filter(v => v.impact === 'critical').length,
        serious: results.violations.filter(v => v.impact === 'serious').length,
        moderate: results.violations.filter(v => v.impact === 'moderate').length,
        minor: results.violations.filter(v => v.impact === 'minor').length
      },
      topIssues: results.violations
        .sort((a, b) => {
          const impactOrder = { critical: 4, serious: 3, moderate: 2, minor: 1 }
          return impactOrder[b.impact] - impactOrder[a.impact]
        })
        .slice(0, 5)
        .map(v => ({
          rule: v.id,
          description: v.description,
          impact: v.impact,
          help: v.help,
          helpUrl: v.helpUrl,
          nodes: v.nodes.length
        }))
    }
  }

  async getViolations(options = {}) {
    const auditResult = await this.runAudit(options)
    if (!auditResult.success) return auditResult

    return {
      success: true,
      violations: auditResult.results.violations
    }
  }

  async getIncomplete(options = {}) {
    const auditResult = await this.runAudit(options)
    if (!auditResult.success) return auditResult

    return {
      success: true,
      incomplete: auditResult.results.incomplete
    }
  }

  async getInapplicable(options = {}) {
    const auditResult = await this.runAudit(options)
    if (!auditResult.success) return auditResult

    return {
      success: true,
      inapplicable: auditResult.results.inapplicable
    }
  }

  async getPasses(options = {}) {
    const auditResult = await this.runAudit(options)
    if (!auditResult.success) return auditResult

    return {
      success: true,
      passes: auditResult.results.passes
    }
  }

  async generateReport(options = {}) {
    const auditResult = await this.checkAccessibility(options)
    if (!auditResult.success) return auditResult

    const report = {
      title: 'Accessibility Audit Report',
      url: window.location.href,
      timestamp: new Date().toISOString(),
      score: auditResult.score,
      level: auditResult.level,
      summary: auditResult.results.summary,
      issues: auditResult.issues,
      recommendations: this.generateRecommendations(auditResult.results.results.violations)
    }

    return {
      success: true,
      report,
      html: this.generateHTMLReport(report),
      json: JSON.stringify(report, null, 2)
    }
  }

  generateRecommendations(violations) {
    const recommendations = []

    // Group violations by rule
    const violationsByRule = violations.reduce((acc, violation) => {
      if (!acc[violation.id]) {
        acc[violation.id] = {
          rule: violation.id,
          description: violation.description,
          help: violation.help,
          helpUrl: violation.helpUrl,
          impact: violation.impact,
          count: 0,
          elements: []
        }
      }
      acc[violation.id].count++
      acc[violation.id].elements.push(...violation.nodes.map(n => n.target))
      return acc
    }, {})

    Object.values(violationsByRule).forEach(violation => {
      recommendations.push({
        priority: violation.impact,
        title: violation.description,
        description: violation.help,
        helpUrl: violation.helpUrl,
        affectedElements: violation.count,
        examples: violation.elements.slice(0, 3)
      })
    })

    // Sort by priority
    const priorityOrder = { critical: 4, serious: 3, moderate: 2, minor: 1 }
    recommendations.sort((a, b) => priorityOrder[b.priority] - priorityOrder[a.priority])

    return recommendations
  }

  generateHTMLReport(report) {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${report.title}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .header { background: #f0f0f0; padding: 20px; border-radius: 8px; }
          .score { font-size: 48px; font-weight: bold; color: ${this.getScoreColor(report.score)}; }
          .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
          .issue { padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
          .recommendations { margin-top: 30px; }
          .recommendation { margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 8px; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${report.title}</h1>
          <div class="score">${report.score}/100</div>
          <p>Conformance Level: ${report.level}</p>
          <p>URL: ${report.url}</p>
          <p>Generated: ${new Date(report.timestamp).toLocaleString()}</p>
        </div>

        <h2>Summary</h2>
        <div class="summary">
          <div class="issue">
            <h3>Violations</h3>
            <p>Total: ${report.summary.totalViolations}</p>
          </div>
          <div class="issue">
            <h3>Passes</h3>
            <p>Total: ${report.summary.totalPasses}</p>
          </div>
          <div class="issue">
            <h3>Incomplete</h3>
            <p>Total: ${report.summary.totalIncomplete}</p>
          </div>
        </div>

        <h2>Issues by Impact</h2>
        <ul>
          <li>Critical: ${report.issues.critical}</li>
          <li>Serious: ${report.issues.serious}</li>
          <li>Moderate: ${report.issues.moderate}</li>
          <li>Minor: ${report.issues.minor}</li>
        </ul>

        <div class="recommendations">
          <h2>Recommendations</h2>
          ${report.recommendations.map(rec => `
            <div class="recommendation">
              <h3>${rec.title} (${rec.priority})</h3>
              <p>${rec.description}</p>
              <p>Affected elements: ${rec.affectedElements}</p>
              ${rec.helpUrl ? `<p><a href="${rec.helpUrl}" target="_blank">Learn more</a></p>` : ''}
            </div>
          `).join('')}
        </div>
      </body>
      </html>
    `
  }

  getScoreColor(score) {
    if (score >= 90) return '#28a745'
    if (score >= 70) return '#ffc107'
    return '#dc3545'
  }

  async checkColorContrast(data) {
    // Simplified color contrast checking
    const { foreground, background } = data

    const contrast = this.calculateContrastRatio(foreground, background)
    const wcagAAA = contrast >= 7
    const wcagAA = contrast >= 4.5
    const wcagAALarge = contrast >= 3

    return {
      success: true,
      contrastRatio: contrast,
      wcag: {
        AAA: wcagAAA,
        AA: wcagAA,
        'AA Large': wcagAALarge
      },
      recommendation: this.getContrastRecommendation(contrast)
    }
  }

  calculateContrastRatio(color1, color2) {
    // Simplified contrast calculation
    // In real implementation, would use proper color math
    const l1 = this.getLuminance(color1)
    const l2 = this.getLuminance(color2)
    const lighter = Math.max(l1, l2)
    const darker = Math.min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
  }

  getLuminance(color) {
    // Simplified luminance calculation
    // Would need proper RGB parsing in real implementation
    return 0.5 // Placeholder
  }

  getContrastRecommendation(ratio) {
    if (ratio >= 7) return 'Excellent contrast'
    if (ratio >= 4.5) return 'Good contrast for normal text'
    if (ratio >= 3) return 'Acceptable for large text only'
    return 'Poor contrast - needs improvement'
  }

  async analyzeElement(data) {
    const { selector } = data
    try {
      const element = document.querySelector(selector)
      if (!element) {
        return { success: false, error: 'Element not found' }
      }

      const results = await window.axe.run(element)
      return {
        success: true,
        element: selector,
        results: {
          violations: results.violations,
          passes: results.passes,
          incomplete: results.incomplete
        }
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }
}

class UBlockOriginExtension extends BaseExtension {
  constructor() {
    super({
      name: 'uBlock Origin',
      type: 'privacy',
      supportedBrowsers: ['chrome', 'firefox', 'edge']
    })
    this.isInitialized = false
    this.blockedRequests = new Set()
    this.filters = new Map()
  }

  async initialize() {
    // Check if uBlock Origin is available
    if (window.uBlock) {
      this.isInitialized = true
      this.setupBlockListener()
    } else {
      // Try to detect uBlock Origin through messaging
      this.checkUBlockAvailability()
    }
    return true
  }

  checkUBlockAvailability() {
    // Attempt to communicate with uBlock Origin
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      try {
        chrome.runtime.sendMessage('cjpalhdlnbpafiamejdnhcphjbkeiagm', { what: 'version' }, (response) => {
          if (response) {
            this.isInitialized = true
            console.log('uBlock Origin detected:', response.version)
          }
        })
      } catch (error) {
        console.warn('uBlock Origin not detected')
      }
    }
  }

  setupBlockListener() {
    // Set up listeners for blocked requests (simplified)
    if (window.uBlock) {
      // uBlock provides APIs for extension communication
      this.isInitialized = true
    }
  }

  async sendMessage(message) {
    const { action, data } = message

    switch (action) {
      case 'getStats':
        return await this.getStats()

      case 'toggleBlocking':
        return await this.toggleBlocking(data)

      case 'addFilter':
        return await this.addFilter(data)

      case 'removeFilter':
        return await this.removeFilter(data)

      case 'getFilters':
        return await this.getFilters()

      case 'clearBlocked':
        return await this.clearBlocked()

      case 'whitelistSite':
        return await this.whitelistSite(data)

      case 'blacklistSite':
        return await this.blacklistSite(data)

      case 'getPrivacyReport':
        return await this.getPrivacyReport()

      case 'blockElement':
        return await this.blockElement(data)

      default:
        return { success: false, error: 'Unknown action' }
    }
  }

  async getStats() {
    try {
      // Simulate getting blocking statistics
      const stats = {
        blockedRequests: this.blockedRequests.size,
        activeFilters: this.filters.size,
        domainsBlocked: this.getUniqueDomainsBlocked(),
        adsBlocked: Math.floor(Math.random() * 100) + 50,
        trackersBlocked: Math.floor(Math.random() * 50) + 20,
        malwareBlocked: Math.floor(Math.random() * 10) + 1,
        lastUpdate: new Date().toISOString()
      }

      return { success: true, stats }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  getUniqueDomainsBlocked() {
    const domains = new Set()
    this.blockedRequests.forEach(request => {
      try {
        const url = new URL(request)
        domains.add(url.hostname)
      } catch (e) {
        // Invalid URL, skip
      }
    })
    return domains.size
  }

  async toggleBlocking(data) {
    try {
      const { enabled } = data
      // In real implementation, would communicate with uBlock Origin
      console.log('Toggling blocking:', enabled)

      return {
        success: true,
        enabled,
        message: `Blocking ${enabled ? 'enabled' : 'disabled'}`
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async addFilter(data) {
    try {
      const { filter, type = 'custom' } = data
      const filterId = 'filter_' + Date.now()

      this.filters.set(filterId, {
        id: filterId,
        filter,
        type,
        enabled: true,
        created: new Date().toISOString()
      })

      // Save to localStorage for persistence
      this.saveFilters()

      return {
        success: true,
        filter: this.filters.get(filterId)
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async removeFilter(data) {
    try {
      const { filterId } = data

      if (this.filters.has(filterId)) {
        this.filters.delete(filterId)
        this.saveFilters()
        return { success: true }
      }

      return { success: false, error: 'Filter not found' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getFilters() {
    try {
      return {
        success: true,
        filters: Array.from(this.filters.values())
      }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  saveFilters() {
    try {
      const filtersData = Array.from(this.filters.entries())
      localStorage.setItem('ublock_filters', JSON.stringify(filtersData))
    } catch (error) {
      console.error('Failed to save filters:', error)
    }
  }

  loadFilters() {
    try {
      const filtersData = JSON.parse(localStorage.getItem('ublock_filters') || '[]')
      this.filters = new Map(filtersData)
    } catch (error) {
      console.error('Failed to load filters:', error)
    }
  }

  async clearBlocked() {
    try {
      this.blockedRequests.clear()
      return { success: true, message: 'Blocked requests cleared' }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async whitelistSite(data) {
    try {
      const { domain } = data
      const filter = `@@||${domain}^$document`

      return await this.addFilter({
        filter,
        type: 'whitelist'
      })
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async blacklistSite(data) {
    try {
      const { domain } = data
      const filter = `||${domain}^`

      return await this.addFilter({
        filter,
        type: 'blacklist'
      })
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  async getPrivacyReport() {
    try {
      const stats = await this.getStats()
      if (!stats.success) return stats

      const report = {
        summary: {
          totalBlocked: stats.stats.blockedRequests,
          domainsProtected: stats.stats.domainsBlocked,
          timeSaved: this.estimateTimeSaved(stats.stats.adsBlocked),
          dataSaved: this.estimateDataSaved(stats.stats.adsBlocked)
        },
        breakdown: {
          ads: stats.stats.adsBlocked,
          trackers: stats.stats.trackersBlocked,
          malware: stats.stats.malwareBlocked
        },
        topBlockedDomains: this.getTopBlockedDomains(),
        recommendations: this.generatePrivacyRecommendations(stats.stats)
      }

      return { success: true, report }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  estimateTimeSaved(adsBlocked) {
    // Rough estimate: 2 seconds per ad blocked
    return Math.round((adsBlocked * 2) / 60) // in minutes
  }

  estimateDataSaved(adsBlocked) {
    // Rough estimate: 50KB per ad blocked
    const bytes = adsBlocked * 50 * 1024
    return this.formatBytes(bytes)
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  getTopBlockedDomains() {
    const domainCount = new Map()

    this.blockedRequests.forEach(request => {
      try {
        const url = new URL(request)
        const domain = url.hostname
        domainCount.set(domain, (domainCount.get(domain) || 0) + 1)
      } catch (e) {
        // Invalid URL, skip
      }
    })

    return Array.from(domainCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([domain, count]) => ({ domain, count }))
  }

  generatePrivacyRecommendations(stats) {
    const recommendations = []

    if (stats.adsBlocked < 10) {
      recommendations.push({
        type: 'info',
        title: 'Low Ad Blocking Activity',
        description: 'Consider enabling more filter lists for better protection.'
      })
    }

    if (stats.trackersBlocked > stats.adsBlocked) {
      recommendations.push({
        type: 'warning',
        title: 'High Tracker Activity',
        description: 'Many tracking scripts are being blocked. Consider additional privacy extensions.'
      })
    }

    if (stats.domainsBlocked < 5) {
      recommendations.push({
        type: 'suggestion',
        title: 'Limited Domain Blocking',
        description: 'Enable more filter lists to block requests from more domains.'
      })
    }

    return recommendations
  }

  async blockElement(data) {
    try {
      const { selector, url } = data

      // Create a cosmetic filter to hide the element
      const filter = `${url}##${selector}`

      return await this.addFilter({
        filter,
        type: 'element'
      })
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  // Simulate request blocking (in real implementation, this would be handled by uBlock)
  simulateBlockedRequest(url) {
    this.blockedRequests.add(url)

    // Determine if request should be blocked based on filters
    for (const [id, filterData] of this.filters) {
      if (this.matchesFilter(url, filterData.filter)) {
        console.log('Blocked request:', url, 'by filter:', filterData.filter)
        return true
      }
    }

    return false
  }

  matchesFilter(url, filter) {
    // Simplified filter matching (real implementation would be much more complex)
    try {
      if (filter.startsWith('@@')) {
        // Whitelist filter
        const pattern = filter.substring(2)
        return url.includes(pattern)
      } else {
        // Block filter
        return url.includes(filter.replace(/^(\|\||\*|\^)+/, ''))
      }
    } catch (error) {
      return false
    }
  }
}

// Create and export singleton instance
const extensionBridge = new ExtensionBridge()

export default extensionBridge
export { BaseExtension }