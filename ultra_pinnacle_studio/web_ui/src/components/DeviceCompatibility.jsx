import React, { useState, useEffect } from 'react'
import axios from 'axios'

const DeviceCompatibility = ({ token }) => {
  const [devices, setDevices] = useState([])
  const [currentDevice, setCurrentDevice] = useState({})
  const [compatibilityMatrix, setCompatibilityMatrix] = useState({})
  const [optimizationSettings, setOptimizationSettings] = useState({})
  const [syncStatus, setSyncStatus] = useState('idle')
  const [isOptimizing, setIsOptimizing] = useState(false)

  const deviceTypes = [
    { id: 'desktop', name: 'Desktop', icon: '🖥️' },
    { id: 'laptop', name: 'Laptop', icon: '💻' },
    { id: 'tablet', name: 'Tablet', icon: '📱' },
    { id: 'mobile', name: 'Mobile', icon: '📱' },
    { id: 'smartwatch', name: 'Smartwatch', icon: '⌚' },
    { id: 'tv', name: 'Smart TV', icon: '📺' },
    { id: 'console', name: 'Gaming Console', icon: '🎮' },
    { id: 'iot', name: 'IoT Device', icon: '🔌' }
  ]

  const operatingSystems = [
    { id: 'windows', name: 'Windows', icon: '🪟' },
    { id: 'macos', name: 'macOS', icon: '🍎' },
    { id: 'linux', name: 'Linux', icon: '🐧' },
    { id: 'android', name: 'Android', icon: '🤖' },
    { id: 'ios', name: 'iOS', icon: '📱' },
    { id: 'tvos', name: 'tvOS', icon: '📺' },
    { id: 'web', name: 'Web Browser', icon: '🌐' }
  ]

  const capabilities = [
    { id: 'touch', name: 'Touch Screen', icon: '👆' },
    { id: 'keyboard', name: 'Physical Keyboard', icon: '⌨️' },
    { id: 'mouse', name: 'Mouse', icon: '🖱️' },
    { id: 'camera', name: 'Camera', icon: '📷' },
    { id: 'microphone', name: 'Microphone', icon: '🎤' },
    { id: 'speakers', name: 'Speakers', icon: '🔊' },
    { id: 'accelerometer', name: 'Accelerometer', icon: '📳' },
    { id: 'gyroscope', name: 'Gyroscope', icon: '🌀' },
    { id: 'gps', name: 'GPS', icon: '📍' },
    { id: 'bluetooth', name: 'Bluetooth', icon: '📶' },
    { id: 'wifi', name: 'WiFi', icon: '📡' },
    { id: 'usb', name: 'USB', icon: '🔌' },
    { id: 'webgl', name: 'WebGL', icon: '🎮' },
    { id: 'webgpu', name: 'WebGPU', icon: '🚀' },
    { id: 'webrtc', name: 'WebRTC', icon: '📹' },
    { id: 'indexeddb', name: 'IndexedDB', icon: '💾' },
    { id: 'serviceworker', name: 'Service Worker', icon: '⚙️' }
  ]

  useEffect(() => {
    if (token) {
      detectCurrentDevice()
      loadDevices()
      loadCompatibilityMatrix()
      loadOptimizationSettings()
    }
  }, [token])

  const detectCurrentDevice = () => {
    const deviceInfo = {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine,
      hardwareConcurrency: navigator.hardwareConcurrency || 'Unknown',
      deviceMemory: navigator.deviceMemory || 'Unknown',
      maxTouchPoints: navigator.maxTouchPoints || 0,
      screen: {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth,
        pixelRatio: window.devicePixelRatio || 1
      },
      capabilities: {}
    }

    // Detect capabilities
    capabilities.forEach(cap => {
      switch (cap.id) {
        case 'touch':
          deviceInfo.capabilities[cap.id] = 'ontouchstart' in window
          break
        case 'webgl':
          deviceInfo.capabilities[cap.id] = !!window.WebGLRenderingContext
          break
        case 'webgpu':
          deviceInfo.capabilities[cap.id] = !!navigator.gpu
          break
        case 'webrtc':
          deviceInfo.capabilities[cap.id] = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
          break
        case 'indexeddb':
          deviceInfo.capabilities[cap.id] = !!window.indexedDB
          break
        case 'serviceworker':
          deviceInfo.capabilities[cap.id] = 'serviceWorker' in navigator
          break
        case 'camera':
        case 'microphone':
          deviceInfo.capabilities[cap.id] = !!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices)
          break
        case 'gps':
          deviceInfo.capabilities[cap.id] = 'geolocation' in navigator
          break
        case 'bluetooth':
          deviceInfo.capabilities[cap.id] = !!navigator.bluetooth
          break
        default:
          deviceInfo.capabilities[cap.id] = true // Assume available for basic features
      }
    })

    setCurrentDevice(deviceInfo)
  }

  const loadDevices = async () => {
    try {
      const response = await axios.get('http://localhost:8000/devices/registered', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDevices(response.data.devices || [])
    } catch (error) {
      console.error('Error loading devices:', error)
    }
  }

  const loadCompatibilityMatrix = async () => {
    try {
      const response = await axios.get('http://localhost:8000/devices/compatibility', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setCompatibilityMatrix(response.data.matrix || {})
    } catch (error) {
      console.error('Error loading compatibility matrix:', error)
    }
  }

  const loadOptimizationSettings = async () => {
    try {
      const response = await axios.get('http://localhost:8000/devices/optimization', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setOptimizationSettings(response.data.settings || {})
    } catch (error) {
      console.error('Error loading optimization settings:', error)
    }
  }

  const registerDevice = async () => {
    try {
      const response = await axios.post('http://localhost:8000/devices/register', {
        deviceInfo: currentDevice
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Device registered successfully!')
      loadDevices()
    } catch (error) {
      alert('Error registering device: ' + error.message)
    }
  }

  const optimizeForDevice = async (deviceId) => {
    setIsOptimizing(true)
    try {
      const response = await axios.post('http://localhost:8000/devices/optimize', {
        deviceId: deviceId,
        currentDevice: currentDevice
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Device optimization completed!')
      loadOptimizationSettings()
    } catch (error) {
      alert('Error optimizing device: ' + error.message)
    } finally {
      setIsOptimizing(false)
    }
  }

  const syncDevices = async () => {
    setSyncStatus('syncing')
    try {
      const response = await axios.post('http://localhost:8000/devices/sync', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Device sync completed!')
      loadDevices()
    } catch (error) {
      alert('Error syncing devices: ' + error.message)
    } finally {
      setSyncStatus('idle')
    }
  }

  const getCompatibilityScore = (deviceType, os) => {
    const key = `${deviceType}-${os}`
    return compatibilityMatrix[key] || 0
  }

  const getCapabilityStatus = (capabilityId) => {
    return currentDevice.capabilities?.[capabilityId] ? '✅' : '❌'
  }

  return (
    <div style={{ padding: '1rem', height: '100vh', overflow: 'auto' }}>
      <h1>Device Compatibility</h1>
      <p>Cross-platform support and device optimization</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
        {/* Main Content */}
        <div>
          {/* Current Device Info */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Current Device</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div>
                <strong>Platform:</strong> {currentDevice.platform || 'Unknown'}
              </div>
              <div>
                <strong>Screen:</strong> {currentDevice.screen?.width || 0} x {currentDevice.screen?.height || 0}
              </div>
              <div>
                <strong>CPU Cores:</strong> {currentDevice.hardwareConcurrency}
              </div>
              <div>
                <strong>Memory:</strong> {currentDevice.deviceMemory} GB
              </div>
              <div>
                <strong>Touch Points:</strong> {currentDevice.maxTouchPoints}
              </div>
              <div>
                <strong>Pixel Ratio:</strong> {currentDevice.screen?.pixelRatio || 1}
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              <button onClick={registerDevice}>Register This Device</button>
              <button onClick={detectCurrentDevice} style={{ marginLeft: '1rem' }}>Refresh Detection</button>
            </div>
          </div>

          {/* Device Capabilities */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Device Capabilities</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '0.5rem' }}>
              {capabilities.map(cap => (
                <div key={cap.id} style={{
                  padding: '0.5rem',
                  border: '1px solid #eee',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <span>{cap.icon}</span>
                  <span style={{ fontSize: '0.9rem' }}>{cap.name}</span>
                  <span style={{ marginLeft: 'auto' }}>{getCapabilityStatus(cap.id)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Compatibility Matrix */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Compatibility Matrix</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '0.5rem', border: '1px solid #ccc' }}>Device Type</th>
                    {operatingSystems.map(os => (
                      <th key={os.id} style={{ padding: '0.5rem', border: '1px solid #ccc' }}>
                        {os.icon} {os.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {deviceTypes.map(device => (
                    <tr key={device.id}>
                      <td style={{ padding: '0.5rem', border: '1px solid #ccc', fontWeight: 'bold' }}>
                        {device.icon} {device.name}
                      </td>
                      {operatingSystems.map(os => {
                        const score = getCompatibilityScore(device.id, os.id)
                        return (
                          <td key={os.id} style={{
                            padding: '0.5rem',
                            border: '1px solid #ccc',
                            textAlign: 'center',
                            backgroundColor: score >= 90 ? '#d4edda' : score >= 70 ? '#fff3cd' : '#f8d7da'
                          }}>
                            {score}%
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Registered Devices */}
          <div style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h3>Registered Devices ({devices.length})</h3>
            <div style={{ display: 'grid', gap: '1rem' }}>
              {devices.map(device => (
                <div key={device.id} style={{
                  border: '1px solid #eee',
                  borderRadius: '4px',
                  padding: '1rem',
                  background: '#f9f9f9'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h4>{device.name}</h4>
                      <p>{device.type} • {device.os} • Last seen: {new Date(device.lastSeen).toLocaleString()}</p>
                    </div>
                    <div>
                      <button
                        onClick={() => optimizeForDevice(device.id)}
                        disabled={isOptimizing}
                      >
                        {isOptimizing ? 'Optimizing...' : 'Optimize'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div>
          {/* Quick Actions */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Quick Actions</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <button onClick={syncDevices} disabled={syncStatus === 'syncing'}>
                {syncStatus === 'syncing' ? 'Syncing...' : 'Sync Devices'}
              </button>
              <button onClick={loadCompatibilityMatrix}>Refresh Matrix</button>
              <button onClick={() => window.location.reload()}>Test Compatibility</button>
            </div>
          </div>

          {/* Optimization Settings */}
          <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Optimization Settings</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <label>
                <input
                  type="checkbox"
                  checked={optimizationSettings.autoOptimize || false}
                  onChange={(e) => setOptimizationSettings(prev => ({ ...prev, autoOptimize: e.target.checked }))}
                />
                Auto-optimize for device
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={optimizationSettings.adaptiveUI || false}
                  onChange={(e) => setOptimizationSettings(prev => ({ ...prev, adaptiveUI: e.target.checked }))}
                />
                Adaptive UI
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={optimizationSettings.performanceMode || false}
                  onChange={(e) => setOptimizationSettings(prev => ({ ...prev, performanceMode: e.target.checked }))}
                />
                Performance mode
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={optimizationSettings.offlineMode || false}
                  onChange={(e) => setOptimizationSettings(prev => ({ ...prev, offlineMode: e.target.checked }))}
                />
                Offline mode
              </label>
            </div>
          </div>

          {/* Device Stats */}
          <div style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h4>Device Statistics</h4>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              <div><strong>Total Devices:</strong> {devices.length}</div>
              <div><strong>Active Now:</strong> {devices.filter(d => d.isActive).length}</div>
              <div><strong>Compatibility Score:</strong> {Math.round(Object.values(compatibilityMatrix).reduce((a, b) => a + b, 0) / Object.values(compatibilityMatrix).length) || 0}%</div>
              <div><strong>Optimization Level:</strong> {optimizationSettings.level || 'Standard'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DeviceCompatibility