import React, { useRef, useState } from 'react'
import { Stage, Layer, Line, Rect, Text } from 'react-konva'
import axios from 'axios'

const Canvas = ({ token }) => {
  const [layers, setLayers] = useState([
    { id: 1, name: 'Layer 1', visible: true, lines: [] }
  ])
  const [activeLayerId, setActiveLayerId] = useState(1)
  const [isDrawing, setIsDrawing] = useState(false)
  const [brushColor, setBrushColor] = useState('#000000')
  const [brushSize, setBrushSize] = useState(2)
  const [tool, setTool] = useState('brush')
  const [prompt, setPrompt] = useState('')
  const [enhancedPrompt, setEnhancedPrompt] = useState('')
  const [projects, setProjects] = useState([])
  const [currentProjectName, setCurrentProjectName] = useState('Untitled Project')
  const [history, setHistory] = useState([]) // For undo/redo
  const [historyIndex, setHistoryIndex] = useState(-1)
  const stageRef = useRef(null)

  const activeLayer = layers.find(l => l.id === activeLayerId)

  const handlePointerDown = (e) => {
    if (tool !== 'brush') return
    setIsDrawing(true)
    const pos = e.target.getStage().getPointerPosition()
    const pressure = e.evt.pressure || 1 // Default to 1 if not supported
    const dynamicSize = brushSize * (0.5 + pressure * 0.5) // Pressure affects brush size

    const newLines = [...activeLayer.lines, {
      points: [pos.x, pos.y],
      stroke: brushColor,
      strokeWidth: dynamicSize,
      pressure: pressure
    }]
    updateLayer(activeLayerId, { lines: newLines })
  }

  const handlePointerMove = (e) => {
    if (!isDrawing || tool !== 'brush') return
    const stage = e.target.getStage()
    const point = stage.getPointerPosition()
    const pressure = e.evt.pressure || 1
    const dynamicSize = brushSize * (0.5 + pressure * 0.5)

    const newLines = [...activeLayer.lines]
    const lastLine = newLines[newLines.length - 1]
    lastLine.points = lastLine.points.concat([point.x, point.y])
    lastLine.strokeWidth = dynamicSize // Update stroke width based on pressure
    updateLayer(activeLayerId, { lines: newLines })
  }

  const handlePointerUp = () => {
    setIsDrawing(false)
  }

  const updateLayer = (id, updates) => {
    setLayers(layers.map(l => l.id === id ? { ...l, ...updates } : l))
  }

  const addLayer = () => {
    const newId = Math.max(...layers.map(l => l.id)) + 1
    setLayers([...layers, { id: newId, name: `Layer ${newId}`, visible: true, lines: [] }])
    setActiveLayerId(newId)
  }

  const deleteLayer = (id) => {
    if (layers.length > 1) {
      setLayers(layers.filter(l => l.id !== id))
      if (activeLayerId === id) {
        setActiveLayerId(layers.find(l => l.id !== id).id)
      }
    }
  }

  const toggleLayerVisibility = (id) => {
    updateLayer(id, { visible: !layers.find(l => l.id === id).visible })
  }

  const clearLayer = (id) => {
    updateLayer(id, { lines: [] })
  }

  const exportCanvas = (format = 'png') => {
    if (format === 'png') {
      const uri = stageRef.current.toDataURL()
      const link = document.createElement('a')
      link.download = 'fashion_design.png'
      link.href = uri
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } else if (format === 'svg') {
      // Export as SVG
      const stage = stageRef.current
      const svgString = stage.toSVG()
      const blob = new Blob([svgString], { type: 'image/svg+xml' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.download = 'fashion_design.svg'
      link.href = url
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } else if (format === 'json') {
      // Export layered JSON
      const dataStr = JSON.stringify({ layers, projectName: currentProjectName }, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.download = 'fashion_design_layers.json'
      link.href = url
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }
  }

  const enhancePrompt = async () => {
    if (!token) {
      alert('Please login first')
      return
    }
    try {
      const res = await axios.post('http://localhost:8000/enhance_prompt', {
        prompt,
        model: 'llama-2-7b-chat'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setEnhancedPrompt(res.data.enhanced_prompt)
    } catch (error) {
      setEnhancedPrompt('Error: ' + error.message)
    }
  }

  const saveProject = async () => {
    if (!token) {
      alert('Please login first')
      return
    }
    try {
      const res = await axios.post('http://localhost:8000/canvas/save', {
        name: currentProjectName,
        layers: layers
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Project saved successfully!')
      loadProjects() // Refresh project list
    } catch (error) {
      alert('Error saving project: ' + error.message)
    }
  }

  const loadProjects = async () => {
    if (!token) return
    try {
      const res = await axios.get('http://localhost:8000/canvas/projects', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setProjects(res.data)
    } catch (error) {
      console.error('Error loading projects:', error)
    }
  }

  const loadProject = async (projectId) => {
    if (!token) {
      alert('Please login first')
      return
    }
    try {
      const res = await axios.get(`http://localhost:8000/canvas/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setLayers(res.data.layers)
      setCurrentProjectName(res.data.name)
      setActiveLayerId(res.data.layers[0]?.id || 1)
    } catch (error) {
      alert('Error loading project: ' + error.message)
    }
  }

  // Load projects on component mount
  React.useEffect(() => {
    if (token) {
      loadProjects()
    }
  }, [token])

  // Register service worker and set up offline sync
  React.useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', event => {
        if (event.data.type === 'SYNC_CANVAS_PROJECTS') {
          // Sync unsaved changes when back online
          syncOfflineProjects()
        }
      })
    }
  }, [])

  const syncOfflineProjects = async () => {
    // Check for offline-saved projects and sync them
    const offlineProjects = JSON.parse(localStorage.getItem('offline_canvas_projects') || '[]')
    for (const project of offlineProjects) {
      try {
        await axios.post('http://localhost:8000/canvas/save', {
          name: project.name,
          layers: project.layers
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (error) {
        console.error('Failed to sync offline project:', error)
      }
    }
    localStorage.removeItem('offline_canvas_projects')
    loadProjects() // Refresh the list
  }

  const saveOffline = (name, layers) => {
    // Save to localStorage when offline
    const offlineProjects = JSON.parse(localStorage.getItem('offline_canvas_projects') || '[]')
    offlineProjects.push({ name, layers, timestamp: Date.now() })
    localStorage.setItem('offline_canvas_projects', JSON.stringify(offlineProjects))
    alert('Project saved offline. Will sync when online.')
  }

  return (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <div>
        <h2>Fashion Design Canvas</h2>
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={currentProjectName}
            onChange={(e) => setCurrentProjectName(e.target.value)}
            placeholder="Project name"
            style={{ marginRight: '1rem' }}
          />
          <button onClick={saveProject}>Save Project</button>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Tool: </label>
          <select value={tool} onChange={(e) => setTool(e.target.value)}>
            <option value="brush">Brush</option>
            <option value="eraser">Eraser</option>
          </select>
          <input
            type="color"
            value={brushColor}
            onChange={(e) => setBrushColor(e.target.value)}
            style={{ marginLeft: '1rem' }}
          />
          <input
            type="range"
            min="1"
            max="20"
            value={brushSize}
            onChange={(e) => setBrushSize(parseInt(e.target.value))}
            style={{ marginLeft: '1rem' }}
          />
          <span>{brushSize}px</span>
        </div>
        <div className="canvas-container">
          <Stage
            width={800}
            height={600}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            ref={stageRef}
          >
            <Layer>
              <Rect x={0} y={0} width={800} height={600} fill="#ffffff" />
              <Text x={20} y={20} text="Draw your fashion design here" fontSize={16} />
            </Layer>
            {layers.filter(l => l.visible).map(layer => (
              <Layer key={layer.id}>
                {layer.lines.map((line, i) => (
                  <Line
                    key={i}
                    points={line.points}
                    stroke={line.stroke}
                    strokeWidth={line.strokeWidth}
                    tension={0.5}
                    lineCap="round"
                    globalCompositeOperation={tool === 'eraser' ? 'destination-out' : 'source-over'}
                  />
                ))}
              </Layer>
            ))}
          </Stage>
        </div>
        <div style={{ marginTop: '1rem' }}>
          <button onClick={undo} disabled={historyIndex <= 0}>Undo</button>
          <button onClick={redo} disabled={historyIndex >= history.length - 1}>Redo</button>
          <button onClick={exportCanvas}>Export PNG</button>
          <button onClick={() => clearLayer(activeLayerId)}>Clear Layer</button>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <h3>AI Design Assistant</h3>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your fashion design idea..."
            rows={3}
            style={{ width: '100%', marginBottom: '0.5rem' }}
          />
          <button onClick={enhancePrompt}>Enhance Prompt with AI</button>
          {enhancedPrompt && (
            <div style={{ marginTop: '0.5rem', padding: '0.5rem', background: '#f0f0f0', borderRadius: '4px' }}>
              <strong>Enhanced:</strong> {enhancedPrompt}
            </div>
          )}
        </div>

        <p>Touch and draw with your finger or stylus for tactile design!</p>
      </div>
      <div style={{ minWidth: '200px' }}>
        <h3>Layers</h3>
        <button onClick={addLayer}>Add Layer</button>
        {layers.map(layer => (
          <div key={layer.id} style={{ margin: '0.5rem 0', padding: '0.5rem', border: activeLayerId === layer.id ? '2px solid #007bff' : '1px solid #ccc' }}>
            <input
              type="checkbox"
              checked={layer.visible}
              onChange={() => toggleLayerVisibility(layer.id)}
            />
            <span onClick={() => setActiveLayerId(layer.id)} style={{ cursor: 'pointer', marginLeft: '0.5rem' }}>
              {layer.name}
            </span>
            <button onClick={() => deleteLayer(layer.id)} style={{ marginLeft: '1rem' }}>X</button>
          </div>
        ))}
        <h3 style={{ marginTop: '2rem' }}>Projects</h3>
        {projects.map(project => (
          <div key={project.id} style={{ margin: '0.5rem 0', padding: '0.5rem', border: '1px solid #ccc', cursor: 'pointer' }} onClick={() => loadProject(project.id)}>
            <strong>{project.name}</strong>
            <br />
            <small>Updated: {new Date(project.updated_at).toLocaleString()}</small>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Canvas