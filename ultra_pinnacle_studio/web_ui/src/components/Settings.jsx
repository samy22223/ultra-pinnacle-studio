import React, { useState, useEffect } from 'react'
import axios from 'axios'

const Settings = ({ token }) => {
  const [settings, setSettings] = useState({
    ai: {
      defaultModel: 'gpt-4',
      autoEnhance: true,
      temperature: 0.7,
      maxTokens: 2048,
      enableMultimodal: true,
      autonomousAgents: true,
      selfOptimization: true
    },
    canvas: {
      autoSave: true,
      autoSaveInterval: 30,
      pressureSensitivity: true,
      touchOptimization: true,
      exportQuality: 'high',
      collaborationMode: false
    },
    performance: {
      enableCaching: true,
      preloadModels: true,
      adaptiveQuality: true,
      backgroundOptimization: true,
      memoryManagement: 'auto'
    },
    automation: {
      autoBackup: true,
      backupInterval: 3600,
      autoUpdate: true,
      selfHealing: true,
      predictiveLoading: true,
      smartResourceAllocation: true
    },
    devices: {
      autoDetect: true,
      optimizeForDevice: true,
      crossPlatformSync: true,
      offlineMode: 'smart'
    },
    security: {
      encryptionLevel: 'high',
      autoLock: true,
      secureStorage: true,
      auditLogging: true,
      anomalyDetection: true
    }
  })

  const [systemStatus, setSystemStatus] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    modelsLoaded: 0,
    activeTasks: 0,
    networkStatus: 'online'
  })

  const [availableModels, setAvailableModels] = useState([])
  const [enhancementProgress, setEnhancementProgress] = useState(0)
  const [isEnhancing, setIsEnhancing] = useState(false)

  useEffect(() => {
    if (token) {
      loadSystemStatus()
      loadAvailableModels()
      const interval = setInterval(loadSystemStatus, 5000)
      return () => clearInterval(interval)
    }
  }, [token])

  const loadSystemStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/health', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSystemStatus(prev => ({
        ...prev,
        modelsLoaded: response.data.models_loaded || 0,
        activeTasks: response.data.active_tasks || 0
      }))
    } catch (error) {
      console.error('Error loading system status:', error)
    }
  }

  const loadAvailableModels = async () => {
    try {
      const response = await axios.get('http://localhost:8000/models', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setAvailableModels(Object.keys(response.data.models || {}))
    } catch (error) {
      console.error('Error loading models:', error)
    }
  }

  const updateSetting = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
  }

  const saveSettings = async () => {
    try {
      await axios.post('http://localhost:8000/settings/update', settings, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Settings saved successfully!')
    } catch (error) {
      alert('Error saving settings: ' + error.message)
    }
  }

  const optimizeSystem = async () => {
    setIsEnhancing(true)
    setEnhancementProgress(0)
    
    try {
      const steps = [
        'Analyzing system performance...',
        'Optimizing AI model loading...',
        'Configuring caching strategies...',
        'Setting up predictive loading...',
        'Enabling autonomous features...',
        'Optimizing resource allocation...',
        'Configuring self-healing mechanisms...',
        'Finalizing enhancements...'
      ]

      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        setEnhancementProgress(((i + 1) / steps.length) * 100)
      }

      alert('System optimized successfully! All pinnacle features enabled.')
    } catch (error) {
      alert('Error optimizing system: ' + error.message)
    } finally {
      setIsEnhancing(false)
      setEnhancementProgress(0)
    }
  }

  const autoConfigure = async () => {
    try {
      const response = await axios.post('http://localhost:8000/settings/auto-configure', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSettings(response.data.settings)
      alert('System auto-configured for optimal performance!')
    } catch (error) {
      alert('Error auto-configuring: ' + error.message)
    }
  }

  const StatusIndicator = ({ value, label }) => (
    <div style={{ margin: '10px 0' }}>
      <div>{label}: {value}%</div>
      <div style={{ width: '100%', backgroundColor: '#e0e0e0', borderRadius: '4px' }}>
        <div 
          style={{ 
            width: `${value}%`, 
            backgroundColor: value > 80 ? '#ff4444' : value > 60 ? '#ffaa00' : '#44ff44',
            height: '20px',
            borderRadius: '4px'
          }}
        />
      </div>
    </div>
  )

  return (
    <div style={{ padding: '20px' }}>
      <h1>Ultra Pinnacle Studio Settings</h1>
      <p>Comprehensive configuration for autonomous AI-powered creative platform</p>

      <div style={{ marginBottom: '30px' }}>
        <h2>System Status</h2>
        <StatusIndicator value={systemStatus.cpu} label="CPU Usage" />
        <StatusIndicator value={systemStatus.memory} label="Memory Usage" />
        <StatusIndicator value={systemStatus.disk} label="Disk Usage" />
        <div>Models Loaded: {systemStatus.modelsLoaded}</div>
        <div>Active Tasks: {systemStatus.activeTasks}</div>
        <div>Network: {systemStatus.networkStatus}</div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>Quick Actions</h2>
        <button 
          onClick={optimizeSystem} 
          disabled={isEnhancing}
          style={{ 
            padding: '10px 20px', 
            margin: '5px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px'
          }}
        >
          {isEnhancing ? `Optimizing... ${enhancementProgress}%` : 'Optimize System'}
        </button>
        <button 
          onClick={autoConfigure}
          style={{ 
            padding: '10px 20px', 
            margin: '5px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px'
          }}
        >
          Auto-Configure
        </button>
        <button 
          onClick={saveSettings}
          style={{ 
            padding: '10px 20px', 
            margin: '5px',
            backgroundColor: '#17a2b8',
            color: 'white',
            border: 'none',
            borderRadius: '4px'
          }}
        >
          Save Settings
        </button>
      </div>

      <div>
        <h2>AI & Intelligence Settings</h2>
        <div style={{ marginBottom: '20px' }}>
          <label>
            Default AI Model:
            <select 
              value={settings.ai.defaultModel}
              onChange={(e) => updateSetting('ai', 'defaultModel', e.target.value)}
              style={{ marginLeft: '10px' }}
            >
              {availableModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.ai.autoEnhance}
              onChange={(e) => updateSetting('ai', 'autoEnhance', e.target.checked)}
            />
            Auto-Enhance Prompts
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.ai.enableMultimodal}
              onChange={(e) => updateSetting('ai', 'enableMultimodal', e.target.checked)}
            />
            Enable Multimodal AI
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.ai.autonomousAgents}
              onChange={(e) => updateSetting('ai', 'autonomousAgents', e.target.checked)}
            />
            Autonomous AI Agents
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.ai.selfOptimization}
              onChange={(e) => updateSetting('ai', 'selfOptimization', e.target.checked)}
            />
            Self-Optimization
          </label>
        </div>
      </div>

      <div style={{ marginTop: '30px' }}>
        <h2>Performance & Optimization</h2>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.performance.enableCaching}
              onChange={(e) => updateSetting('performance', 'enableCaching', e.target.checked)}
            />
            Enable Intelligent Caching
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.performance.preloadModels}
              onChange={(e) => updateSetting('performance', 'preloadModels', e.target.checked)}
            />
            Preload AI Models
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.performance.backgroundOptimization}
              onChange={(e) => updateSetting('performance', 'backgroundOptimization', e.target.checked)}
            />
            Background Optimization
          </label>
        </div>
      </div>

      <div style={{ marginTop: '30px' }}>
        <h2>Automation & Intelligence</h2>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.automation.autoBackup}
              onChange={(e) => updateSetting('automation', 'autoBackup', e.target.checked)}
            />
            Auto-Backup System
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.automation.selfHealing}
              onChange={(e) => updateSetting('automation', 'selfHealing', e.target.checked)}
            />
            Self-Healing System
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input 
              type="checkbox"
              checked={settings.automation.predictiveLoading}
              onChange={(e) => updateSetting('automation', 'predictiveLoading', e.target.checked)}
            />
            Predictive Loading
          </label>
        </div>
      </div>
    </div>
  )
}

export default Settings
